import asyncio
from typing import Dict
import logging
from bot import JagerBot
import config
from utils.setup import setup_logging, load_data
from webserver import keep_alive

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import dateparser
import pytz
from pytz.exceptions import UnknownTimeZoneError
from dateparser.conf import settings as dp_settings
import html


def create_bot() -> JagerBot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    bot = JagerBot(
        command_prefix=">",
        intents=intents,
        help_command=None
    )
    return bot

async def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    bot = create_bot()
    
    data = load_data()
    bot.planes = data.get("planes", [])
    bot.alerts = data.get("alerts", {})
    bot.user_scores = data.get("trivia_scores", {})
    
    keep_alive()

    try:
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await bot.close()
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise
    finally:
        remaining_tasks = [t for t in asyncio.all_tasks()if t is not asyncio.current_task()]
        if remaining_tasks:
            logger.info(f"Cleaning up {len(remaining_tasks)} remaining tasks...")
            for task in remaining_tasks:
                task.cancel()
            await asyncio.gather(*remaining_tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())