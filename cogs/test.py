import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="test", description="Test command group", invoke_without_command=True)
    async def test(self, ctx: commands.Context):
        await ctx.respond("Use a subcommand, like `/test hello`")

    @test.command(name="hello", description="Say hello!")
    async def hello(self, ctx: commands.Context):
        await ctx.respond(f"Hallo {ctx.author.mention} :)")

def setup(bot):
    bot.add_cog(TestCog(bot))
