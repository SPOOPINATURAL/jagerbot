#!/bin/zsh
set -e
cd /home/spoopinatural/jagerbot
git pull origin main
git rm --cached -r __pycache__/
git rm --cached -r cogs/__pycache__/
git rm --cached -r utils/__pycache__/
find . -type d -name "__pycache__" -exec rm -rf {} +
source ~/jagerbot/venv/bin/activate
pip install -U -r requirements.txt
sudo systemctl restart jagerbot.service
