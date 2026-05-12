import serial
import os
import time
import telebot
import cv2  # Pastikan sudah: pip install opencv-python
import subprocess

# --- KONFIGURASI SERIAL ---
SERIAL_PORT = '/dev/ttyACM0' 
BAUD_RATE = 115200

# PATH DIREKTORI UTAMA
BASE_PATHS = {
    "LIFETECH": "/home/myoga/Documents/Lifetech",
    "POSBEET": "/home/myoga/Documents/posbeet"
}

# Variabel Global
current_parent_path = ""
bot = None
CHAT_ID = ""

def get_credentials_from_esp():
    """Mengambil Token dan Chat ID dari memori ESP32 via Serial"""
    print("🔌 Menghubungkan ke ESP32 untuk mengambil kredensial...")
    try:
        # Gunakan context manager agar serial tertutup otomatis setelah ambil data
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            time.sleep(2)  # Tunggu ESP32 reboot setelah dicolok
            
            # Minta Token
            ser.write(b"GET_TOKEN\n")
            token_line = ser.readline().decode().strip()
            token = token_line.replace("TOKEN:", "")
            
            # Minta Chat ID
            ser.write(b"GET_ID\n")
            id_line = ser.readline().decode().strip()
            chat_id = id_line.replace("ID:", "")
            
            if token and chat_id:
                return token, chat_id
            else:
                return None, None
    except Exception as e:
        print(f"❌ Gagal mengambil data: {e}")
        return None, None

def capture_photo_opencv():
    cap = None
    try:
        bot.send_message(CHAT_ID, "🎬 Memulai Burst Mode OpenCV (10 foto)...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            bot.send_message(CHAT_ID, "❌ Kamera tidak terdeteksi!")
            return

        # Buang 5 frame pertama untuk penyesuaian cahaya
        for _ in range(5):
            cap.read()

        for i in range(1, 11):
            ret, frame = cap.read()
            if ret:
                photo_path = f"/tmp/burst_{i}.jpg"
                cv2.imwrite(photo_path, frame)
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(CHAT_ID, photo, caption=f"📷 OpenCV Burst {i}/10")
                os.remove(photo_path)
            time.sleep(1.5)

        cap.release()
        bot.send_message(CHAT_ID, "✅ Selesai mengambil 10 foto.")
    except Exception as e:
        if cap: cap.release()
        bot.send_message(CHAT_ID, f"❌ Error OpenCV: {e}")

def send_folder_list(parent_key):
    global current_parent_path
    path = BASE_PATHS.get(parent_key)
    current_parent_path = path
    
    if not os.path.exists(path):
        bot.send_message(CHAT_ID, f"❌ Path tidak ditemukan: {path}")
        return

    try:
        subfolders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        if not subfolders:
            bot.send_message(CHAT_ID, f"📁 Folder {parent_key} kosong.")
            return

        message = f"📂 Sub-folder di {parent_key}:\nKlik untuk membuka:\n\n"
        for f in subfolders:
            safe_name = f.replace(" ", "_")
            message += f"📁 {f} -> /open_{safe_name}\n"
        bot.send_message(CHAT_ID, message)
    except Exception as e:
        bot.send_message(CHAT_ID, f"❌ Error: {e}")

def open_with_antigravity(cmd_text):
    global current_parent_path
    if not current_parent_path:
        bot.send_message(CHAT_ID, "⚠️ Pilih folder induk dulu (/lifetech atau /posbeet)")
        return

    folder_name = cmd_text.replace("/open_", "").replace("_", " ")
    full_path = os.path.join(current_parent_path, folder_name)

    if os.path.exists(full_path):
        print(f"🚀 Launching: {full_path}")
        os.system(f"antigravity \"{full_path}\" &")
        os.system(f"nautilus \"{full_path}\" &")
    else:
        bot.send_message(CHAT_ID, f"❌ Folder tidak ditemukan: {folder_name}")

def execute_command(line):
    # Filter log sampah dari ESP32
    if any(x in line for x in ["*", "IP Address", "WIFI_READY", "TOKEN:", "ID:"]):
        return 

    print(f"📩 Valid Command: {line}")
    
    # 1. KAMERA
    if line == "CMD_CAPTURE_PHOTO":
        capture_photo_opencv()

    # 2. FOLDER EXPLORER
    elif line == "CMD_LIST_LIFETECH":
        send_folder_list("LIFETECH")
    elif line == "CMD_LIST_POSBEET":
        send_folder_list("POSBEET")
    elif line.startswith("CMD_OPEN_DIR:"):
        cmd_text = line.split(":")[1]
        open_with_antigravity(cmd_text)

    # 3. BROWSER
    elif line == "CMD_YT":
        os.system("google-chrome https://www.youtube.com &")
    elif line == "CMD_CLAUDE":
        os.system("google-chrome https://claude.ai &")
    elif line == "CMD_WA":
        os.system("google-chrome https://web.whatsapp.com &")
    elif line == "CMD_CHROME":
        os.system("google-chrome &")

    # 4. SISTEM
    elif line == "CMD_CLOSE_ALL":
        os.system("wmctrl -lp | awk '{print $1}' | xargs -n 1 wmctrl -ic")
    elif line == "CMD_SLEEP":
        os.system("systemctl suspend")
    elif line == "CMD_SHUTDOWN":
        os.system("poweroff")

def main():
    global bot, CHAT_ID
    print("--- Picoclaw Unified Bridge System Online ---")

    # Inisialisasi Kredensial
    token, chat_id = get_credentials_from_esp()
    
    if not token or not chat_id:
        print("❌ Gagal mendapatkan Token dari hardware. Mematikan sistem...")
        return

    CHAT_ID = chat_id
    bot = telebot.TeleBot(token)
    print(f"✅ Bot Terhubung (ID: {CHAT_ID})")

    # Loop utama mendengarkan Serial
    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                print(f"📡 Mendengarkan Command di {SERIAL_PORT}...")
                while True:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            execute_command(line)
                    time.sleep(0.1)
        except Exception as e:
            print(f"📴 Koneksi terputus, mencoba ulang... ({e})")
            time.sleep(3)

if __name__ == "__main__":
    main()
