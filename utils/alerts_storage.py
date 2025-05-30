import json
import copy
from pathlib import Path
from config import ALERTS_FILE as ALERTS_FILE_STR
from dateutil.parser import isoparse
from datetime import datetime, timezone

ALERTS_FILE = Path(ALERTS_FILE_STR)
alerts = {}

def load_alerts():
    global alerts
    if ALERTS_FILE.exists():
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                alerts_raw = json.load(f)
            alerts = {}
            for user_id, user_alerts in alerts_raw.items():
                alerts[user_id] = []
                for alert in user_alerts:
                    alert['time'] = isoparse(alert['time'])
                    if alert_time.tzinfo is None:
                        alert_time = alert_time.replace(tzinfo=timezone.utc)
                    else:
                        alert_time = alert_time.astimezone(timezone.utc)
                    alerts[user_id].append({
                        "event": alert.get("event", "Unnamed Event"),
                        "time": alert_time,
                        "recurring": alert.get("recurring")
                    })
        except Exception as e:
            print(f"Failed to load alerts: {e}")
            alerts = {}
    else:
        alerts = {}
    return alerts

def save_alerts():
    try:
        to_save = copy.deepcopy(alerts)
        for user_id, user_alerts in to_save.items():
            for alert in user_alerts:
                alert['time'] = alert['time'].astimezone(timezone.utc).isoformat()
        ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
    except Exception as e:
        print(f"Failed to save alerts: {e}")


