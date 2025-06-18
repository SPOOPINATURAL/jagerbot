
from discord.ext import commands
from utils.cache import GameCache, AutocompleteCache
import config

class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = GameCache()
        self.autocomplete_cache = AutocompleteCache()
        self.session = None
        self.cache_duration = config.CACHE_DURATION

    async def fetch_json(self, url: str, headers: dict = None):
        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            return None