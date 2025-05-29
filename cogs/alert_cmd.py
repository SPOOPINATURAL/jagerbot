import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from dateutil import parser as dateparser
from utils.alerts_storage import alerts, save_alerts
from utils.helpers import parse_time
from pytz import UTC

class AlertCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="alert", description="Set an alert for a specific event")
    @app_commands.describe(input_str="Alert details, e.g. 'Meeting at 15:00 recurring 1h'")
    async def alert(self, interaction: discord.Interaction, *, input_str: str):
        recurring = None
        if "recurring" in input_str:
            parts = input_str.rsplit("recurring", 1)
            input_str = parts[0].strip()
            recurring = parts[1].strip()

            if parse_time(recurring) is None:
                await interaction.response.send_message("❌ Invalid recurring time format! Use number + s/m/h.")
                return

        keywords = [' in ', ' at ', ' on ', ' tomorrow', ' today', ' next ', ' this ']
        split_pos = None
        for kw in keywords:
            pos = input_str.lower().find(kw)
            if pos != -1:
                split_pos = pos
                break

        if split_pos is not None:
            event = input_str[:split_pos].strip()
            datetime_str = input_str[split_pos:].strip()
        else:
            parts = input_str.split(maxsplit=1)
            event = parts[0]
            datetime_str = parts[1] if len(parts) > 1 else ""

        date = dateparser.parse(datetime_str, settings={'RETURN_AS_TIMEZONE_AWARE': True, 'TO_TIMEZONE': 'UTC'})
        if date is None:
            await interaction.response.send_message("❌ Couldn't parse the date/time. Try a different format.")
            return

        now = datetime.now(UTC)
        if date < now:
            await interaction.response.send_message("❌ The specified time is in the past.")
            return

        user_id = str(interaction.user.id)
        if user_id not in alerts:
            alerts[user_id] = []

        alerts[user_id].append({
            "event": event,
            "time": date,
            "recurring": recurring
        })

        save_alerts()

        await interaction.response.send_message(
            f"✅ Alert for **{event}** set at {date.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            + (f", recurring every {recurring}" if recurring else "") + "."
        )

    @app_commands.command(name="cancelalerts", description="Cancel all your active alerts")
    async def cancelalerts(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id in alerts:
            del alerts[user_id]
            save_alerts()
            await interaction.response.send_message("🛑 All your alerts have been cancelled.")
        else:
            await interaction.response.send_message("ℹ️ You have no active alerts.")

    @app_commands.command(name="listalerts", description="List all your active alerts")
    async def listalerts(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in alerts or len(alerts[user_id]) == 0:
            await interaction.response.send_message("ℹ️ You have no active alerts.")
            return

        embed = discord.Embed(title=f"{interaction.user.name}'s Alerts", color=0x2ecc71)
        from datetime import datetime
        from pytz import UTC

        now = datetime.now(UTC)
        for i, alert in enumerate(alerts[user_id], 1):
            time_left = alert['time'] - now
            total_seconds = int(time_left.total_seconds())
            if total_seconds < 0:
                continue
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            time_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
            recur = f" (recurring every {alert['recurring']})" if alert.get('recurring') else ""
            embed.add_field(name=f"{i}. {alert['event']}", value=f"Triggers in {time_str}{recur}", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AlertCommands(bot))
