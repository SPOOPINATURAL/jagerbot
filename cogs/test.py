from discord.ext import commands
import discord

class TestCog(commands.Cog):
    @commands.slash_command(name='hello', description="Hello!")
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Hallo {ctx.user.mention} :)")

def setup(bot):
    bot.add_cog(TestCog(bot))