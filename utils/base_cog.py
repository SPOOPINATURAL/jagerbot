import aiohttp
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

    async def cog_load(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def cog_unload(self) -> None:
        if hasattr(self, 'session') and self.session and not self.session.closed:
            await self.session.close()
        self.cache.cleanup_expired(self.cache_duration)

    async def fetch_json(self, url: str, headers: dict = None):
        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            return None