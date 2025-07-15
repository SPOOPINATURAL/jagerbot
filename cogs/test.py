import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("TestCog initialized")

    @commands.slash_command(name="ping", description="Ping command")
    async def ping(self, ctx):
        await ctx.respond("Pong!")

def setup(bot):
    logger.info("✅ Loaded TestCog")
    bot.add_cog(TestCog(bot))
