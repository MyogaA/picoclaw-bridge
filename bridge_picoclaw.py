import serial
import serial.tools.list_ports
import os
import time
import telebot
import cv2 
import subprocess
import sys
import threading
import speech_recognition as sr
from pydub import AudioSegment

# --- 1. OTOMATIS DETEKSI PORT (SMART SCAN) ---
def find_esp_port():
    ports = serial.tools.list_ports.comports()
    print("[DEBUG] Mencari perangkat USB yang tersedia...")
    
    for port in ports:
        desc = port.description.upper()
        if any(x in desc for x in ["USB", "UART", "CP210", "CH340", "BRIDGE", "SERAIL"]):
            print(f"[DEBUG] Perangkat ditemukan: {port.device} ({port.description})")
            return port.device
            
    return 'COM3' if os.name == 'nt' else '/dev/ttyACM0'

SERIAL_PORT = find_esp_port()
BAUD_RATE = 115200

# --- 2. KONFIGURASI PATH DINAMIS ---
home = os.path.expanduser("~")
if os.name == 'nt': 
    BASE_PATHS = {
        "LIFETECH": os.path.join(home, "Documents", "Lifetech"),
        "POSBEET": os.path.join(home, "Documents", "posbeet")
    }
    TEMP_DIR = os.environ.get('TEMP', 'C:\\Temp')
else: 
    BASE_PATHS = {
        "LIFETECH": f"/home/myoga/Documents/Lifetech",
        "POSBEET": f"/home/myoga/Documents/posbeet"
    }
    TEMP_DIR = "/tmp"

# Variabel Global
current_parent_path = ""
bot = None
CHAT_ID = ""
recognizer = sr.Recognizer()

def get_credentials_from_esp():
    """Mengambil Token dan Chat ID dari hardware ESP32 via Serial"""
    print(f"[INFO] Menghubungkan ke ESP32 di {SERIAL_PORT}...")
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=3, dsrdtr=True) as ser:
            time.sleep(4) # Tunggu ESP32 selesai booting setelah buka port
            ser.reset_input_buffer()
            
            # Request Token
            ser.write(b"GET_TOKEN\n")
            time.sleep(1)
            token_line = ser.readline().decode('utf-8', errors='ignore').strip()
            token = token_line.replace("TOKEN:", "").strip()
            
            # Request Chat ID
            ser.write(b"GET_ID\n")
            time.sleep(1)
            id_line = ser.readline().decode('utf-8', errors='ignore').strip()
            chat_id = id_line.replace("ID:", "").strip()
            
            if token and chat_id:
                return token, chat_id
    except Exception as e:
        print(f"[ERROR] Gagal komunikasi Serial: {e}")
    return None, None

def capture_photo_opencv():
    cap = None
    try:
        if bot: bot.send_message(CHAT_ID, "📸 Memulai kamera (Linux V4L2)...")
        # Di Linux, gunakan CAP_V4L2 untuk stabilitas
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if not cap.isOpened():
            if bot: bot.send_message(CHAT_ID, "Gagal: Kamera tidak terdeteksi!")
            return

        # Warming up sensor
        for _ in range(10): cap.read()

        ret, frame = cap.read()
        if ret:
            photo_path = os.path.join(TEMP_DIR, "capture.jpg")
            cv2.imwrite(photo_path, frame)
            with open(photo_path, 'rb') as photo:
                bot.send_photo(CHAT_ID, photo, caption="📸 Berhasil mengambil foto!")
            try: os.remove(photo_path)
            except: pass
        
        cap.release()
    except Exception as e:
        if cap: cap.release()
        if bot: bot.send_message(CHAT_ID, f"Error Kamera: {e}")

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
            os.system(f"antigravity \"{full_path}\" &")
            os.system(f"nautilus \"{full_path}\" &")
    else:
        bot.send_message(CHAT_ID, f"Error: Folder tidak ditemukan di {full_path}")

def execute_command(line):
    if any(x in line for x in ["*", "IP Address", "WIFI", "TOKEN:", "ID:"]):
        return 

    print(f"[CMD] Eksekusi: {line}")
    
    if line == "CMD_CAPTURE_PHOTO":
        capture_photo_opencv()
    elif line == "CMD_LIST_LIFETECH":
        send_folder_list("LIFETECH")
    elif line == "CMD_LIST_POSBEET":
        send_folder_list("POSBEET")
    elif line.startswith("CMD_OPEN_DIR:"):
        open_with_antigravity(line.split(":")[1])
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
            os.system(f"xdg-open {target} &")
    elif line == "CMD_SLEEP":
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0" if os.name == 'nt' else "systemctl suspend")

# --- 3. LOGIKA VOICE HANDLER ---
def start_voice_bot():
    @bot.message_handler(content_types=['voice'])
    def handle_voice(message):
        try:
            print("[VOICE] Menerima pesan suara...")
            file_info = bot.get_file(message.voice.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            oga_path = os.path.join(TEMP_DIR, "voice.oga")
            wav_path = os.path.join(TEMP_DIR, "voice.wav")
            
            with open(oga_path, 'wb') as f:
                f.write(downloaded_file)
            
            # Konversi OGA ke WAV (Butuh FFmpeg di sistem)
            audio = AudioSegment.from_ogg(oga_path)
            audio.export(wav_path, format="wav")
            
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language="id-ID").lower()
                bot.reply_to(message, f"🎙️ Mendengar: \"{text}\"")
                
                # Pemetaan Perintah Suara
                if "foto" in text or "kamera" in text:
                    execute_command("CMD_CAPTURE_PHOTO")
                elif "youtube" in text:
                    execute_command("CMD_YT")
                elif "whatsapp" in text:
                    execute_command("CMD_WA")
                elif "istirahat" in text or "tidur" in text:
                    execute_command("CMD_SLEEP")
                else:
                    bot.send_message(CHAT_ID, "Perintah suara tidak dikenali.")

            if os.path.exists(oga_path): os.remove(oga_path)
            if os.path.exists(wav_path): os.remove(wav_path)
            
        except Exception as e:
            bot.reply_to(message, f"❌ Error Voice: {e}")

    print("[SUCCESS] Bot Polling Aktif (Menunggu Pesan/Suara)...")
    bot.infinity_polling()

def main():
    global bot, CHAT_ID
    print("--- Picoclaw Unified Bridge System Online ---")

    token, chat_id = get_credentials_from_esp()
    
    if not token or not chat_id:
        print("[FAIL] Kredensial hardware gagal diambil. Pastikan ESP32 terhubung dan merespon.")
        return

    CHAT_ID = chat_id
    bot = telebot.TeleBot(token)
    print(f"[SUCCESS] Bot Terhubung (ID: {CHAT_ID})")

    # Jalankan Bot Telegram di Thread terpisah
    bot_thread = threading.Thread(target=start_voice_bot, daemon=True)
    bot_thread.start()

    # Loop utama monitoring Serial ESP32
    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                print(f"[READY] Monitoring perintah Serial di {SERIAL_PORT}...")
                while True:
                    if ser.in_waiting > 0:
                        raw_line = ser.readline()
                        line = raw_line.decode('utf-8', errors='ignore').strip()
                        if line:
                            execute_command(line)
                    time.sleep(0.1)
        except Exception as e:
            print(f"[RECONNECT] Koneksi terputus: {e}. Mencoba lagi...")
            time.sleep(3)

if __name__ == "__main__":
    main()
