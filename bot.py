import discord
import os
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from typing import List, Optional
from dotenv import load_dotenv
import config

load_dotenv()

logger = logging.getLogger(__name__)

class JagerBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_extensions: List[str] = []
        self.config = config
        self._synced: bool = False
        self._sync_lock = asyncio.Lock()
        self._dev_mode = os.getenv("BOT_ENV", "prod").lower() == "dev"

    @property
    def is_dev(self) -> bool:
        return self._dev_mode
    
    async def sync_commands(self):
        async with self._sync_lock:
            try:
                await asyncio.sleep(1)
                
                if self.is_dev:
                    guild = discord.Object(id=self.config.TEST_GUILD_ID)
                    self.tree.clear_commands(guild=guild)
                    
                    self.tree.copy_global_to(guild=guild)
                    for attempt in range(3):
                        try:
                            await self.tree.sync(guild=guild)
                            break
                        except asyncio.CancelledError:
                            if attempt == 2:  # Last attempt
                                raise
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
                    commands = await self.tree.fetch_commands(guild=guild)
                    logger.info(f"Synced {len(commands)} commands to test guild")
                    for cmd in commands:
                        logger.info(f"  • {cmd.name}")
                else:
                    # Add retry logic for global sync
                    for attempt in range(3):
                        try:
                            await self.tree.sync()
                            break
                        except asyncio.CancelledError:
                            if attempt == 2:  # Last attempt
                                raise
                            await asyncio.sleep(2 ** attempt)
                    
                    commands = await self.tree.fetch_commands()
                    logger.info(f"Synced {len(commands)} commands globally")
                    for cmd in commands:
                        logger.info(f"  • {cmd.name}")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")
                raise

    async def setup_hook(self):
        logger.info("Starting setup hook...")
        try:
            loaded_extensions = []
            for extension in self.config.INITIAL_EXTENSIONS:
                try:
                    await self.load_extension(extension)
                    loaded_extensions.append(extension)
                    logger.info(f"Loaded extension: {extension}")
                except Exception as e:
                    logger.error(f"Failed to load extension {extension}: {e}")

            # Then sync commands with retry logic
            await self.sync_commands()
            self._synced = True

        except Exception as e:
            logger.error(f"Setup hook failed: {e}")
            raise

    async def ensure_sync(self) -> None:
        try:
            await self.sync_commands()
        except Exception as e:
            logger.error(f"Force sync failed: {e}")
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
            await self.sync_commands()
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