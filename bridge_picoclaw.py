import serial
import serial.tools.list_ports
import os
import time
import telebot
import cv2 
import sys
import threading
import speech_recognition as sr
from pydub import AudioSegment

# --- 1. OTOMATIS DETEKSI PORT ---
def find_esp_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Linux biasanya mendeteksi ESP32 sebagai ttyUSB0 atau ttyACM0
        if any(x in port.device.upper() for x in ["USB", "ACM"]):
            return port.device
    return '/dev/ttyACM0' 

SERIAL_PORT = find_esp_port()
BAUD_RATE = 115200
TEMP_DIR = "/tmp"

# --- 2. KONFIGURASI PATH ---
home = os.path.expanduser("~")
BASE_PATHS = {
    "LIFETECH": os.path.join(home, "Documents/Lifetech"),
    "POSBEET": os.path.join(home, "Documents/posbeet")
}

# Variabel Global
bot = None
CHAT_ID = ""
recognizer = sr.Recognizer()

# --- 3. FUNGSI KAMERA (FIX NAMA & BACKEND LINUX) ---
def capture_photo_opencv():
    """Fungsi ini sekarang dipanggil dengan benar di execute_command"""
    cap = None
    try:
        # Gunakan V4L2 backend untuk kompatibilitas Ubuntu yang lebih baik
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if not cap.isOpened():
            if bot: bot.send_message(CHAT_ID, "❌ Kamera tidak terdeteksi di /dev/video0")
            return

        # Warming up sensor
        for _ in range(10): cap.read()

        ret, frame = cap.read()
        if ret:
            photo_path = os.path.join(TEMP_DIR, "snap.jpg")
            cv2.imwrite(photo_path, frame)
            with open(photo_path, 'rb') as photo:
                bot.send_photo(CHAT_ID, photo, caption="📸 Capture Success (Linux)")
            os.remove(photo_path)
    except Exception as e:
        if bot: bot.send_message(CHAT_ID, f"❌ Error Kamera: {e}")
    finally:
        if cap: cap.release()

# --- 4. EKSEKUSI PERINTAH ---
def execute_command(line):
    if any(x in line for x in ["*", "IP Address", "WIFI", "TOKEN:", "ID:"]): return 
    
    print(f"[CMD] Eksekusi: {line}")
    
    if line == "CMD_CAPTURE_PHOTO":
        capture_photo_opencv() # NAMA SUDAH SESUAI
    elif line == "CMD_YT":
        os.system("xdg-open https://www.youtube.com &")
    elif line == "CMD_WA":
        os.system("xdg-open https://web.whatsapp.com &")
    elif line == "CMD_SLEEP":
        os.system("systemctl suspend")
    elif line == "CMD_CLOSE_ALL":
        os.system("wmctrl -lp | awk '{print $1}' | xargs -n 1 wmctrl -ic")

# --- 5. LOGIKA VOICE COMMAND ---
def start_telebot_polling():
    @bot.message_handler(content_types=['voice'])
    def handle_voice(message):
        try:
            file_info = bot.get_file(message.voice.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            oga_path = os.path.join(TEMP_DIR, "voice.oga")
            wav_path = os.path.join(TEMP_DIR, "voice.wav")
            
            with open(oga_path, 'wb') as f: f.write(downloaded_file)
            
            # Konversi OGA ke WAV (Butuh ffmpeg: sudo apt install ffmpeg)
            audio = AudioSegment.from_ogg(oga_path)
            audio.export(wav_path, format="wav")
            
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language="id-ID").lower()
                bot.reply_to(message, f"Mendengar: \"{text}\"")
                
                # Mapping Suara ke Perintah
                if "foto" in text or "kamera" in text:
                    execute_command("CMD_CAPTURE_PHOTO")
                elif "youtube" in text:
                    execute_command("CMD_YT")
                elif "tidur" in text or "istirahat" in text:
                    execute_command("CMD_SLEEP")
            
            os.remove(oga_path)
            os.remove(wav_path)
        except Exception as e:
            bot.reply_to(message, f"❌ Error Voice: {e}")

    bot.infinity_polling()

# --- 6. MAIN LOOP ---
def main():
    global bot, CHAT_ID
    print("--- Picoclaw Bridge Linux Online ---")
    
    # Ambil kredensial dari hardware
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            time.sleep(2)
            ser.write(b"GET_TOKEN\n")
            token = ser.readline().decode('utf-8', errors='ignore').strip().replace("TOKEN:", "")
            ser.write(b"GET_ID\n")
            chat_id = ser.readline().decode('utf-8', errors='ignore').strip().replace("ID:", "")
            
            if not token or not chat_id:
                print("[FAIL] Kredensial kosong!")
                return
    except Exception as e:
        print(f"[ERROR] Gagal Serial: {e}"); return

    CHAT_ID = chat_id
    bot = telebot.TeleBot(token)
    
    # JALANKAN BOT DI THREAD TERPISAH
    threading.Thread(target=start_telebot_polling, daemon=True).start()
    print(f"[SUCCESS] Bot & Voice Handler Aktif. Monitoring {SERIAL_PORT}...")

    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                while True:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line: execute_command(line)
                    time.sleep(0.1)
        except:
            time.sleep(3)

if __name__ == "__main__":
    main()
