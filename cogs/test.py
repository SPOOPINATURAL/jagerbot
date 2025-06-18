from discord.ext import commands
import discord

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.add_command(
            discord.SlashCommandGroup(name="testgroup", description="Test group")
        )
    @commands.slash_command(name='hello', description="Hello!")
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Hallo {ctx.user.mention} :)")

def setup(bot):
    bot.add_cog(TestCog(bot))