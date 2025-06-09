#!/bin/bash
cd /home/spoopinatural/jagerbot
git pull origin main
sudo systemctl restart jagerbot
