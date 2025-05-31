import discord
import os
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from typing import List
from dotenv import load_dotenv
import config

load_dotenv()

logger = logging.getLogger(__name__)

class JagerBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_dev = os.getenv("BOT_ENV", "prod").lower() == "dev"
        self.initial_extensions: List[str] = []
        self.config = config
        self._synced: bool = False
        self._sync_lock = asyncio.Lock()

    async def sync_commands(self):
        try:
            if os.getenv("BOT_ENV", "dev").lower() == "dev":
                guild = discord.Object(id=self.config.TEST_GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info("Commands synced to test guild")
            else:
                await self.tree.sync()
                logger.info("Commands synced globally")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            raise

    async def setup_hook(self):
        try:
            for cog in self.config.INITIAL_EXTENSIONS:
                try:
                    await self.load_extension(cog)
                    logger.info(f"Loaded extension {cog}")
                except Exception as e:
                    logger.error(f"Failed to load extension {cog}: {e}")
                
            await self.sync_commands()
        except Exception as e:
            logger.error(f"Error in setup hook: {e}")
            raise

    async def load_cogs(self) -> None:
        loaded_count = 0
        start_time = asyncio.get_event_loop().time()
        
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    loaded_count += 1
                    logger.info(f"Loaded cog ({loaded_count}): {cog_name}")
                except Exception as e:
                    logger.error(f"Failed to load cog {cog_name}: {str(e)}")
                    
        elapsed = asyncio.get_event_loop().time() - start_time
        logger.info(f"Finished loading {loaded_count} cogs in {elapsed:.2f} seconds")

    async def on_ready(self) -> None:
        try:
            logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
            
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="Everything"
                )
            )

            if self._synced:
                guild = discord.Object(id=self.config.TEST_GUILD_ID) if self.is_dev else None
                try:
                    async with asyncio.timeout(10):
                        commands = await self.tree.fetch_commands(guild=guild)
                        if commands:
                            logger.info(f"Registered Commands ({len(commands)}):")
                            for cmd in commands:
                                logger.info(f"  • {cmd.name}")
                        else:
                            logger.warning("No commands registered")
                except asyncio.TimeoutError:
                    logger.error("Timeout while fetching commands")
                except Exception as e:
                    logger.error(f"Error fetching commands: {e}")

        except Exception as e:
            logger.error(f"Error in on_ready: {str(e)}")

    async def force_sync(self, guild_id=None):
        try:
            self._synced = False
            if guild_id:
                guild = discord.Object(id=guild_id)
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Force synced commands to guild {guild_id}")
            else:
                self.tree.clear_commands()
                await self.tree.sync()
                logger.info("Force synced commands globally")
            self._synced = True
        except Exception as e:
            logger.error(f"Force sync failed: {e}")
            raise

    async def on_connect(self) -> None:
        logger.info("Connected to Discord")

    async def on_disconnect(self) -> None:
        logger.warning("Disconnected from Discord")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        logger.error(f"Unhandled error in {event_method}", exc_info=True)