import logging
from discord.ext import commands
from typing import Optional
from discord import Object

logger = logging.getLogger(__name__)

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.id in self.bot.config.OWNER_IDS

    @commands.command(name='sync')
    @commands.is_owner()
    async def sync_command(self, ctx: commands.Context, scope: Optional[str] = None):
        """
        Usage:
        $sync           - Sync globally (may take up to 1 hour)
        $sync guilds    - Sync to all guilds in config.ALLOWED_GUILD_IDS (instant)
        $sync guild     - Sync to this guild only (instant)
        """
        if scope == "guilds":
            total = 0
            for gid in self.bot.config.ALLOWED_GUILD_IDS:
                await ctx.send(f"🔄 Syncing commands to guild {gid}...")
                synced = await self.bot.tree.sync(guild=Object(id=gid))
                await ctx.send(f"✅ Synced {len(synced)} commands to guild {gid}: {[cmd.name for cmd in synced]}")
                total += len(synced)
            await ctx.send(f"✅ Finished syncing to all guilds. Total commands synced: {total}")
            logger.info(f"Manually synced commands to all allowed guilds.")
        elif scope == "guild":
            if ctx.guild:
                await ctx.send(f"🔄 Syncing commands to this guild ({ctx.guild.id})...")
                synced = await self.bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"✅ Synced {len(synced)} commands to this guild: {[cmd.name for cmd in synced]}")
                logger.info(f"Manually synced commands to guild {ctx.guild.id}.")
            else:
                await ctx.send("❌ This command must be used in a server.")
        else:
            await ctx.send("🔄 Syncing commands globally...")
            try:
                synced = await self.bot.tree.sync()
                fetched_cmds = await self.bot.tree.fetch_commands()
                cmd_names = [cmd.name for cmd in fetched_cmds]
                await ctx.send(f"✅ Synced {len(fetched_cmds)} global commands: {cmd_names}")
                logger.info(f"Manually synced {len(fetched_cmds)} commands globally: {cmd_names}")
            except Exception as e:
                await ctx.send(f"❌ Sync failed: {e}")
                logger.error("Manual sync failed", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
