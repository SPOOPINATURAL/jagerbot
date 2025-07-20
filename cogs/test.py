import discord
from discord.ext import commands,bridge
import logging

logger = logging.getLogger(__name__)
test = bridge.BridgeCommandGroup("test", description="Test commands")
class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("TestCog initialized")

    @test.command(name="ping", description="Ping command")
    async def ping(self, ctx):
        await ctx.respond("Pong!")

def setup(bot: commands.Bot):
    logger.info("✅ Loaded TestCog")
    bot.add_cog(TestCog(bot))
