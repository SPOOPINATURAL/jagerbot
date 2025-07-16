import random
from discord.ext import commands,bridge

class FrostCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @bridge.bridge_command(name="frost")
    async def frost(self, ctx: commands.Context):
        frostl = random.randint(1, 1_000_000)
        await ctx.send(f"frosty took another L — he's at {frostl:,} L's now")

async def setup(bot):
    await bot.add_cog(FrostCog(bot))
