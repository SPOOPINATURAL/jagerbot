import os
import re
import json
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
import config
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from collections import defaultdict
from difflib import get_close_matches

AlertsDict = Dict[str, List[Dict[str, Any]]]
CooldownKey = Tuple[int, str]
JsonData = Dict[str, Any]
logger = logging.getLogger(__name__)
# jsons
class FileHelper:
    @staticmethod
    def load_json_file(path: str) -> JsonData:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading JSON file {path}: {e}")
        return {}

    @staticmethod
    def save_json_file(path: str, data: JsonData) -> None:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving JSON file {path}: {e}")


# cooldowns
class CooldownManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.cooldowns = {}
        return cls._instance

    def __init__(self):
        self.cooldowns: Dict[CooldownKey, datetime] = {}

    def check_cooldown(self, user_id: int, command_name: str) -> Tuple[bool, int]:
        key = (user_id, command_name)
        now = datetime.now()

        if key in self.cooldowns:
            expires = self.cooldowns[key]
            if expires and now < expires:
                return True, int((expires - now).total_seconds())
        return False, 0

    async def start_cooldown(self, user_id: int, command_name: str, cooldown_seconds: int) -> None:
        key = (user_id, command_name)
        self.cooldowns[key] = datetime.now() + timedelta(seconds=cooldown_seconds)

        await asyncio.sleep(cooldown_seconds)
        self.cooldowns.pop(key, None)
    async def cleanup_expired(self):
        now = datetime.now()
        expired = [
            key for key, expires in self.cooldowns.items()
            if now >= expires
        ]
        for key in expired:
            self.cooldowns.pop(key, None)



# tz stuff
class TimeHelper:

    UNIT_MULTIPLIERS = {
        'w': 7 * 24 * 60 * 60,
        'd': 24 * 60 * 60,
        'h': 60 * 60,
        'm': 60,
        's': 1,
    }

    @staticmethod
    def normalize_tz(tz_str: str) -> str:
        return config.SUPPORTED_TZ.get(tz_str.strip().upper(), tz_str)

    @staticmethod
    def parse_time(time_str: str) -> Optional[int]:
        if not time_str:
            return None

        try:
            time_str = time_str.strip().lower()
            pattern = re.findall(r"(\d+)([wdsmh])", time_str)

            if not pattern:
                return None

            total_seconds = 0
            for value, unit in pattern:
                if unit not in TimeHelper.UNIT_MULTIPLIERS:
                    logger.warning(f"Invalid time unit: {unit}")
                    continue
                try:
                    total_seconds += int(value) * TimeHelper.UNIT_MULTIPLIERS[unit]
                except ValueError:
                    logger.error(f"Invalid time value: {value}")
                    return None

            return total_seconds if total_seconds > 0 else None

        except Exception as e:
            logger.error(f"Error parsing time string '{time_str}': {e}")
            return None


# weather
class WeatherHelper:
    CONDITION_EMOJIS = {
        "clear": "☀️",
        "cloud": "☁️",
        "rain": "🌧️",
        "storm": "⛈️",
        "thunder": "⛈️",
        "snow": "❄️",
        "fog": "🌫️",
        "mist": "🌫️"
    }

    @staticmethod
    def get_weather_emoji(condition: str) -> str:
        condition = condition.lower()
        for key, emoji in WeatherHelper.CONDITION_EMOJIS.items():
            if key in condition:
                return emoji
        return "🌈"


# data/alias stuff
class DataHelper:
    @staticmethod
    async def safe_json_operation(func, *args, **kwargs):
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error in JSON operation: {e}")
            return None

    @staticmethod
    async def load_json_file(path: str) -> Optional[dict]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading file {path}: {e}")
            return None

    @staticmethod
    def find_match(data_dict: dict, search_term: str) -> Optional[dict]:
        if not data_dict:
            return None
        search_term = search_term.lower()
        for item in data_dict.values():
            if item.get('name', '').lower() == search_term:
                return item
            for item in data_dict.values():
                aliases = item.get('aliases', [])
                if any(search_term == alias.lower() for alias in aliases):
                    return item
        names = [(item.get('name', ''), item) for item in data_dict.values()]
        aliases = [(alias, item) for item in data_dict.values() for alias in item.get('aliases', [])]
        
        all_candidates = names + aliases
        match_names = [name.lower() for name, _ in all_candidates]
        close = get_close_matches(search_term, match_names, n=1, cutoff=0.6)
        if close:
            for name, item in all_candidates:
                if name.lower() == close[0]:
                    return item
        return None

    @staticmethod
    async def fetch_json(url: str, session: Optional[aiohttp.ClientSession], timeout: int = 5) -> Optional[Dict[str, Any]]:
        try:
            should_close = False
            if session is None:
                session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout))
                should_close = True

            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
            finally:
                if should_close and session and not session.closed:
                    await session.close()
        except Exception as e:
            logger.error(f"Error fetching JSON from {url}: {e}")
            return None



#alerts
class AlertManager:
    def __init__(self):
        self.alerts: AlertsDict = defaultdict(list)

    def validate_alert(self, alert: Dict[str, Any]) -> bool:
        required_fields = {'time', 'message'}
        return all(field in alert for field in required_fields)

    def add_alert(self, user_id: str, alert: Dict[str, Any]) -> bool:
        if not self.validate_alert(alert):
            logger.error(f"Invalid alert format: {alert}")
            return False

        self.alerts[user_id].append(alert)
        self.save_alerts()
        return True

    def remove_alert(self, user_id: str, alert_index: int) -> bool:
        try:
            if user_id in self.alerts and 0 <= alert_index < len(self.alerts[user_id]):
                self.alerts[user_id].pop(alert_index)
                self.save_alerts()
                return True
        except Exception as e:
            logger.error(f"Error removing alert: {e}")
        return False

    def load_alerts(self) -> AlertsDict:
        try:
            with open(config.ALERTS_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}

                data = json.loads(content)
                self.alerts = defaultdict(list)

                for user_id, user_alerts in data.items():
                    for alert in user_alerts:
                        alert['time'] = datetime.fromisoformat(alert['time'])
                    self.alerts[user_id] = user_alerts

                return self.alerts

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading alerts: {e}")
            return {}

    def save_alerts(self, alerts: AlertsDict) -> None:
        try:
            os.makedirs(config.DATA_FOLDER, exist_ok=True)
            with open(config.ALERTS_FILE, "w", encoding="utf-8") as f:
                to_save = {
                    user_id: [
                        {**alert, 'time': alert['time'].isoformat()}
                        for alert in user_alerts
                    ]
                    for user_id, user_alerts in self.alerts.items()
                }
                json.dump(to_save, f, indent=2)

        except IOError as e:
            logger.error(f"Error saving alerts: {e}")


def load_all_json_from_folder(folder: str = "data") -> JsonData:
    data = {}
    try:
        for filename in os.listdir(folder):
            if filename.endswith(".json"):
                path = os.path.join(folder, filename)
                key = os.path.splitext(filename)[0]
                data[key] = FileHelper.load_json_file(path)
    except OSError as e:
        logger.error(f"Error loading JSONs from folder {folder}: {e}")
    return data

async def cleanup() -> None:
    try:
        await CooldownManager().cleanup_expired()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")