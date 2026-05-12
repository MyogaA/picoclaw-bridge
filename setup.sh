#!/bin/bash

echo "🚀 Memulai Setup Picoclaw Bridge..."

# 1. Update & Install Python venv (jika belum ada)
sudo apt update && sudo apt install -y python3-venv python3-pip

# 2. Buat Virtual Environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual Environment dibuat."
fi

# 3. Aktivasi venv dan Install Requirements
source venv/bin/activate
pip install --upgrade pip
pip install opencv-python pyTelegramBotAPI pyserial

echo "✅ Semua requirements berhasil diinstall!"
echo "🚀 Menjalankan Bridge..."

# 4. Jalankan Bridge
python3 bridge_picoclaw.py
