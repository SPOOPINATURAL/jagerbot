import logging
from discord.ext import commands
from typing import Optional
from discord import app_commands

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
        $sync --force   - Force clear and sync globally
        """
        if scope == "guilds":
            total = 0
            for gid in self.bot.config.ALLOWED_GUILD_IDS:
                await ctx.send(f"🔄 Syncing commands to guild {gid}...")
                synced = await self.bot.tree.sync(guild=Object(id=gid))
                await ctx.send(f"✅ Synced {len(synced)} commands to guild {gid}.")
                total += len(synced)
            await ctx.send(f"✅ Finished syncing to all guilds. Total commands synced: {total}")
            logger.info(f"Manually synced commands to all allowed guilds.")
        elif scope == "guild":
            if ctx.guild:
                await ctx.send(f"🔄 Syncing commands to this guild ({ctx.guild.id})...")
                synced = await self.bot.tree.sync(guild=ctx.guild)
                await ctx.send(f"✅ Synced {len(synced)} commands to this guild.")
                logger.info(f"Manually synced commands to guild {ctx.guild.id}.")
            else:
                await ctx.send("❌ This command must be used in a server.")
        else:
            force_sync = scope == "--force"
            await ctx.send("🔄 Syncing commands globally...")
            try:
                if force_sync:
                    self.bot.tree.clear_commands(guild=None)
                await self.bot.tree.sync()
                synced_cmds = await self.bot.tree.fetch_commands()
                cmd_count = len(synced_cmds)
                await ctx.send(f"✅ Synced {cmd_count} commands globally.")
                logger.info(f"Manually synced {cmd_count} commands globally.")
            except Exception as e:
                await ctx.send(f"❌ Sync failed: {e}")
                logger.error("Manual sync failed", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
