from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
import discord

logger = logging.getLogger(__name__)

class CachedResponse:
    def __init__(self, data: Any, timestamp: datetime):
        self.data = data
        self.timestamp = timestamp

    def is_expired(self, max_age: int) -> bool:
        return (datetime.now() - self.timestamp).total_seconds() > max_age


class BaseCache:
    def __init__(self):
        self._cache: Dict[str, CachedResponse] = {}
    
    def get(self, key: str, max_age: int) -> Optional[Any]:
        if key in self._cache:
            cached = self._cache[key]
            if not cached.is_expired(max_age):
                return cached.data
            else:
                del self._cache[key]
        return None

    def set(self, key: str, data: Any):
        self._cache[key] = CachedResponse(data, datetime.now())

    def clear(self):
        self._cache.clear()

    def cleanup_expired(self, max_age: int):
        now = datetime.now()
        expired = [
            k for k, v in self._cache.items() 
            if (now - v.timestamp).total_seconds() > max_age
        ]
        for k in expired:
            del self._cache[k]


class GameCache(BaseCache):
    def __init__(self):
        super().__init__()
        self.stats_cache = BaseCache()
        self.data_cache = BaseCache()
        self.api_cache = BaseCache()

    def cleanup_expired(self, max_age: int):
        for cache in [self.stats_cache, self.data_cache, self.api_cache]:
            cache.cleanup_expired(max_age)


class AutocompleteCache(BaseCache):
    def get_suggestions(
        self, 
        query: str, 
        suggestions: List[discord.OptionChoice], 
        max_age: int = 300,
        max_results: int = 25
    ) -> List[discord.OptionChoice]:
        query = query.lower()
        cached = self.get(query, max_age)
        if cached:
            return cached[:max_results]
        
        self.set(query, suggestions)
        return suggestions[:max_results]

    def cleanup_expired(self, max_age: int):
        super().cleanup_expired(max_age)


class APICache(BaseCache):
    async def get_or_fetch(
        self, 
        key: str, 
        fetch_func, 
        max_age: int = 300,
        **kwargs
    ) -> Optional[Any]:
        cached = self.get(key, max_age)
        if cached:
            return cached

        try:
            data = await fetch_func(**kwargs)
            self.set(key, data)
            return data
        except Exception as e:
            logger.error(f"Error fetching data for {key}: {e}")
            return None


class EmbedCache(BaseCache):
    def get_embed(
        self, 
        key: str, 
        max_age: int = 300
    ) -> Optional[Any]:
        return self.get(key, max_age)

    def set_embed(self, key: str, embed: Any):
        self.set(key, embed)