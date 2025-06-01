import logging
from discord.ext import commands
import aiohttp
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
                    self.bot.tree.copy_global_to(guild=guild)
                    await self.bot.tree.sync(guild=guild)
                else:
                    await self.bot.tree.sync()
                return True
            except Exception as e:
                logger.error(f"Sync failed: {e}")
                return False

        await ctx.send("🔄 Starting sync...")

        try:
            self.bot.tree.clear_commands(guild=discord.Object(id=self.bot.config.TEST_GUILD_ID) if self.bot.is_dev else None)
            
            commands = []
            for cmd in self.bot.tree._get_all_commands():
                if isinstance(cmd, app_commands.Group):
                    commands.extend(cmd.commands)
                else:
                    commands.append(cmd)

            total_commands = len(commands)
            logger.info(f"Found {total_commands} commands to sync")

            batch_size = 25
            for i in range(0, total_commands, batch_size):
                batch = commands[i:i + batch_size]
                if self.bot.is_dev:
                    success = await sync_to(self.bot.config.TEST_GUILD_ID)
                else:
                    success = await sync_to()
                
                if success:
                    await ctx.send(f"✅ Synced batch {i//batch_size + 1} ({min(i + batch_size, total_commands)}/{total_commands} commands)")
                else:
                    await ctx.send(f"❌ Failed to sync batch {i//batch_size + 1}")
                    return

                await asyncio.sleep(1)

            await ctx.send(f"✅ Successfully synced {total_commands} commands!")

        except Exception as e:
            await ctx.send(f"❌ Sync failed: {str(e)}")
            logger.error(f"Sync error: {e}", exc_info=True)

    @commands.command(name='debugcmds')
    @commands.is_owner()
    async def debug_commands(self, ctx: commands.Context):
        """Debug command tree"""
        def format_cmd(cmd):
            return f"- {cmd.name}: {type(cmd).__name__}"

        lines = ["**Registered Commands:**"]
        
        lines.append("\n*Global Commands:*")
        for cmd in self.bot.tree._get_all_commands():
            lines.append(format_cmd(cmd))
            if isinstance(cmd, app_commands.Group):
                for subcmd in cmd.commands:
                    lines.append(f"  └─ {format_cmd(subcmd)}")

        if self.bot.is_dev:
            guild = discord.Object(id=self.bot.config.TEST_GUILD_ID)
            lines.append("\n*Guild Commands:*")
            for cmd in self.bot.tree._get_all_commands(guild=guild):
                lines.append(format_cmd(cmd))
                if isinstance(cmd, app_commands.Group):
                    for subcmd in cmd.commands:
                        lines.append(f"  └─ {format_cmd(subcmd)}")

        content = "\n".join(lines)
        if len(content) > 2000:
            chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]
            for chunk in chunks:
                await ctx.send(f"```\n{chunk}\n```")
        else:
            await ctx.send(content)
async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
