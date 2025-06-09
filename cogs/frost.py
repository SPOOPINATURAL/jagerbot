import random
from discord.ext import commands

class FrostCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content.startswith('$frost'):
            print(f"$frost was triggered by {message.author.id} | {message.author.name}")
            frostl = random.randint(1, 1_000_000)
            await message.channel.send(f"frosty took another L — he's at {frostl:,} L's now")
        await self.bot.process_commands(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(FrostCog(bot))
