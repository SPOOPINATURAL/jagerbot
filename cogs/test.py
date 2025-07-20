import discord
from discord.ext import commands,bridge
import logging

logger = logging.getLogger(__name__)
class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("TestCog initialized")
    
    @bridge.group()
    async def test(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use a subcommand like `/test hello`")

    @test.command(name="ping", description="Ping command")
    async def ping(self, ctx):
        await ctx.respond("Pong!")

def setup(bot: commands.Bot):
    logger.info("✅ Loaded TestCog")
    bot.add_cog(TestCog(bot))
