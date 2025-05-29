import logging
from discord.ext import tasks
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AlertChecker:
    def __init__(self, bot, alerts, UTC, parse_time, save_alerts):
        self.bot = bot
        self.alerts = alerts
        self.UTC = UTC
        self.parse_time = parse_time
        self.save_alerts = save_alerts

@tasks.loop(seconds=30)
async def check_alerts(self):
    now = datetime.now(self.UTC)
    to_remove = []

    for user_id, user_alerts in list(self.alerts.items()):
        user = self.bot.get_user(int(user_id))
        if not user:
            continue
        for alarm in list(user_alerts):
            if alarm['time'] <= now:
                try:
                    await user.send(f"⏰ Reminder: **{alarm['event']}**")
                except Exception:
                    pass
                if alarm.get('recurring'):
                    seconds = self.parse_time(alarm['recurring'])
                    if seconds:
                        alarm['time'] += timedelta(seconds=seconds)
                else:
                    to_remove.append((user_id, alarm))

    for user_id, alarm in to_remove:
        self.alerts[user_id].remove(alarm)
        if not self.alerts[user_id]:
            del self.alerts[user_id]

    self.save_alerts()

    def start(self):
        if not self.check_alerts.is_running():
            self.check_alerts.start()