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
def serialize_alerts(alerts_dict):
    serialized = {}
    for user_id, user_alerts in alerts_dict.items():
        serialized[user_id] = []
        for alert in user_alerts:
            alert_copy = alert.copy()
            alert_copy['time'] = alert['time'].isoformat()
            serialized[user_id].append(alert_copy)
    return serialized

def deserialize_alerts(alerts_dict):
    deserialized = defaultdict(list)
    for user_id, user_alerts in alerts_dict.items():
        for alert in user_alerts:
            alert['time'] = datetime.fromisoformat(alert['time'])
            deserialized[user_id].append(alert)
    return deserialized

class AlertCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alerts = defaultdict(list)

    async def cog_load(self):
        try:
            with open('data/alerts.json', 'r') as f:
                data = json.load(f)
                self.alerts = deserialize_alerts(data)
        except FileNotFoundError:
            self.alerts = defaultdict(list)
        except Exception as e:
            logger.error(f"Failed to load alerts: {e}")
            self.alerts = defaultdict(list)

        if not self.check_alerts.is_running():
            self.check_alerts.start()

    async def cog_unload(self):
        if self.check_alerts.is_running():
            self.check_alerts.cancel()

    def save_alerts(self):
        try:
            with open('data/alerts.json', 'w') as f:
                json.dump(serialize_alerts(self.alerts), f, indent=4)
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
                                alert['time'] = now + timedelta(seconds=seconds)
                        else:
                            to_remove.append((user_id, alert))

                    except Exception as e:
                        logger.error(f"Failed to send alert to {user_id}: {e}")
                        to_remove.append((user_id, alert))

        for user_id, alert in to_remove:
            if user_id in self.alerts:
                self.alerts[user_id].remove(alert)
                if not self.alerts[user_id]:
                    del self.alerts[user_id]

        self.save_alerts()

    @check_alerts.before_loop
    async def before_check_alerts(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AlertCog(bot))
