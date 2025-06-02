import logging
from discord.ext import commands
import discord
import asyncio
from typing import Optional
from discord import app_commands

logger = logging.getLogger(__name__)

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.id in self.bot.config.OWNER_IDS

    @commands.command(name='sync')
    @commands.is_owner()
    async def sync_command(self, ctx: commands.Context, spec: Optional[str] = None):
        async def sync_to(guild_id=None):
            try:
                if guild_id:
                    guild = discord.Object(id=guild_id)
                    self.bot.tree.clear_commands(guild=guild)
                    self.bot.tree.copy_global_to(guild=guild)
                    await self.bot.tree.sync(guild=guild)
                else:
                    self.bot.tree.clear_commands()
                    await self.bot.tree.sync()
                return True
            except Exception as e:
                logger.error(f"Sync failed: {e}")
                return False

        await ctx.send("🔄 Starting sync...")

        try:
            commands = []
            for cmd in self.bot.tree._get_all_commands():
                if isinstance(cmd, app_commands.Group):
                    commands.extend(cmd.commands)
                else:
                    commands.append(cmd)

            total_commands = len(commands)
            logger.info(f"Found {total_commands} commands to sync")

            batch_size = 25
            if self.bot.is_dev:
                for guild_id in self.bot.config.ALLOWED_GUILD_IDS:
                    for i in range(0, total_commands, batch_size):
                        batch = commands[i:i + batch_size]
                        success = await sync_to(guild_id)
                        if success:
                            await ctx.send(f"✅ Synced batch {i//batch_size + 1} ({min(i + batch_size, total_commands)}/{total_commands}) to guild {guild_id}")
                        else:
                            await ctx.send(f"❌ Failed to sync batch {i//batch_size + 1} to guild {guild_id}")
                            return
                        await asyncio.sleep(1)
            else:
                for i in range(0, total_commands, batch_size):
                    batch = commands[i:i + batch_size]
                    success = await sync_to()
                    if success:
                        await ctx.send(f"✅ Synced batch {i//batch_size + 1} ({min(i + batch_size, total_commands)}/{total_commands}) globally")
                    else:
                        await ctx.send(f"❌ Failed to sync batch {i//batch_size + 1} globally")
                        return
                    await asyncio.sleep(1)

            await ctx.send(f"✅ Successfully synced {total_commands} commands!")

        except Exception as e:
            await ctx.send(f"❌ Sync failed: {str(e)}")
            logger.error(f"Sync error: {e}", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
