import os
import sys
import logging
import asyncio
from typing import List
import discord
from discord.ext import commands, bridge
from dotenv import load_dotenv
import config

load_dotenv()

log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler("jagerbot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("jagerbot")
logger.info(f"discord imported from: {discord.__file__}")
logger.info(f"discord version: {discord.__version__}")
class JagerBot(bridge.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_extensions: List[str] = config.INITIAL_EXTENSIONS
        self._dev_mode = os.getenv("BOT_ENV", "prod").lower() == "dev"

    async def setup_hook(self):
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Loaded extension: {ext}")
            except Exception as e:
                logger.error(f"Failed to load extension {ext}: {e}", exc_info=True)

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} application commands.")
        except Exception as e:
            logger.error(f"Failed to sync application commands: {e}", exc_info=True)
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.watching, name="everything")
        )
        logger.info(f"Commands registered in tree before start: {len(list(self.tree.walk_commands()))}")
        for cmd in self.tree.walk_commands():
            logger.info(f"Slash command: /{cmd.qualified_name} | Type: {cmd.type} | Default permission: {cmd.default_permission}")
            if cmd.default_permission is False:
                logger.warning(f"Command /{cmd.qualified_name} is disabled by default")
            if hasattr(cmd, 'guild_ids') and cmd.guild_ids:
                logger.info(f"Restricted to guilds: {cmd.guild_ids}")
            if hasattr(cmd, 'commands') and cmd.commands:
                for subcmd in cmd.commands:
                    logger.info(f"Subcommand: {subcmd.name} | Default permission: {subcmd.default_permission}")

        for cmd in self.commands:
            logger.info(f"Loaded prefix command: {cmd.qualified_name}")

async def main():
    logger.info("main() is running")
    intents = discord.Intents.all()
    bot = JagerBot(
        command_prefix="$",
        help_command=None,
        intents=intents,
        application_id=1376008090968657990
    )
    try:
        logger.info("Starting bot...")
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await bot.close()
        logger.info("Bot closed cleanly.")

if __name__ == "__main__":
    asyncio.run(main())
