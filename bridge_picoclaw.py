import serial
import serial.tools.list_ports
import os
import time
import telebot
import cv2 
import subprocess
import sys

# --- OTOMATIS DETEKSI PORT ---
def find_esp_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Mencari port yang biasanya digunakan ESP32/Serial
        if "USB" in port.description or "UART" in port.description or "ACM" in port.device or "COM" in port.device:
            return port.device
    # Default jika tidak deteksi (Windows pakai COM, Linux pakai ttyACM)
    return 'COM3' if os.name == 'nt' else '/dev/ttyACM0'

SERIAL_PORT = find_esp_port()
BAUD_RATE = 115200

# --- KONFIGURASI PATH (WINDOWS & LINUX) ---
if os.name == 'nt': # Jika di Windows (Lenovo)
    home = os.path.expanduser("~")
    BASE_PATHS = {
        "LIFETECH": os.path.join(home, "Documents", "Lifetech"),
        "POSBEET": os.path.join(home, "Documents", "posbeet")
    }
else: # Jika di Ubuntu
    BASE_PATHS = {
        "LIFETECH": "/home/myoga/Documents/Lifetech",
        "POSBEET": "/home/myoga/Documents/posbeet"
    }

# Variabel Global
current_parent_path = ""
bot = None
CHAT_ID = ""

def get_credentials_from_esp():
    """Mengambil Token dan Chat ID tanpa menggunakan emoji (Aman untuk Windows)"""
    print(f"[INFO] Mencoba koneksi ke ESP32 di port: {SERIAL_PORT}")
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            time.sleep(2) 
            
            # Minta Token
            ser.write(b"GET_TOKEN\n")
            token_line = ser.readline().decode('utf-8', errors='ignore').strip()
            token = token_line.replace("TOKEN:", "")
            
            # Minta Chat ID
            ser.write(b"GET_ID\n")
            id_line = ser.readline().decode('utf-8', errors='ignore').strip()
            chat_id = id_line.replace("ID:", "")
            
            if token and chat_id:
                return token, chat_id
    except Exception as e:
        print(f"[ERROR] Gagal mengambil data: {e}")
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
                # Gunakan path temporary universal
                photo_path = os.path.join(os.environ.get('TEMP', '/tmp'), f"burst_{i}.jpg")
                cv2.imwrite(photo_path, frame)
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(CHAT_ID, photo, caption=f"Photo {i}/10")
                os.remove(photo_path)
            time.sleep(1.2)
        cap.release()
    except Exception as e:
        if cap: cap.release()
        bot.send_message(CHAT_ID, f"Error Kamera: {e}")

def send_folder_list(parent_key):
    global current_parent_path
    path = BASE_PATHS.get(parent_key)
    current_parent_path = path
    
    if not os.path.exists(path):
        bot.send_message(CHAT_ID, f"Path tidak ditemukan: {path}")
        return

    try:
        subfolders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        if not subfolders:
            bot.send_message(CHAT_ID, f"Folder {parent_key} kosong.")
            return

        message = f"Folder di {parent_key}:\n\n"
        for f in subfolders:
            safe_name = f.replace(" ", "_")
            message += f" {f} -> /open_{safe_name}\n"
        bot.send_message(CHAT_ID, message)
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error List Folder: {e}")

def open_with_antigravity(cmd_text):
    global current_parent_path
    if not current_parent_path:
        bot.send_message(CHAT_ID, "Pilih folder induk dulu!")
        return

    folder_name = cmd_text.replace("/open_", "").replace("_", " ")
    full_path = os.path.join(current_parent_path, folder_name)

    if os.path.exists(full_path):
        print(f"Launching: {full_path}")
        if os.name == 'nt': # Perintah Windows
            os.startfile(full_path)
        else: # Perintah Linux
            os.system(f"antigravity \"{full_path}\" &")
            os.system(f"nautilus \"{full_path}\" &")
    else:
        bot.send_message(CHAT_ID, f"Folder tidak ditemukan: {full_path}")

def execute_command(line):
    # Filter log
    if any(x in line for x in ["*", "IP Address", "WIFI", "TOKEN:", "ID:"]):
        return 

    print(f"Command Received: {line}")
    
    if line == "CMD_CAPTURE_PHOTO":
        capture_photo_opencv()
    elif line == "CMD_LIST_LIFETECH":
        send_folder_list("LIFETECH")
    elif line == "CMD_LIST_POSBEET":
        send_folder_list("POSBEET")
    elif line.startswith("CMD_OPEN_DIR:"):
        open_with_antigravity(line.split(":")[1])
    
    # Browser (Universal Command)
    elif line in ["CMD_YT", "CMD_CLAUDE", "CMD_WA", "CMD_CHROME"]:
        urls = {
            "CMD_YT": "https://www.youtube.com",
            "CMD_CLAUDE": "https://claude.ai",
            "CMD_WA": "https://web.whatsapp.com",
            "CMD_CHROME": "https://google.com"
        }
        url = urls.get(line, "https://google.com")
        if os.name == 'nt':
            os.system(f"start {url}")
        else:
            os.system(f"google-chrome {url} &")

    # Sistem
    elif line == "CMD_CLOSE_ALL" and os.name != 'nt':
        os.system("wmctrl -lp | awk '{print $1}' | xargs -n 1 wmctrl -ic")
    elif line == "CMD_SLEEP":
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0" if os.name == 'nt' else "systemctl suspend")

def main():
    global bot, CHAT_ID
    # Menghapus emoji di header
    print("--- Picoclaw Unified Bridge System Online ---")

    token, chat_id = get_credentials_from_esp()
    
    if not token or not chat_id:
        print("[FAIL] Tidak bisa mengambil token dari ESP32. Pastikan dicolok!")
        return

    CHAT_ID = chat_id
    bot = telebot.TeleBot(token)
    print(f"[SUCCESS] Bot Connected (ID: {CHAT_ID})")

    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                print(f"[READY] Listening on {SERIAL_PORT}...")
                while True:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            execute_command(line)
                    time.sleep(0.1)
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    main()
