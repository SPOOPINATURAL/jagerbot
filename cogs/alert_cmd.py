import logging
import discord
import aiohttp
from discord.ext import commands
from datetime import datetime, timedelta
from pytz import UTC
from typing import Optional, List, Dict, Any

import dateparser

from utils.helpers import TimeHelper
from utils.alerts_storage import alerts, save_alerts
from utils.embed_builder import EmbedBuilder
from views.alert_modal import AlertModal
from views.alert_view import AlertItemView

logger = logging.getLogger(__name__)

class AlertCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._configure_limits()
        self.session = None
        super().__init__()

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

    async def cog_unload(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    def _configure_limits(self) -> None:
        self.max_alerts = 10
        self.max_event_length = 100
        self.min_recurring_seconds = 60

    @staticmethod
    async def validate_time(time_str: str) -> Optional[datetime]:
        try:
            date = dateparser.parse(
                time_str,
                settings={
                    'RETURN_AS_TIMEZONE_AWARE': True,
                    'TO_TIMEZONE': 'UTC',
                    'TIMEZONE': 'UTC',
                    'PREFER_DATES_FROM': 'future'
                }
            )
        except Exception as e:
            logger.error(f"Date parsing error: {e}")
            date = None

        if date is None:
            seconds = TimeHelper.parse_time(time_str)
            if seconds:
                date = datetime.now(UTC) + timedelta(seconds=seconds)

        if date and date.tzinfo is None:
            date = date.replace(tzinfo=UTC)
        elif date:
            date = date.astimezone(UTC)

        return date

    async def validate_recurring(self, recurring_str: str) -> Optional[str]:
        if not recurring_str:
            return None

        recurring = recurring_str.strip().lower()
        seconds = TimeHelper.parse_time(recurring)

        if seconds is None or seconds < self.min_recurring_seconds:
            return None

        return recurring

    @staticmethod
    def create_alert_embed(event: str, date: datetime, recurring: Optional[str]) -> discord.Embed:
        return EmbedBuilder.success(
            message=(
                f"**Event:** {event}\n"
                f"**Time:** {date.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"**Recurring:** {recurring if recurring else 'No'}"
            ),
            title="✅ Alert Set"
        )

    async def handle_alert_creation(
        self,
        interaction: discord.Interaction,
        event: str,
        time_str: str,
        recurring_str: str
    ) -> None:
        try:
            if len(event) > self.max_event_length:
                await interaction.response.send_message(
                    f"❌ Event name too long (max {self.max_event_length} characters).",
                    ephemeral=True
                )
                return

            date = await self.validate_time(time_str)
            if not date:
                await interaction.response.send_message(
                    "❌ Invalid time format. Examples:\n"
                    "• tomorrow at 3pm\n"
                    "• in 2 hours\n"
                    "• 30m\n"
                    "• 2023-12-25 15:00",
                    ephemeral=True
                )
                return

            if date < datetime.now(UTC):
                await interaction.response.send_message(
                    "❌ Cannot set alerts in the past.",
                    ephemeral=True
                )
                return

            recurring = await self.validate_recurring(recurring_str)
            if recurring_str and not recurring:
                await interaction.response.send_message(
                    "❌ Invalid recurring format. Examples:\n"
                    "• 1h (hourly)\n"
                    "• 30m (every 30 min)\n"
                    "• 1d (daily)",
                    ephemeral=True
                )
                return

            user_id = str(interaction.user.id)
            if user_id not in alerts:
                alerts[user_id] = []
            elif len(alerts[user_id]) >= self.max_alerts:
                await interaction.response.send_message(
                    f"❌ Maximum alerts reached ({self.max_alerts}).",
                    ephemeral=True
                )
                return

            alerts[user_id].append({
                "event": event,
                "time": date,
                "recurring": recurring
            })
            save_alerts()

            embed = self.create_alert_embed(event, date, recurring)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Alert creation error: {e}")
            await interaction.response.send_message(
                "❌ Failed to create alert.",
                ephemeral=True
            )

    @commands.slash_command(name="alert", description="Set an alert via interactive modal")
    async def alert(self, ctx: discord.ApplicationContext):
        modal = AlertModal(self.handle_alert_creation)
        await ctx.interaction.response.send_modal(modal)

    @staticmethod
    def create_alert_list_embed(alert: dict, index: int, time_left: timedelta) -> discord.Embed:
        total_seconds = int(time_left.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        time_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
        recur = f" (recurring every {alert['recurring']})" if alert.get('recurring') else ""

        return EmbedBuilder.info(
            title=f"Alert {index+1}: {alert['event']}",
            description=f"Triggers in {time_str}{recur}"
        )

    def get_active_alerts(self, user_alerts: List[Dict[str, Any]]) -> List[tuple]:
        now = datetime.now(UTC)
        active_alerts = []

        for i, alert in enumerate(user_alerts):
            time_left = alert['time'] - now
            if time_left.total_seconds() < 0:
                continue

            embed = self.create_alert_list_embed(alert, i, time_left)
            view = AlertItemView(
                cog=self,
                alert=alert,
                alert_index=i,
                on_cancel=self.cancel_alert,
                on_snooze=self.snooze_alert
            )
            active_alerts.append((embed, view))

        return active_alerts

    @commands.slash_command(name="listalerts", description="List your active alerts with controls")
    async def listalerts(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        user_id = str(ctx.author.id)
        user_alerts = alerts.get(user_id, [])

        if not user_alerts:
            await ctx.followup.send(
                "ℹ️ You have no active alerts.",
                ephemeral=True
            )
            return

        active_alerts = self.get_active_alerts(user_alerts)

        if not active_alerts:
            await ctx.followup.send(
                "ℹ️ You have no active alerts.",
                ephemeral=True
            )
            return

        for embed, view in active_alerts:
            await ctx.followup.send(embed=embed, view=view)

    @commands.slash_command(name="cancelalerts", description="Cancel all your active alerts")
    async def cancelalerts(self, ctx: discord.ApplicationContext):
        user_id = str(ctx.author.id)
        if user_id in alerts:
            del alerts[user_id]
            save_alerts()
            await ctx.respond(
                "🛑 All your alerts have been cancelled.",
                ephemeral=True
            )
        else:
            await ctx.respond(
                "ℹ️ You have no active alerts.",
                ephemeral=True
            )

    @staticmethod
    async def cancel_alert(interaction: discord.Interaction, alert_index: int):
        user_id = str(interaction.user.id)
        user_alerts = alerts.get(user_id, [])

        if not (0 <= alert_index < len(user_alerts)):
            await interaction.response.send_message(
                "⚠️ That alert no longer exists.",
                ephemeral=True
            )
            return

        removed_alert = user_alerts.pop(alert_index)
        if not user_alerts:
            del alerts[user_id]

        save_alerts()
        await interaction.response.send_message(
            f"🗑️ Canceled alert: **{removed_alert['event']}**",
            ephemeral=True
        )

    @staticmethod
    async def snooze_alert(interaction: discord.Interaction, alert_index: int):
        user_id = str(interaction.user.id)
        user_alerts = alerts.get(user_id, [])

        if not (0 <= alert_index < len(user_alerts)):
            await interaction.response.send_message(
                "❌ Invalid alert index.",
                ephemeral=True
            )
            return

        alert = user_alerts[alert_index]
        alert['time'] += timedelta(minutes=10)
        save_alerts()

        await interaction.response.send_message(
            f"😴 Snoozed alert **{alert['event']}** by 10 minutes.",
            ephemeral=True
        )

def setup(bot: commands.Bot):
    bot.add_cog(AlertCommands(bot))