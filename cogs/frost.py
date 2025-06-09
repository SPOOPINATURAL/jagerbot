import random
from discord.ext import commands

class FrostCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="frost", help="Check how many L's Frost has taken")
    async def frost(self, ctx: commands.Context):
        frostl = random.randint(1, 1_000_000)
        await ctx.send(f"frosty took another L — he's at {frostl:,} L's now")

async def setup(bot: commands.Bot):
    await bot.add_cog(FrostCog(bot))
