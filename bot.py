import logging
import os
from typing import List
import discord
from discord.ext import commands
from dotenv import load_dotenv

import config

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("jagerbot.log", encoding="utf-8"),
        logging.StreamHandler()
    ],
)

class JagerBot(commands.Bot):
    def __init__(self, **kwargs):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=kwargs.get("command_prefix", "$"),
            intents=intents,
            help_command=None,
            **kwargs
        )
        self.initial_extensions: List[str] = config.INITIAL_EXTENSIONS
        self.config = config
        self._dev_mode = os.getenv("BOT_ENV", "prod").lower() == "dev"

    async def setup_hook(self) -> None:
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Loaded extension: {ext}")
            except Exception as e:
                logger.error(f"Failed to load extension {ext}: {e}", exc_info=True)

        # await self.tree.sync()

    async def on_ready(self) -> None:
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.watching, name="everything")
        )
        logger.info(f"Commands registered in tree: {len(list(self.tree.walk_commands()))}")
        for cmd in self.tree.walk_commands():
            logger.info(f"Loaded slash command: /{cmd.qualified_name} (type: {cmd.type})")
        for cmd in self.commands:
            logger.info(f"Loaded prefix command: {cmd.qualified_name}")

    async def on_connect(self):
        logger.info("Connected to Discord")

    async def on_disconnect(self):
        logger.warning("Disconnected from Discord")

    async def on_error(self, event_method: str, *args, **kwargs):
        logger.error(f"Unhandled error in {event_method}", exc_info=True)

    async def close(self):
        logger.info("Shutting down bot...")
        await super().close()
        logger.info("Bot shutdown complete")
