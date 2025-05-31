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
        self._setup_logging()
        self._synced: bool = False

    @property
    def synced(self) -> bool:
        return self._synced

    @synced.setter
    def synced(self, value: bool):
        self._synced = value

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('discord.log', encoding='utf-8', errors='replace'),
                logging.StreamHandler()
            ]
        )
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        for handler in logging.root.handlers:
            handler.setFormatter(formatter)


    async def load_cogs(self) -> None:
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    logger.info(f"Loaded cog: {filename}")
                except Exception as e:
                    logger.error(f"Failed to load cog {filename}: {str(e)}")
        logger.info("Finished loading cogs")

    async def setup_hook(self) -> None:
        try:
            logger.info("Setup hook started")
            await self.load_cogs()
            if not self.synced:
                logger.info("Starting command tree sync")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        if self.is_dev:
                            test_guild = discord.Object(id=self.config.TEST_GUILD_ID)

                            # Batch sync commands instead of individual syncs
                            commands = []
                            for cmd in self.tree.get_commands():
                                if not isinstance(cmd, app_commands.Group):
                                    commands.append(cmd)

                            self.tree.clear_commands(guild=test_guild)
                            async with asyncio.timeout(30):
                                await self.tree.sync(guild=test_guild)
                            logger.info("Development mode: Commands synced to test guild")
                        else:
                            async with asyncio.timeout(30):
                                await self.tree.sync()
                            logger.info("Production mode: Commands synced globally")
                        self.synced = True
                        break
                    except asyncio.TimeoutError:
                        if attempt < max_retries - 1:
                            logger.warning(f"Command sync attempt {attempt + 1} timed out, retrying...")
                            await asyncio.sleep(5)
                        else:
                            logger.error("Command sync failed after all attempts")
                            raise
            else:
                logger.info("Commands already synced, skipping sync")

        except Exception as e:
            logger.error(f"Error during setup: {str(e)}")
            raise

    async def sync_command_group(self, group_name: str) -> None:
        try:
            if self.is_dev:
                test_guild = discord.Object(id=self.config.TEST_GUILD_ID)
                await self.tree.sync(guild=test_guild)
            else:
                await self.tree.sync()
            logger.info(f"Successfully synced command group: {group_name}")
        except Exception as e:
            logger.error(f"Failed to sync command group {group_name}: {e}")


    async def on_ready(self) -> None:
        try:
            logger.info(f"Logged in as {self.user} (ID: {self.user.id}) :)")

            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="Everything"
                )
            )

            guild = discord.Object(id=self.config.TEST_GUILD_ID) if self.is_dev else None
            logger.info("Registered Commands:")
            try:
                async with asyncio.timeout(10):
                    commands = await self.tree.fetch_commands(guild=guild)
                    logger.info("Registered Commands:")
                    for cmd in commands:
                        logger.info(f"  • {cmd.name}")
            except asyncio.TimeoutError:
                logger.error("Timeout while fetching commands")

        except Exception as e:
            logger.error(f"Error in on_ready: {str(e)}")

    async def on_connect(self) -> None:
        logger.info("Connected to Discord")

    async def on_disconnect(self) -> None:
        logger.warning("Disconnected from Discord")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        logger.error(f"Unhandled error in {event_method}", exc_info=True)
