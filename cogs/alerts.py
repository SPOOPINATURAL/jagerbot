import logging

import pytz
from discord.ext import commands, tasks
from utils.helpers import load_alerts, save_alerts, parse_time
from datetime import datetime, timedelta, timezone
import discord

logger = logging.getLogger(__name__)
UTC = pytz.UTC

class AlertCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        global alerts
        alerts = load_alerts()
        self.alerts = alerts

    async def cog_load(self):
        if not self.check_alerts.is_running():
            self.check_alerts.start()

    @tasks.loop(seconds=30)
    async def check_alerts(self):
        global alerts
        now = datetime.now(timezone.utc)
        to_remove = []

        for user_id, user_alerts in list(self.alerts.items()):
            user = self.bot.get_user(int(user_id))
            if not user:
                continue
            for alert in list(user_alerts):
                alert_time = alert['time']
                if alert_time.tzinfo is None:
                    alert_time = alert_time.replace(tzinfo=timezone.utc)
                else:
                    alert_time = alert_time.astimezone(timezone.utc)
                if alert_time <= now:
                    try:
                        await user.send(f"⏰ Reminder: **{alert['event']}**")
                    except Exception:
                        pass
                    if alert.get('recurring'):
                        seconds = parse_time(alert['recurring'])
                        if seconds:
                            alert['time'] + timedelta(seconds=seconds)
                    else:
                        to_remove.append((user_id, alert))

        for user_id, alert in to_remove:
            self.alerts[user_id].remove(alert)
            if not self.alerts[user_id]:
                del self.alerts[user_id]

        save_alerts(self.alerts)

    @check_alerts.before_loop
    async def before_check_alerts(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AlertCog(bot))