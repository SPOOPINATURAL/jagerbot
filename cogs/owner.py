from discord.ext import commands
import discord

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(self, ctx):
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Synced {len(synced)} command(s) globally.")
        except Exception as e:
            await ctx.send(f"❌ Error syncing commands: {e}")

async def setup(bot):
    await bot.add_cog(Owner(bot))
