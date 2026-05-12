import serial
import serial.tools.list_ports
import os
import time
import telebot
import cv2 
import sys

# --- OTOMATIS DETEKSI PORT (COM untuk Windows, /dev/ untuk Linux) ---
def find_esp_port():
    ports = serial.tools.list_ports.comports()
    # 1. Cari port yang spesifik hardware ESP32
    for port in ports:
        desc = port.description.upper()
        if "USB" in desc or "UART" in desc or "CP210" in desc or "CH340" in desc:
            return port.device
    
    # 2. Jika tidak ketemu, cari port COM apapun (Windows) atau ttyACM (Linux)
    for port in ports:
        if os.name == 'nt' and "COM" in port.device:
            return port.device
        elif "ttyACM" in port.device or "ttyUSB" in port.device:
            return port.device
            
    # 3. Fallback default
    return 'COM3' if os.name == 'nt' else '/dev/ttyACM0'

SERIAL_PORT = find_esp_port()
BAUD_RATE = 115200

# --- KONFIGURASI PATH (WINDOWS & LINUX) ---
if os.name == 'nt': 
    home = os.path.expanduser("~")
    BASE_PATHS = {
        "LIFETECH": os.path.join(home, "Documents", "Lifetech"),
        "POSBEET": os.path.join(home, "Documents", "posbeet")
    }
else:
    BASE_PATHS = {
        "LIFETECH": "/home/myoga/Documents/Lifetech",
        "POSBEET": "/home/myoga/Documents/posbeet"
    }

current_parent_path = ""
bot = None
CHAT_ID = ""

def get_credentials_from_esp():
    """Mengambil Token dan Chat ID dari hardware ESP32"""
    print(f"[INFO] Mencoba koneksi ke ESP32 di port: {SERIAL_PORT}")
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            time.sleep(2) # Tunggu ESP32 reboot
            
            ser.write(b"GET_TOKEN\n")
            token_line = ser.readline().decode('utf-8', errors='ignore').strip()
            token = token_line.replace("TOKEN:", "")
            
            ser.write(b"GET_ID\n")
            id_line = ser.readline().decode('utf-8', errors='ignore').strip()
            chat_id = id_line.replace("ID:", "")
            
            if token and chat_id:
                return token, chat_id
    except Exception as e:
        print(f"[ERROR] Gagal mengambil data via Serial: {e}")
    return None, None

def capture_photo_opencv():
    cap = None
    try:
        bot.send_message(CHAT_ID, "Memulai Burst Mode OpenCV (10 foto)...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            bot.send_message(CHAT_ID, "Kamera tidak terdeteksi!")
            return

        for _ in range(5): cap.read() # Warming up

        for i in range(1, 11):
            ret, frame = cap.read()
            if ret:
                # Path temporary universal
                temp_dir = os.environ.get('TEMP', '/tmp')
                photo_path = os.path.join(temp_dir, f"burst_{i}.jpg")
                cv2.imwrite(photo_path, frame)
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(CHAT_ID, photo, caption=f"Photo {i}/10")
                os.remove(photo_path)
            time.sleep(1.2)
        cap.release()
    except Exception as e:
        if cap: cap.release()
        bot.send_message(CHAT_ID, f"Error Kamera: {e}")

def execute_command(line):
    if any(x in line for x in ["*", "IP Address", "WIFI", "TOKEN:", "ID:"]):
        return 

    print(f"Command Received: {line}")
    
    if line == "CMD_CAPTURE_PHOTO":
        capture_photo_opencv()
    elif line == "CMD_YT":
        url = "https://www.youtube.com"
        os.system(f"start {url}" if os.name == 'nt' else f"google-chrome {url} &")
    elif line == "CMD_SLEEP":
        if os.name == 'nt':
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        else:
            os.system("systemctl suspend")
    # Tambahkan command lain di sini...

def main():
    global bot, CHAT_ID
    print("--- Picoclaw Unified Bridge System Online ---")

    token, chat_id = get_credentials_from_esp()
    
    if not token or not chat_id:
        print("[FAIL] Gagal mendapatkan kredensial. Cek kabel USB!")
        return

    CHAT_ID = chat_id
    bot = telebot.TeleBot(token)
    print(f"[SUCCESS] Bot Aktif menggunakan token dari Hardware (ID: {CHAT_ID})")

    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                print(f"[READY] Mendengarkan perintah di {SERIAL_PORT}...")
                while True:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            execute_command(line)
                    time.sleep(0.1)
        except Exception as e:
            print(f"[RECONNECT] Koneksi hilang, mencoba lagi dalam 3 detik...")
            time.sleep(3)

if __name__ == "__main__":
    main()
