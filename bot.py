import asyncio
import logging
import os
import sys
from typing import List

import discord
from discord.ext import commands
from dotenv import load_dotenv

import config

load_dotenv()

log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_file = "jagerbot.log"

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

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

    async def sync_commands(self, force: bool = False) -> None:
        async with self._sync_lock:
            if self._synced and not force:
                return

        logger.info(f"{'Force ' if force else ''}Syncing commands globally...")

        try:
            if force:
                self.tree.clear_commands(guild=None)

            await self.tree.sync()
            logger.info("✅ Commands synced globally")
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

        for extension in self.config.INITIAL_EXTENSIONS:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")

        try:
            await self.sync_commands(force=True)
        except Exception as e:
            logger.error(f"Initial command sync failed: {e}")

    async def on_ready(self) -> None:
        try:
            logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="everything"
                )
            )

            await self.sync_commands(force=True)
            logger.info("Global commands synced. They may take up to 1 hour to appear on Discord clients.")

            for attempt in range(3):
                try:
                    async with asyncio.timeout(30):
                        commands = await self.tree.fetch_commands(guild=None)
                        if commands:
                            logger.info(f"Registered Commands ({len(commands)}):")
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
