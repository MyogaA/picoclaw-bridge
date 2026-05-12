#!/bin/bash

REPO_URL="https://github.com/MyogaA/picoclaw-bridge.git"
PROJECT_DIR="picoclaw-bridge"

echo "------------------------------------------------"
echo "🚀 Picoclaw Bootstrapper (Fix Command Not Found)"
echo "------------------------------------------------"

# 1. Download Repo
if [ ! -d "$PROJECT_DIR" ]; then
    git clone $REPO_URL
fi
cd $PROJECT_DIR || exit

# 2. Deteksi Perintah Python yang Tersedia
if command -v python &>/dev/null; then
    PY_CMD="python"
elif command -v python3 &>/dev/null; then
    PY_CMD="python3"
else
    echo "❌ Error: Python tidak ditemukan di sistem ini!"
    exit 1
fi

echo "✅ Menggunakan: $PY_CMD"

# 3. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Membuat Virtual Environment..."
    $PY_CMD -m venv venv
fi

# 4. Aktivasi (Cek folder Scripts untuk Windows atau bin untuk Linux)
if [ -d "venv/Scripts" ]; then
    echo "💻 Mendeteksi Windows (Git Bash)..."
    source venv/Scripts/activate
elif [ -d "venv/bin" ]; then
    echo "🐧 Mendeteksi Linux..."
    source venv/bin/activate
else
    echo "❌ Error: Folder venv ditemukan tapi tidak bisa diaktivasi."
    exit 1
fi

# 5. Install Dependencies
echo "📥 Menginstall requirements..."
pip install --upgrade pip
pip install pyserial pyTelegramBotAPI opencv-python

# 6. Jalankan Bridge
echo "------------------------------------------------"
echo "⚡ MENJALANKAN BRIDGE..."
echo "------------------------------------------------"
$PY_CMD bridge_picoclaw.py
