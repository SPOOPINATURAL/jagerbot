import logging
from discord.ext import commands
import aiohttp
import discord
from typing import Optional

logger = logging.getLogger(__name__)


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def cog_unload(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx):
        try:
            logger.info("Starting global command sync...")
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Synced {len(synced)} command(s) globally.")
            logger.info(f"Synced {len(synced)} commands globally")
        except Exception as e:
            error_msg = f"❌ Failed to sync commands: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await ctx.send(error_msg)

    @sync.error
    async def sync_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")
        else:
            logger.error(f"Unexpected error in sync command: {error}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred.")

    @commands.is_owner()
    @commands.command(name='clearsync')
    async def clear_commands(self, ctx: commands.Context):
        """Clear and resync all commands"""
        await ctx.send("Clearing commands...")
        if self.bot.is_dev:
            guild = discord.Object(id=self.bot.config.TEST_GUILD_ID)
            self.bot.tree.clear_commands(guild=guild)
            await self.bot.tree.sync(guild=guild)
        else:
            self.bot.tree.clear_commands()
            await self.bot.tree.sync()
        await ctx.send("✅ Commands cleared and resynced!")


async def setup(bot):
    await bot.add_cog(Owner(bot))