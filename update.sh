#!/bin/zsh
set -euo pipefail
cd /home/spoopinatural/jagerbot
git pull origin main
find . -type d -name "__pycache__" -exec rm -rf {} +
/home/spoopinatural/jagerbot/venv/bin/pip install --upgrade -r requirements.txt
sudo systemctl restart jagerbot.service
