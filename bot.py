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
logger.info("bot.py is running")
class JagerBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_extensions: List[str] = config.INITIAL_EXTENSIONS
        self.config = config
        self._dev_mode = os.getenv("BOT_ENV", "prod").lower() == "dev"


    async def setup_hook(self) -> None:
        logger.info("Setup hook started")
        self.owner_id = 640289470763237376

        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")

        logger.info(f"App commands loaded: {self.application_commands}")
        logger.info(f"Registered global app commands: {[cmd.name for cmd in self.application_commands]}")
        logger.info("Slash commands will be synced automatically by Pycord.")

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
        except Exception as e:
            logger.error(f"Error in on_ready: {e}", exc_info=True)

    @staticmethod
    async def on_connect() -> None:
        logger.info("Connected to Discord")

    @staticmethod
    async def on_disconnect() -> None:
        logger.warning("Disconnected from Discord")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        logger.error(f"Unhandled error in {event_method}", exc_info=True)

    async def close(self) -> None:
        logger.info("Shutting down bot...")
        try:
            await super().close()
            logger.info("Bot shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
