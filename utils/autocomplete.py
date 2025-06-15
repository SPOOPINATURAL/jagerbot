from typing import Dict, List, Tuple
import discord

class AutocompleteMixin:
    def get_suggestions(
        self,
        current: str,
        primary_dict: Dict[str, str],
        alias_dict: Dict[str, str] = None,
        max_results: int = 25,
        cache_prefix: str = ""
    ) -> List[discord.OptionChoice]:
        if not current:
            return []

        current = current.lower()
        cache_key = f"{cache_prefix}_{current}" if cache_prefix else current

        cached = self.autocomplete_cache.get(cache_key)
        if cached:
            return cached

        suggestions = []

        for name, full_name in primary_dict.items():
            if current in name:
                suggestions.append(discord.OptionChoice(name=full_name, value=full_name))


        if alias_dict and len(suggestions) < max_results:
            for alias, name in alias_dict.items():
                if current in alias.lower() and len(suggestions) < max_results:
                    suggestions.append(discord.OptionChoice(
                        name=f"{alias} (alias for {name})",
                        value=name
                    ))

        suggestions = suggestions[:max_results]
        self.autocomplete_cache.set(cache_key, suggestions)
        return suggestions