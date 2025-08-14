#!/bin/zsh
set -euo pipefail
cd /mnt/ssd/jagerbot
PULL_OUTPUT=$(git pull origin main)

if [[ "$PULL_OUTPUT" == *"Already up to date."* ]]; then
    exit 0
fi

find . -type d -name "__pycache__" -exec rm -rf {} +
/mnt/ssd/jagerbot/venv/bin/pip install --upgrade -r requirements.txt
sudo systemctl restart jagerbot.service
