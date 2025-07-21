import os
import sys
import json
import aiohttp
import logging
import traceback
import discord
from discord.ext import bridge, commands
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
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
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
@bot.event
async def on_connect():
    if not hasattr(bot, "session"):
        bot.session = aiohttp.ClientSession()
        logger.info("aiohttp session initialized.")
@bot.event
async def on_shutdown():
    if hasattr(bot, "session"):
        await bot.session.close()
        logger.info("aiohttp session closed.")

if __name__ == "__main__":
    try:
        bot.maps = load_json("data/maps.json")
        bot.operators = load_json("data/operators.json")
        bot.planes = load_json("data/planes.json")
        logger.info("Loaded map, operator, and plane data.")
    except Exception as e:
        logger.exception("Failed to load JSON data.")
        sys.exit(1)
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

