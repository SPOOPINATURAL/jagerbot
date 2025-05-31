import logging
from discord.ext import commands
import aiohttp
import discord
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def cog_unload(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    @commands.command(name='sync')
    @commands.is_owner()
    async def sync_cmd(self, ctx: commands.Context):
        await ctx.send("🔄 Starting command sync...")

        try:
            if self.bot.is_dev:
                guild = discord.Object(id=self.bot.config.TEST_GUILD_ID)
                self.bot.tree.copy_global_to(guild=guild)

                commands_to_sync = self.bot.tree._get_all_commands()
                total_commands = len(commands_to_sync)


                for i in range(0, total_commands, 25):
                    batch = commands_to_sync[i:i + 25]
                    async with asyncio.timeout(30):
                        await self.bot.tree.sync(guild=guild)
                    await ctx.send(f"✅ Synced batch of {len(batch)} commands ({i + len(batch)}/{total_commands})")
                    await asyncio.sleep(1)
                await ctx.send(f"✅ Finished syncing all {total_commands} commands to development guild!")
            else:
                commands_to_sync = self.bot.tree._get_all_commands()
                total_commands = len(commands_to_sync)

                for i in range(0, total_commands, 25):
                    batch = commands_to_sync[i:i + 25]
                    async with asyncio.timeout(30):
                        await self.bot.tree.sync()
                    await ctx.send(f"✅ Synced batch of {len(batch)} commands ({i + len(batch)}/{total_commands})")
                    await asyncio.sleep(1)

                await ctx.send(f"✅ Finished syncing all {total_commands} commands globally!")

        except Exception as e:
            await ctx.send(f"❌ Error during sync: {str(e)}")
            return

    @sync_cmd.error
    async def sync_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")
        else:
            logger.error(f"Unexpected error in sync command: {error}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred.")

    @commands.is_owner()
    @commands.command(name='clearsync')
    async def clear_commands(self, ctx: commands.Context):
        """Clear and resync all commands"""
        await ctx.send("Clearing commands...")
        if self.bot.is_dev:
            guild = discord.Object(id=self.bot.config.TEST_GUILD_ID)
            self.bot.tree.clear_commands(guild=guild)
            await self.bot.tree.sync(guild=guild)
        else:
            self.bot.tree.clear_commands()
            await self.bot.tree.sync()
        await ctx.send("✅ Commands cleared and resynced!")

    @commands.command(name='nukesync')
    @commands.is_owner()
    async def nuke_sync(self, ctx: commands.Context):
        await ctx.send(" Starting nuclear sync...")
        
        try:
            guild = discord.Object(id=self.bot.config.TEST_GUILD_ID)
            self.bot.tree.clear_commands(guild=guild)
            await self.bot.tree.sync(guild=guild)
        
            self.bot.tree.clear_commands()
            await self.bot.tree.sync()
        
            await ctx.send("✅ All commands cleared. Resyncing...")
        
            if self.bot.is_dev:
                self.bot.tree.copy_global_to(guild=guild)
                async with asyncio.timeout(60):
                    await self.bot.tree.sync(guild=guild)
            else:
                async with asyncio.timeout(60):
                    await self.bot.tree.sync()
                
            await ctx.send("✅ Nuclear sync complete!")
        
        except Exception as e:
            await ctx.send(f"❌ Error during nuclear sync: {str(e)}")


async def setup(bot):
    await bot.add_cog(Owner(bot))