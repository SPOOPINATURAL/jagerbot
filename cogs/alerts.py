import logging
import json
import pytz
from discord.ext import commands, tasks
from utils.helpers import AlertManager, TimeHelper
from datetime import datetime, timedelta, timezone
import discord
from collections import defaultdict


logger = logging.getLogger(__name__)
UTC = pytz.UTC

class AlertCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alerts = defaultdict(list)
        self.alert_manager = AlertManager()
        self.alerts = defaultdict(list)


    async def cog_load(self):
        if not self.check_alerts.is_running():
            self.check_alerts.start()

    async def cog_unload(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    @classmethod
    def save_alerts(cls, alerts):
        try:
            with open('data/alerts.json', 'w') as f:
                json.dump(alerts, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving alerts: {e}")

    @tasks.loop(seconds=30)
    async def check_alerts(self):
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
                        await user.send(
                            embed=discord.Embed(
                                title="⏰ Reminder",
                                description=f"**{alert['event']}**",
                                color=0x2ecc71
                            )
                        )

                        if alert.get('recurring'):
                            seconds = TimeHelper.parse_time(alert['recurring'])
                            if seconds:
                                alert['time'] = alert_time + timedelta(seconds=seconds)
                        else:
                            to_remove.append((user_id, alert))

                    except Exception as e:
                        logger.error(f"Failed to send alert to {user_id}: {e}")
                        continue

        for user_id, alert in to_remove:
            if user_id in self.alerts:
                self.alerts[user_id].remove(alert)
                if not self.alerts[user_id]:
                    del self.alerts[user_id]

        self.alert_manager.save_alerts(self.alert_manager.alerts)


    @check_alerts.before_loop
    async def before_check_alerts(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AlertCog(bot))