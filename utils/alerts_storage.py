import json
import copy
from pathlib import Path
from config import ALERTS_FILE as ALERTS_FILE_STR
from dateutil.parser import isoparse

ALERTS_FILE = Path(ALERTS_FILE_STR)
alerts = {}

def load_alerts():
    global alerts
    if ALERTS_FILE.exists():
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                alerts = json.load(f)
            for user_id in alerts:
                for alert in alerts[user_id]:
                    alert['time'] = isoparse(alert['time'])
        except Exception as e:
            print(f"Failed to load alerts: {e}")
            alerts = {}
    else:
        alerts = {}
    return alerts

def save_alerts():
    try:
        to_save = copy.deepcopy(alerts)
        for user_id in to_save:
            for alert in to_save[user_id]:
                alert['time'] = alert['time'].isoformat()
        ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
    except Exception as e:
        print(f"Failed to save alerts: {e}")


