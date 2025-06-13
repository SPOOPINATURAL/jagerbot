import logging
from discord.ext import commands
import discord
from typing import Optional
from discord import app_commands

logger = logging.getLogger(__name__)

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.id in self.bot.config.OWNER_IDS

    @commands.command(name='sync')
    @commands.is_owner()
    async def sync_command(self, ctx: commands.Context):
        await ctx.send("🔄 Syncing commands globally...")

        try:
            self.bot.tree.clear_commands(guild=None)
            await self.bot.tree.sync()

            synced_cmds = await self.bot.tree.fetch_commands()
            cmd_count = len(synced_cmds)

            await ctx.send(f"✅ Synced {cmd_count} commands globally.")
            logger.info(f"Manually synced {cmd_count} commands globally.")
        except Exception as e:
            await ctx.send(f"❌ Sync failed: {e}")
            logger.error("Manual sync failed", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
