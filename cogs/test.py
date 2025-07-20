import discord
from discord.ext import commands,bridge
import logging

logger = logging.getLogger(__name__)
class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("TestCog initialized")
    
    @bridge.bridge_group()
    def test(self, ctx):
        pass
    
    @bridge.bridge_group()
    @bridge.map_to(name="ping", description="test cmd")
    async def ping(self, ctx):
        await ctx.respond("balls")

def setup(bot: commands.Bot):
    logger.info("✅ Loaded TestCog")
    bot.add_cog(TestCog(bot))
