import serial
import os
import time
import telebot
import cv2  # Pastikan sudah: pip install opencv-python
import subprocess

# --- KONFIGURASI ---
TOKEN = "8663457580:AAFmJ9Taj3_mumbW1zbWKFkt8P00FYWW8fM"
CHAT_ID = "1318804813"
SERIAL_PORT = '/dev/ttyACM0' 
BAUD_RATE = 115200

bot = telebot.TeleBot(TOKEN)

# PATH DIREKTORI UTAMA
BASE_PATHS = {
    "LIFETECH": "/home/myoga/Documents/Lifetech",
    "POSBEET": "/home/myoga/Documents/posbeet"
}

current_parent_path = ""

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
    # Abaikan pesan log dari WiFiManager (yang biasanya diawali tanda *)
    if line.startswith("*") or "IP Address" in line:
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
    print("--- Picoclaw Unified Bridge System Online ---")
    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                print(f"✅ Bridge Aktif di {SERIAL_PORT}")
                while True:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8').strip()
                        if line:
                            execute_command(line)
                    time.sleep(0.1)
        except Exception as e:
            print(f"📴 Menunggu koneksi ESP32... ({e})")
            time.sleep(3)

if __name__ == "__main__":
    main()
