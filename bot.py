import logging
import os
import sys
from typing import List
import asyncio
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
            logger.info(f"Commands registered in tree before start: {len(list(self.tree.walk_commands()))}")
            for cmd in self.tree.walk_commands():
                logger.info(f"Loaded slash command: /{cmd.qualified_name} (type: {cmd.type})")
            for cmd in self.commands:
                logger.info(f"Loaded prefix command: {cmd.qualified_name}")
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
            await super().close()
            logger.info("Bot shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
