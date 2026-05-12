#!/bin/bash

REPO_URL="https://github.com/MyogaA/picoclaw-bridge.git"
PROJECT_DIR="picoclaw-bridge"

echo "------------------------------------------------"
echo "🚀 Picoclaw Bootstrapper (Windows/Linux Fix)"
echo "------------------------------------------------"

# 1. Download/Update Repo
if [ ! -d "$PROJECT_DIR" ] && [ ! -f "bridge_picoclaw.py" ]; then
    git clone $REPO_URL
    cd $PROJECT_DIR || exit
elif [ -d "$PROJECT_DIR" ]; then
    cd $PROJECT_DIR || exit
fi

# 2. Cari perintah Python yang benar (Windows sering pakai 'python')
if command -v python &>/dev/null; then
    PY_BIN="python"
elif command -v python3 &>/dev/null; then
    PY_BIN="python3"
else
    echo "❌ Error: Python tidak ditemukan. Install Python & centang 'Add to PATH'."
    exit 1
fi

# 3. Buat VENV jika belum ada
if [ ! -d "venv" ]; then
    echo "🛠️ Membuat Virtual Environment..."
    $PY_BIN -m venv venv
fi

# 4. AKTIVASI (Logika deteksi folder yang sangat ketat)
if [ -f "venv/Scripts/activate" ]; then
    echo "💻 Windows detected, activating..."
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    echo "🐧 Linux detected, activating..."
    source venv/bin/activate
else
    echo "❌ Error: Folder venv/Scripts atau venv/bin tidak ditemukan!"
    exit 1
fi

# 5. Install requirements
echo "📥 Menginstall library..."
pip install --upgrade pip
pip install pyserial pyTelegramBotAPI opencv-python

# 6. Jalankan dengan encoding UTF-8 agar tidak error di Windows
echo "⚡ MENJALANKAN BRIDGE..."
export PYTHONIOENCODING=utf-8
$PY_BIN bridge_picoclaw.py
