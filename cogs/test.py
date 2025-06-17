from discord.ext import commands
import discord

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="group")
    async def group(self, ctx: discord.ApplicationContext):
        pass

    @group.sub_command(name="sub")
    async def sub(self, ctx: discord.ApplicationContext):
        await ctx.respond("Subcommand works!")

async def setup(bot):
    await bot.add_cog(TestCog(bot))