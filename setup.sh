#!/bin/bash

# --- CONFIGURATION ---
REPO_URL="https://github.com/MyogaA/picoclaw-bridge.git"
PROJECT_DIR="picoclaw-bridge"
ALIAS_NAME="pico" # Menggunakan 'pico' agar lebih unik dan aman di Ubuntu

echo "------------------------------------------------"
echo "🚀 Picoclaw Unified Bootstrapper (Secure Version)"
echo "------------------------------------------------"

# 1. Pendaftaran Perintah Pendek (Alias)
# Agar kamu cukup ketik 'pico' untuk menjalankan sistem di masa depan
if ! grep -q "alias $ALIAS_NAME=" ~/.bashrc; then
    echo "📝 Mendaftarkan perintah '$ALIAS_NAME' ke sistem..."
    echo "alias $ALIAS_NAME='curl -sSL https://raw.githubusercontent.com/MyogaA/picoclaw-bridge/main/setup.sh | bash'" >> ~/.bashrc
    echo "✅ Perintah '$ALIAS_NAME' berhasil didaftarkan."
fi

# 2. Cek/Download Repository
if [ ! -d "$PROJECT_DIR" ] && [ ! -f "bridge_picoclaw.py" ]; then
    echo "📂 Mendownload project dari GitHub..."
    git clone $REPO_URL
    cd $PROJECT_DIR || exit
elif [ -d "$PROJECT_DIR" ]; then
    cd $PROJECT_DIR || exit
fi

# 3. Instalasi Dependensi Sistem
echo "📦 Mengecek kebutuhan sistem (Python venv, OpenCV, Serial)..."
sudo apt update -y && sudo apt install -y python3-venv python3-pip libgl1-mesa-glx wmctrl

# 4. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "🛠️ Membuat Virtual Environment..."
    python3 -m venv venv
fi

# 5. Aktivasi & Instalasi Library Python
source venv/bin/activate
echo "📥 Mengupdate library Python..."
pip install --upgrade pip
pip install pyserial pyTelegramBotAPI opencv-python

# 6. Menjalankan Bridge
echo "------------------------------------------------"
echo "⚡ MENJALANKAN BRIDGE..."
echo "💡 Pastikan ESP32 sudah dicolokkan ke USB!"
echo "------------------------------------------------"

# Memberikan izin akses port serial jika belum ada
sudo usermod -a -G dialout $USER

python3 bridge_picoclaw.py
