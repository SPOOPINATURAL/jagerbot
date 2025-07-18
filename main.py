import os
import sys
import logging
import traceback
import discord
from discord.ext import bridge
from dotenv import load_dotenv
import config

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

intents = discord.Intents.all()
bot = bridge.Bot(
    command_prefix="$",
    help_command=None,
    intents=intents,
    application_id=1376008090968657990,
    sync_commands=True
)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    synced = await bot.sync_commands()
    logger.info(f"Synced {len(synced)} global command(s).")
    logger.info("Slash cmds:")
    for cmd in bot.application_commands:
        logger.info(f"/{cmd.name} - {cmd.description}")

    logger.info("Prefix cmds:")
    for cmd in bot.commands:
        logger.info(f"{bot.command_prefix}{cmd.name}")

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name="everything")
    )

if __name__ == "__main__":
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"Loaded cog: {filename[:-3]}")
            except Exception as e:
                logger.error(f"Failed to load cog {filename[:-3]}: {e}")
                traceback.print_exc()
    try:
        logger.info("Starting bot...")
        load_dotenv()
        bot.run(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        logger.info("Bot closed cleanly.")

