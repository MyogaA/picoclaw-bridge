#!/bin/bash

# Konfigurasi
PROJECT_DIR="picoclaw-bridge"
REPO_URL="https://github.com/MyogaA/picoclaw-bridge.git"

echo "------------------------------------------"
echo "🚀 Picoclaw Unified Bootstrapper"
echo "------------------------------------------"

# 1. Cek apakah kita sudah di dalam folder project
if [ ! -f "bridge_picoclaw.py" ]; then
    echo "📂 Project belum ada. Mendownload dari GitHub..."
    git clone $REPO_URL $PROJECT_DIR
    cd $PROJECT_DIR || exit
fi

# 2. Cek/Install Python Venv & Dependencies
if [ ! -d "venv" ]; then
    echo "📦 Setup pertama kali: Membuat Virtual Environment..."
    sudo apt update && sudo apt install -y python3-venv python3-pip
    python3 -m venv venv
    
    source venv/bin/activate
    echo "📥 Menginstal OpenCV dan library lainnya..."
    pip install --upgrade pip
    pip install opencv-python pyTelegramBotAPI pyserial
else
    echo "✅ Environment ditemukan. Mengaktifkan..."
    source venv/bin/activate
fi

# 3. Jalankan Bridge
echo "⚡ Menjalankan Bridge Picoclaw..."
python3 bridge_picoclaw.py
