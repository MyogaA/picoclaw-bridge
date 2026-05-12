#!/bin/bash

REPO_URL="https://github.com/MyogaA/picoclaw-bridge.git"
PROJECT_DIR="picoclaw-bridge"

echo "Setup Picoclaw..."

# 1. Download Repo
if [ ! -d "$PROJECT_DIR" ] && [ ! -f "bridge_picoclaw.py" ]; then
    git clone $REPO_URL
    cd $PROJECT_DIR || exit
elif [ -d "$PROJECT_DIR" ]; then
    cd $PROJECT_DIR || exit
fi

# 2. Cari Python
if command -v python &>/dev/null; then
    PY_BIN="python"
elif command -v python3 &>/dev/null; then
    PY_BIN="python3"
else
    echo "Python tidak ditemukan!"
    exit 1
fi

# 3. Virtual Environment
if [ ! -d "venv" ]; then
    $PY_BIN -m venv venv
fi

# 4. Aktivasi (Windows vs Linux)
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# 5. Install Library
pip install --upgrade pip
pip install pyserial pyTelegramBotAPI opencv-python

# 6. Run Bridge
export PYTHONIOENCODING=utf-8
$PY_BIN bridge_picoclaw.py
