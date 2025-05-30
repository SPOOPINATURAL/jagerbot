#standard stuff
import os, logging, warnings, tracemalloc
from datetime import datetime
from types import SimpleNamespace

#3rd party
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import dateparser
import pytz
from pytz.exceptions import UnknownTimeZoneError
from dateparser.conf import settings as dp_settings
import html
import asyncio

#local
import webserver
import config
import utils.helpers as helpers
from views.info_pages import InfoPages
from bot import JagerBot
from cogs.alerts import AlertCog

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = JagerBot(
    command_prefix=">",
    intents=intents,
    help_command=None
)

bot.config = config

print(f"[DEBUG] API Key: {config.TRACKER_API_KEY}")
tracemalloc.start()
warnings.simplefilter('always', RuntimeWarning)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
custom_settings = SimpleNamespace(**dp_settings.__dict__)
custom_settings.RETURN_AS_TIMEZONE_AWARE = False
timeout = aiohttp.ClientTimeout(total=10)
sessions = {}

# data load
alerts = helpers.load_alerts() or {}
helpers.save_alerts(alerts)
all_data = helpers.load_all_json_from_folder()

bot.planes = all_data.get("planes", [])
bot.alerts = all_data.get("alerts", {})
bot.user_scores = all_data.get("trivia_scores", {})

UTC = pytz.UTC
alert_checker = AlertCog(bot)

# logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("discord.log", encoding="utf-8", mode="w"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
if __name__ == "__main__":
    webserver.keep_alive()
    bot.run(config.DISCORD_TOKEN)