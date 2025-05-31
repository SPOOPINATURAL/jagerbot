
from typing import Dict, List, Tuple
from discord import app_commands

class AutocompleteMixin:
    def get_suggestions(
        self,
        current: str,
        primary_dict: Dict[str, str],
        alias_dict: Dict[str, str] = None,
        max_results: int = 25,
        cache_prefix: str = ""
    ) -> List[app_commands.Choice[str]]:
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
                suggestions.append(app_commands.Choice(name=full_name, value=full_name))


        if alias_dict and len(suggestions) < max_results:
            for alias, name in alias_dict.items():
                if current in alias.lower() and len(suggestions) < max_results:
                    suggestions.append(app_commands.Choice(
                        name=f"{alias} (alias for {name})",
                        value=name
                    ))

        suggestions = suggestions[:max_results]
        self.autocomplete_cache.set(cache_key, suggestions)
        return suggestions