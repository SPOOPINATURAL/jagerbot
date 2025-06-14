#!/bin/zsh
cd /home/spoopinatural/jagerbot
git pull origin main
find . -type d -name "__pycache__" -exec rm -rf {} +
sudo systemctl restart jagerbot
