import serial
import serial.tools.list_ports
import os
import time
import telebot
import cv2 
import subprocess
import sys

# --- 1. OTOMATIS DETEKSI PORT (SMART SCAN) ---
def find_esp_port():
    ports = serial.tools.list_ports.comports()
    print("[DEBUG] Mencari perangkat USB yang tersedia...")
    
    # Prioritas 1: Cari berdasarkan deskripsi chip hardware
    for port in ports:
        desc = port.description.upper()
        if any(x in desc for x in ["USB", "UART", "CP210", "CH340", "BRIDGE", "SERAIL"]):
            print(f"[DEBUG] Perangkat ditemukan: {port.device} ({port.description})")
            return port.device
            
    # Prioritas 2: Khusus Windows, ambil port COM yang tersedia
    if os.name == 'nt':
        for port in ports:
            if "COM" in port.device:
                print(f"[DEBUG] Menggunakan port COM aktif: {port.device}")
                return port.device
                
    # Fallback default jika tidak ada yang terdeteksi
    return 'COM3' if os.name == 'nt' else '/dev/ttyACM0'

SERIAL_PORT = find_esp_port()
BAUD_RATE = 115200

# --- 2. KONFIGURASI PATH DINAMIS ---
if os.name == 'nt': # Konfigurasi Windows (Lenovo)
    home = os.path.expanduser("~")
    BASE_PATHS = {
        "LIFETECH": os.path.join(home, "Documents", "Lifetech"),
        "POSBEET": os.path.join(home, "Documents", "posbeet")
    }
    # Gunakan folder TEMP standar Windows
    TEMP_DIR = os.environ.get('TEMP', 'C:\\Temp')
else: # Konfigurasi Linux (Ubuntu)
    BASE_PATHS = {
        "LIFETECH": "/home/myoga/Documents/Lifetech",
        "POSBEET": "/home/myoga/Documents/posbeet"
    }
    TEMP_DIR = "/tmp"

# Variabel Global
current_parent_path = ""
bot = None
CHAT_ID = ""

def get_credentials_from_esp():
    """Mengambil Token dan Chat ID dari hardware ESP32 via Serial"""
    print(f"[INFO] Menghubungkan ke ESP32 di {SERIAL_PORT}...")
    try:
        # dsrdtr=True sering membantu kestabilan koneksi serial di Windows
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2, dsrdtr=True) as ser:
            time.sleep(2) # Tunggu ESP32 stabil setelah inisialisasi port
            
            # Request Token
            ser.write(b"GET_TOKEN\n")
            token_line = ser.readline().decode('utf-8', errors='ignore').strip()
            token = token_line.replace("TOKEN:", "")
            
            # Request Chat ID
            ser.write(b"GET_ID\n")
            id_line = ser.readline().decode('utf-8', errors='ignore').strip()
            chat_id = id_line.replace("ID:", "")
            
            if token and chat_id:
                return token, chat_id
    except Exception as e:
        print(f"[ERROR] Gagal komunikasi Serial: {e}")
    return None, None

