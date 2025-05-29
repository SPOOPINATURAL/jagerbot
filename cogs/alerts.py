import logging
from discord.ext import commands, tasks
from utils.helpers import load_alerts, save_alerts, parse_time
from datetime import datetime, timedelta
import discord

logger = logging.getLogger(__name__)

class AlertCog(commands.Cog):
    async def cog_load(self):
        if not self.check_alerts.is_running():
            self.check_alerts.start()

    def __init__(self, bot):
        self.bot = bot
        self.alerts = load_alerts()

    @tasks.loop(seconds=30)
    async def check_alerts(self):
        now = datetime.now()
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
                        seconds = parse_time(alarm['recurring'])
                        if seconds:
                            alarm['time'] += timedelta(seconds=seconds)
                    else:
                        to_remove.append((user_id, alarm))

        for user_id, alarm in to_remove:
            self.alerts[user_id].remove(alarm)
            if not self.alerts[user_id]:
                del self.alerts[user_id]

        save_alerts(self.alerts)

    @check_alerts.before_loop
    async def before_check_alerts(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AlertCog(bot))