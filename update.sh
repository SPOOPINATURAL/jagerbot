#!/bin/zsh
cd /home/spoopinatural/jagerbot
git pull origin main
find . -type d -name "__pycache__" -exec rm -rf {} +
~/jagerbot/venv/bin/pip install -U -r requirements.txt
sudo systemctl restart jagerbot.service
