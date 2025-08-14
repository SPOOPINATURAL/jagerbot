#!/bin/zsh
set -euo pipefail
cd /mnt/ssd/jagerbot
PULL_OUTPUT=$(git pull origin main)

BOT_DIR="/mnt/ssd/jagerbot"
VENV_DIR="$BOT_DIR/venv"

if [[ "$PULL_OUTPUT" == *"Already up to date."* ]]; then
    exit 0
fi

if [[ ! -x "$VENV_DIR/bin/python3" ]] || grep -q "/home/spoopinatural/jagerbot" "$VENV_DIR/bin/activate"; then
    echo "[WARN] venv broken, rebuilding"
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "[INFO] Updating dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade -r requirements.txt
fi

find . -type d -name "__pycache__" -exec rm -rf {} +
/mnt/ssd/jagerbot/venv/bin/pip install --upgrade -r requirements.txt
sudo systemctl restart jagerbot.service
