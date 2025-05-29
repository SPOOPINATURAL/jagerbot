import os
import json
import aiohttp
import asyncio
from datetime import datetime, timedelta
import config

# jsons

def load_json_file(path: str):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_json_file(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# cooldowns

cooldowns = {}

def check_cooldown(user_id, command_name, cooldown_seconds):
    key = (user_id, command_name)
    now = datetime.now()
    if key in cooldowns:
        expires = cooldowns[key]
        if now < expires:
            return True, (expires - now).seconds
    cooldowns[key] = now + timedelta(seconds=cooldown_seconds)
    return False, 0

async def start_cooldown_timer(user_id, command_name, cooldown_seconds, callback=None):
    key = (user_id, command_name)
    cooldowns[key] = datetime.now() + timedelta(seconds=cooldown_seconds)
    await asyncio.sleep(cooldown_seconds)
    if key in cooldowns:
        del cooldowns[key]
    if callback:
        await callback()

# tz stuff

def normalize_tz(tz_str):
    tz_str = tz_str.strip().upper()
    return config.SUPPORTED_TZ.get(tz_str, tz_str)

# parsing

def parse_time(time_str: str):
    units = {"s": 1, "m": 60, "h": 3600}
    try:
        amount = int(time_str[:-1])
        unit = time_str[-1].lower()
        return amount * units[unit]
    except (ValueError, KeyError):
        return None

# weather

def get_weather_emoji(condition: str) -> str:
    condition = condition.lower()
    if "clear" in condition:
        return "☀️"
    elif "cloud" in condition:
        return "☁️"
    elif "rain" in condition:
        return "🌧️"
    elif "storm" in condition or "thunder" in condition:
        return "⛈️"
    elif "snow" in condition:
        return "❄️"
    elif "fog" in condition or "mist" in condition:
        return "🌫️"
    else:
        return "🌈"

# data/alias stuff

def find_match(data_dict: dict, user_input: str):
    user_input = user_input.lower()
    for key, entry in data_dict.items():
        if user_input == key:
            return entry
        if "aliases" in entry and user_input in [a.lower() for a in entry["aliases"]]:
            return entry
    return None

# http

async def fetch_json(url: str, timeout: int = 5):
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_obj) as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            return {}

#alerts
alerts = {}
def load_alerts():
    global alerts
    try:
        with open(config.ALERTS_FILE, "r") as f:
            data = json.load(f)
            for user_id, user_alerts in data.items():
                for alert in user_alerts:
                    alert['time'] = datetime.fromisoformat(alert['time'])
            alerts = data
    except FileNotFoundError:
        alerts = {}

def save_alerts():
    os.makedirs(config.DATA_FOLDER, exist_ok=True)
    with open(config.ALERTS_FILE, "w", encoding="utf-8") as f:
        to_save = {}
        for user_id, user_alerts in alerts.items():
            to_save[user_id] = []
            for alert in user_alerts:
                a = alert.copy()
                a['time'] = a['time'].isoformat()
                to_save[user_id].append(a)
        json.dump(to_save, f, indent=2)

#load jsons
def load_all_json_from_folder(folder="data"):
    data = {}
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            path = os.path.join(folder, filename)
            with open(path, "r", encoding="utf-8") as f:
                key = os.path.splitext(filename)[0]  # filename without .json
                data[key] = json.load(f)
    return data