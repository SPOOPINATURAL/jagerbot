import random
import discord
from discord.ext import commands,bridge

class FrostCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @bridge.bridge_command(name="frost", description="Frosty L's")
    async def frost(self, ctx: discord.ApplicationContext):
        frostl = random.randint(1, 1_000_000)
        await ctx.respond(f"frosty took another L — he's at {frostl:,} L's now")

def setup(bot: commands.Bot):
    bot.add_cog(FrostCog(bot))
