import discord
import os
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from typing import List, Optional, Set
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
        self.added_command_groups: Set[str] = set()

    @property
    def is_dev(self) -> bool:
        return self._dev_mode

    async def sync_commands(self, force: bool = False) -> None:
        async with self._sync_lock:
            if self._synced and not force:
                return
            
            logger.info(f"{'Force ' if force else ''}Syncing commands...")
            try:
                if self.is_dev:
                    guild = discord.Object(id=self.config.TEST_GUILD_ID)
                    self.tree.clear_commands(guild=guild)
                    if force:
                        self.tree.clear_commands(guild=guild)
                    self.tree.copy_global_to(guild=guild)
                    async with asyncio.timeout(30):
                        await self.tree.sync(guild=guild)
                    logger.info(f"Commands {'force ' if force else ''}synced to test guild")
                else:
                    if force:
                        self.tree.clear_commands()
                    async with asyncio.timeout(30):
                        await self.tree.sync()
                    logger.info(f"Commands {'force ' if force else ''}synced globally")
                
                self._synced = True
            except asyncio.TimeoutError:
                logger.error("Command sync timed out")
                raise
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")
                raise

    async def setup_hook(self) -> None:
        logger.info("Setup hook started")
        self.owner_id = 640289470763237376

        try:
            if self.is_dev:
                guild = discord.Object(id=self.config.TEST_GUILD_ID)
                self.tree.clear_commands(guild=guild)
            else:
                self.tree.clear_commands()

            for extension in self.config.INITIAL_EXTENSIONS:
                try:
                    await self.load_extension(extension)
                    logger.info(f"Loaded extension: {extension}")
                except Exception as e:
                    logger.error(f"Failed to load extension {extension}: {e}")
                    continue

            try:
                if self.is_dev:
                    guild = discord.Object(id=self.config.TEST_GUILD_ID)
                    self.tree.copy_global_to(guild=guild)
                    await self.tree.sync(guild=guild)
                    logger.info(f"Synced commands to development guild")
                else:
                    await self.tree.sync()
                    logger.info("Synced commands globally")
            except Exception as e:
                logger.error(f"Initial sync failed: {e}")

        except Exception as e:
            logger.error(f"Setup hook failed: {e}", exc_info=True)

    def add_group_to_tree(self, group: app_commands.Group, group_name: str) -> bool:
        if not isinstance(group, app_commands.Group):
            logger.error(f"Invalid group type for {group_name}: {type(group)}")
            return False
        
        try:
            if group_name in self.added_command_groups:
                logger.debug(f"Command group {group_name} already added")
                return True

            self.tree.add_command(group)
            self.added_command_groups.add(group_name)
            logger.info(f"Added command group: {group_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add command group {group_name}: {e}")
            return False

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

            guild = discord.Object(id=self.config.TEST_GUILD_ID) if self.is_dev else None
            
            for attempt in range(3):
                try:
                    async with asyncio.timeout(30):
                        commands = await self.tree.fetch_commands(guild=guild)
                        command_count = len(commands)
                        
                        if command_count > 0:
                            logger.info(f"Registered Commands ({command_count}):")
                            for cmd in commands:
                                logger.info(f"  • {cmd.name}")
                        else:
                            logger.warning("No commands registered, attempting force sync...")
                            await self.sync_commands(force=True)
                        break
                except asyncio.TimeoutError:
                    logger.warning(f"Fetch attempt {attempt + 1} timed out...")
                    if attempt == 2:
                        logger.error("All fetch attempts failed")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Error fetching commands: {e}")

        except Exception as e:
            logger.error(f"Error in on_ready: {e}", exc_info=True)

    async def on_connect(self) -> None:
        logger.info("Connected to Discord")

    async def on_disconnect(self) -> None:
        logger.warning("Disconnected from Discord")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        logger.error(f"Unhandled error in {event_method}", exc_info=True)

    async def close(self) -> None:
        logger.info("Shutting down bot...")
        try:
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            if tasks:
                logger.info(f"Cancelling {len(tasks)} remaining tasks...")
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            
            await super().close()
            logger.info("Bot shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise