import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="test", description="Test command group")
    async def test(self, ctx: discord.ApplicationContext):
        await ctx.respond("Use a subcommand like `/test hello`")

    @test.sub_command(name="hello", description="Say hello!")
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Hallo {ctx.user.mention} :)")

    @test.sub_command(name="bye", description="Say goodbye!")
    async def bye(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Tschüss {ctx.user.mention} 👋")

def setup(bot):
    bot.add_cog(TestCog(bot))
    logger.info("✅ Loaded TestCog")