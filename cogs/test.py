import discord
from discord.ext import commands,bridge
import logging

logger = logging.getLogger(__name__)

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("TestCog initialized")

    @bridge.bridge_command(name="ping", description="Ping command")
    async def ping(self, ctx):
        await ctx.respond("Pong!")

async def setup(bot):
    logger.info("✅ Loaded TestCog")
    await bot.add_cog(TestCog(bot))
