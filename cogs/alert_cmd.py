import discord
import dateparser
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from pytz import UTC
from functools import partial

from utils.helpers import parse_time
from utils.alerts_storage import alerts, save_alerts

from views.alert_modal import AlertModal
from views.alert_view import AlertItemView

class AlertCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="alert", description="Set an alert via interactive modal")
    async def alert(self, interaction: discord.Interaction):
        async def on_submit(interaction, event, time_str, recurring_str):
            #parse
            try:
                date = dateparser.parse(time_str, settings={'RETURN_AS_TIMEZONE_AWARE': True, 'TO_TIMEZONE': 'UTC', 'TIMEZONE': 'UTC'}) # type: ignore
            except Exception:
                date = None

            if date is None:
                seconds = parse_time(time_str)
                if seconds:
                    date = datetime.now(UTC) + timedelta(seconds=seconds)

            if date is None:
                await interaction.response.send_message("❌ Couldn't parse the date/time.", ephemeral=True)
                return
            if date < datetime.now(UTC):
                await interaction.response.send_message("❌ Time is invalid or in the past.", ephemeral=True)
                return

            if date.tzinfo is None:
                date = date.replace(tzinfo=UTC)

            recurring = recurring_str.strip().lower() if recurring_str else None
            if recurring and parse_time(recurring) is None:
                await interaction.response.send_message("❌ Invalid recurring time format! Use e.g. 10m, 1h.", ephemeral=True)
                return

            user_id = str(interaction.user.id)
            if user_id not in alerts:
                alerts[user_id] = []

            alerts[user_id].append({
                "event": event or "Unnamed Event",
                "time": date,
                "recurring": recurring
            })
            save_alerts()

            await interaction.response.send_message(
                f"✅ Alert for **{event or 'Unnamed Event'}** set at {date.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                + (f", recurring every {recurring}" if recurring else "") + ".",
                ephemeral=True
            )

        modal = AlertModal(on_submit)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="listalerts", description="List your active alerts with controls")
    async def listalerts(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        user_alerts = alerts.get(user_id, [])
        if not user_alerts:
            await interaction.response.send_message("ℹ️ You have no active alerts.", ephemeral=True)
            return

        now = datetime.now(UTC)
        for i, alert in enumerate(user_alerts):
            time_left = alert['time'] - now
            total_seconds = int(time_left.total_seconds())
            if total_seconds < 0:
                continue
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            time_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
            recur = f" (recurring every {alert['recurring']})" if alert.get('recurring') else ""

            embed = discord.Embed(
                title=f"Alert {i+1}: {alert['event']}",
                description=f"Triggers in {time_str}{recur}",
                color=0x2ecc71
            )

            view = AlertItemView(
                cog=self,
                alert=alerts[user_id][i],
                alert_index=i,
                on_cancel=lambda interaction, idx=i: self.cancel_alert(interaction, idx),
                on_snooze=lambda interaction, idx=i: self.snooze_alert(interaction, idx)
            )

            await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="cancelalerts", description="Cancel all your active alerts")
    async def cancelalerts(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id in alerts:
            del alerts[user_id]
            save_alerts()
            await interaction.response.send_message("🛑 All your alerts have been cancelled.", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ You have no active alerts.", ephemeral=True)

    async def cancel_alert(self, interaction: discord.Interaction, _button: discord.ui.Button, alert_index: int):
        user_id = str(interaction.user.id)
        user_alerts = alerts.get(user_id, [])
        if not (0 <= alert_index < len(user_alerts)):
            await interaction.response.send_message("⚠️ That alert no longer exists.", ephemeral=True)
            return
        removed_alert = user_alerts.pop(alert_index)
        if not user_alerts:
            del alerts[user_id]

        save_alerts()
        await interaction.response.send_message(f"🗑️ Canceled alert: **{removed_alert['event']}**", ephemeral=True)

    async def snooze_alert(self, interaction: discord.Interaction, alert_index: int):
        user_id = str(interaction.user.id)
        user_alerts = alerts.get(user_id, [])
        if 0 <= alert_index < len(user_alerts):
            alert = user_alerts[alert_index]
            alert['time'] += timedelta(minutes=10)  # Snooze 10 minutes
            save_alerts()
            await interaction.response.send_message(f"😴 Snoozed alert **{alert['event']}** by 10 minutes.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid alert index.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AlertCommands(bot))
