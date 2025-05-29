import json
from pathlib import Path
from config import ALERTS_FILE

alerts = {}

def load_alerts():
    global alerts
    if ALERTS_FILE.exists():
        try:
            with open(ALERTS_FILE, "r") as f:
                alerts = json.load(f)
            from dateutil.parser import isoparse
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
        import copy
        to_save = copy.deepcopy(alerts)
        for user_id in to_save:
            for alert in to_save[user_id]:
                alert['time'] = alert['time'].isoformat()
        with open(ALERTS_FILE, "w") as f:
            json.dump(to_save, f, indent=2)
    except Exception as e:
        print(f"Failed to save alerts: {e}")
