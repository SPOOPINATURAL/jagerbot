import asyncio
import logging
from bot import JagerBot
import config
import os
from utils.setup import load_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_bot() -> JagerBot:
    import discord
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True

    bot = JagerBot(
        command_prefix="$",
        intents=intents,
        help_command=None
    )
    return bot

async def main():
    logger.info("main() is running")
    data = load_data()
    logger.info("Loaded data from JSON.")

    bot = create_bot()
    bot.planes = data.get("planes", [])
    bot.alerts = data.get("alerts", {})
    bot.user_scores = data.get("trivia_scores", {})
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            logger.info(f"Loaded extension: cogs.{filename[:-3]}")
    try:
        logger.info("Starting bot...")
        await bot.start(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await bot.close()
        logger.info("Bot closed cleanly.")

if __name__ == "__main__":
    asyncio.run(main())