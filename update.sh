#!/bin/zsh
cd /home/spoopinatural/jagerbot
git pull origin main
find . -type d -name "__pycache__" -exec rm -rf {} +
source ~/jagerbot/venv/bin/activate
pip install -U -r requirements.txt
sudo systemctl restart jagerbot.service