def capture_photo_opencv():
    cap = None
    try:
        bot.send_message(CHAT_ID, "Memulai Burst Mode OpenCV (10 foto)...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            bot.send_message(CHAT_ID, "Gagal: Kamera tidak terdeteksi!")
            return

        # Warming up sensor
        for _ in range(5): cap.read()

        for i in range(1, 11):
            ret, frame = cap.read()
            if ret:
                photo_name = f"burst_{i}.jpg"
                photo_path = os.path.join(TEMP_DIR, photo_name)
                cv2.imwrite(photo_path, frame)
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(CHAT_ID, photo, caption=f"Capture {i}/10")
                try: os.remove(photo_path)
                except: pass
            time.sleep(1.2)
        cap.release()
        bot.send_message(CHAT_ID, "Selesai mengambil burst photo.")
    except Exception as e:
        if cap: cap.release()
        bot.send_message(CHAT_ID, f"Error OpenCV: {e}")

def send_folder_list(parent_key):
    global current_parent_path
    path = BASE_PATHS.get(parent_key)
    current_parent_path = path
    
    if not path or not os.path.exists(path):
        bot.send_message(CHAT_ID, f"Error: Path {path} tidak ditemukan.")
        return

    try:
        subfolders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        if not subfolders:
            bot.send_message(CHAT_ID, f"Folder {parent_key} kosong.")
            return

        message = f"Folder di {parent_key}:\n\n"
        for f in subfolders:
            safe_name = f.replace(" ", "_")
            message += f" - {f} -> /open_{safe_name}\n"
        bot.send_message(CHAT_ID, message)
    except Exception as e:
        bot.send_message(CHAT_ID, f"Error List Folder: {e}")

def open_with_antigravity(cmd_text):
    global current_parent_path
    if not current_parent_path:
        bot.send_message(CHAT_ID, "⚠️ Pilih folder induk dulu!")
        return

    folder_name = cmd_text.replace("/open_", "").replace("_", " ")
    full_path = os.path.join(current_parent_path, folder_name)

    if os.path.exists(full_path):
        print(f"[SYSTEM] Membuka: {full_path}")
        if os.name == 'nt':
            os.startfile(full_path)
        else:
            # Perintah khusus Ubuntu untuk membuka folder dan tool kustom
            os.system(f"antigravity \"{full_path}\" &")
            os.system(f"nautilus \"{full_path}\" &")
    else:
        bot.send_message(CHAT_ID, f"Error: Folder tidak ditemukan di {full_path}")

def execute_command(line):
    # Filter log handshake agar tidak dianggap perintah
    if any(x in line for x in ["*", "IP Address", "WIFI", "TOKEN:", "ID:"]):
        return 

    print(f"[CMD] Eksekusi: {line}")
    
    # 1. Kamera
    if line == "CMD_CAPTURE_PHOTO":
        capture_photo_opencv()
        
    # 2. Explorer
    elif line == "CMD_LIST_LIFETECH":
        send_folder_list("LIFETECH")
    elif line == "CMD_LIST_POSBEET":
        send_folder_list("POSBEET")
    elif line.startswith("CMD_OPEN_DIR:"):
        open_with_antigravity(line.split(":")[1])
    
    # 3. Browser
    elif line in ["CMD_YT", "CMD_CLAUDE", "CMD_WA", "CMD_CHROME"]:
        urls = {
            "CMD_YT": "https://www.youtube.com",
            "CMD_CLAUDE": "https://claude.ai",
            "CMD_WA": "https://web.whatsapp.com",
            "CMD_CHROME": "https://google.com"
        }
        target = urls.get(line)
        if os.name == 'nt':
            os.system(f"start {target}")
        else:
            os.system(f"google-chrome {target} &")

    # 4. Power Management
    elif line == "CMD_CLOSE_ALL" and os.name != 'nt':
        os.system("wmctrl -lp | awk '{print $1}' | xargs -n 1 wmctrl -ic")
    elif line == "CMD_SLEEP":
        if os.name == 'nt':
            # Perintah sleep Windows standar
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        else:
            os.system("systemctl suspend")

def main():
    global bot, CHAT_ID
    print("--- Picoclaw Unified Bridge System Online ---")

    # Ambil Kredensial (Token/ID) langsung dari hardware
    token, chat_id = get_credentials_from_esp()
    
    if not token or not chat_id:
        print("[FAIL] Kredensial hardware gagal diambil. Pastikan ESP32 terhubung.")
        return

    CHAT_ID = chat_id
    bot = telebot.TeleBot(token)
    print(f"[SUCCESS] Bot Berhasil Terhubung (ID: {CHAT_ID})")

    # Loop utama monitoring Serial
    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                print(f"[READY] Monitoring perintah di {SERIAL_PORT}...")
                while True:
                    if ser.in_waiting > 0:
                        raw_line = ser.readline()
                        line = raw_line.decode('utf-8', errors='ignore').strip()
                        if line:
                            execute_command(line)
                    time.sleep(0.1)
        except Exception as e:
            print(f"[RECONNECT] Koneksi terputus: {e}. Mencoba dalam 3 detik...")
            time.sleep(3)

if __name__ == "__main__":
    main()
