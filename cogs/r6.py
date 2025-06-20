import discord
import random
import aiohttp
import feedparser
import logging
from typing import Dict, Any, List
from discord.ext import commands
from discord.commands import slash_command
from datetime import datetime, timedelta

from utils.base_cog import BaseCog
from utils.autocomplete import AutocompleteMixin
from utils.views import PaginationView
from utils.helpers import DataHelper, FileHelper
from config import (
    TRACKER_API_KEY,
    R6_API_BASE,
    R6_STEAM_RSS,
    R6_VIEW_TIMEOUT,
    CACHE_DURATION,
    API_TIMEOUT
)

logger = logging.getLogger(__name__)

class MapFloorView(PaginationView):
    def __init__(self, floors: List[dict], map_name: str):
        super().__init__(timeout=R6_VIEW_TIMEOUT)
        self.floors = floors
        self.map_name = map_name

    def create_embed(self, index: int) -> discord.Embed:
        floor = self.floors[index]
        return discord.Embed(
            title=f"{self.map_name} – {floor['name']}",
            description=f"Floor {index + 1}/{len(self.floors)}",
            color=0x8B0000
        ).set_image(url=floor.get("image", ""))


class R6Cog(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.session = None
        self.cache = {}
        self.operators: Dict[str, Any] = {}
        self.maps: Dict[str, Any] = {}
        self._operator_names: Dict[str, str] = {}
        self._operator_aliases: Dict[str, str] = {}
        self._map_names: Dict[str, str] = {}
        self._map_aliases: Dict[str, str] = {}
        self._news_cache = {
            "data": None,
            "timestamp": None,
        }
        self.r6_group = self.bot.create_group("r6", "Rainbow Six Siege commands")

        @self.r6_group.command(name="stats", description="Look up R6 player stats")
        async def stats(
            ctx: discord.ApplicationContext,
            platform: discord.Option(str, "uplay / psn / xbl", autocomplete=lambda ctx: ["uplay", "psn", "xbl"]),
            username: discord.Option(str, "Player username")
        ):
            await ctx.defer()
            url = f"{R6_API_BASE}/profile/{platform}/{username}"
            headers = {
                "TRN-Api-Key": TRACKER_API_KEY,
                "Accept": "application/json"
            }
            try:
                async with self.session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        await ctx.followup.send(f"❌ Could not find stats for `{username}` on `{platform}`.")
                        return
                    data = await resp.json()

                stats = data["data"]["segments"][0]["stats"]
                metadata = data["data"]["segments"][0]["metadata"]

                rp = stats.get("rankedPoints", {}).get("displayValue", "—")
                kd = stats.get("kd", {}).get("displayValue", "—")
                wl = stats.get("wlPercentage", {}).get("displayValue", "—")
                avg_kills = stats.get("killsPerMatch", {}).get("displayValue") or stats.get("averageKills", {}).get(
                    "displayValue", "—")
                headshot_pct = stats.get("headshotPct", {}).get("displayValue") or stats.get("headshotPercentage", {}).get(
                    "displayValue", "—")
                rank_icon = metadata.get("rankImageUrl") or metadata.get("iconUrl")

                embed = discord.Embed(
                    title=f"📊 {username}'s R6 Stats ({platform.upper()})",
                    color=0x8B0000
                )
                embed.set_thumbnail(url=rank_icon)
                embed.add_field(name="Ranked Points (RP)", value=rp, inline=True)
                embed.add_field(name="K/D Ratio", value=kd, inline=True)
                embed.add_field(name="Win %", value=wl, inline=True)
                embed.add_field(name="Avg Kills/Match", value=avg_kills, inline=True)
                embed.add_field(name="Headshot %", value=headshot_pct, inline=True)
                embed.set_footer(text="Data provided by Tracker Network")

                await ctx.followup.send(embed=embed)

            except Exception as e:
                logger.error(f"Error fetching R6 stats for {username}: {e}")
                await ctx.followup.send("❌ Error fetching stats.")

        @self.r6_group.command(name="map", description="Look up map information")
        async def map_lookup(
            ctx: discord.ApplicationContext,
            name: discord.Option(str, "Name of the map", autocomplete=True)
        ):
            await ctx.defer()
            map_data = DataHelper.find_match(self.maps, name)
            if not map_data:
                await ctx.followup.send(f"❌ Map `{name}` not found.")
                return

            floors = map_data.get("floors", [])
            if not floors:
                await ctx.followup.send("❌ No floor data available.")
                return

            view = MapFloorView(floors=floors, map_name=map_data['name'])
            await ctx.followup.send(embed=view.create_embed(0), view=view)
            view.message = await ctx.original_response()

        @self.r6_group.command(name="op", description="Look up operator information")
        async def op_command(
            ctx: discord.ApplicationContext,
            name: discord.Option(str, "Name of the operator", autocomplete=True)
        ):
            await ctx.defer()
            op_data = DataHelper.find_match(self.operators, name)
            if not op_data:
                await ctx.followup.send(f"❌ Operator `{name}` not found.", ephemeral=True)
                return
            embed = self.create_op_embed(op_data)
            await ctx.followup.send(embed=embed)

        @self.r6_group.command(name="oprandom", description="Get a random operator")
        async def oprandom(
            ctx: discord.ApplicationContext,
            role: discord.Option(str, "Optional: attacker or defender", required=False) = None
        ):
            await ctx.defer()
            role_val = role.lower() if role else None
            filtered = [op for op in self.operators.values() if not role_val or op["role"].lower() == role_val]
            if not filtered:
                await ctx.followup.send("❌ No operators found.")
                return
            op_data = random.choice(filtered)
            embed = self.create_op_embed(op_data)
            await ctx.followup.send(embed=embed)

        @self.r6_group.command(name="oplist", description="List all operators")
        async def oplist(ctx: discord.ApplicationContext):
            attackers = sorted([op["name"] for op in self.operators.values() if op["role"].lower() == "attacker"])
            defenders = sorted([op["name"] for op in self.operators.values() if op["role"].lower() == "defender"])

            embed = discord.Embed(
                title="Operators by Role",
                description="Use `/r6 op [name]` to view detailed info.",
                color=0x8B0000
            )
            embed.add_field(name="Attackers", value="\n".join(attackers) or "—", inline=True)
            embed.add_field(name="Defenders", value="\n".join(defenders) or "—", inline=True)

            await ctx.respond(embed=embed)

        @self.r6_group.command(name="maplist", description="List all maps")
        async def maplist(ctx: discord.ApplicationContext):
            names = sorted(m["name"] for m in self.maps.values())
            half = len(names) // 2
            embed = discord.Embed(
                title="Available Ranked Maps",
                description="Use `/r6 map (name)` to view floorplans.",
                color=0x8B0000
            )
            embed.add_field(name="Maps A–M", value="\n".join(names[:half]) or "—", inline=True)
            embed.add_field(name="Maps N–Z", value="\n".join(names[half:]) or "—", inline=True)
            await ctx.respond(embed=embed)

        @self.r6_group.command(name="news", description="Get latest R6 news")
        async def news(ctx: discord.ApplicationContext):
            await ctx.defer()

            now = datetime.now()
            cache_data = self._news_cache.get("data")
            cache_time = self._news_cache.get("timestamp")

            if cache_data and cache_time and (now - cache_time).total_seconds() < CACHE_DURATION:
                embed = self._build_news_embed(cache_data)
                await ctx.followup.send(embed=embed)
                return

            try:
                feed = feedparser.parse(R6_STEAM_RSS)
                if not feed.entries:
                    await ctx.followup.send("❌ Could not fetch R6 news.", ephemeral=True)
                    return

                news_data = []
                for entry in feed.entries[:3]:
                    summary = entry.summary[:200] + "..." if len(entry.summary) > 200 else entry.summary
                    news_data.append({
                        "title": entry.title,
                        "published": entry.published,
                        "summary": summary,
                        "link": entry.link,
                    })

                self._news_cache["data"] = news_data
                self._news_cache["timestamp"] = now

                embed = self._build_news_embed(news_data)
                await ctx.followup.send(embed=embed)

            except Exception as e:
                logger.error(f"Error fetching R6 news: {e}")
                await ctx.followup.send("❌ Error fetching news. Please try again later.", ephemeral=True)
        
        logger.info("R6Cog loaded and slash commands registered")

    async def load_game_data(self):
        operators_data = await DataHelper.load_json_file("data/operators.json")
        maps_data = await DataHelper.load_json_file("data/maps.json")

        self.operators = operators_data or {}
        self.maps = maps_data or {}

        if not self.operators:
            raise ValueError("No operator data loaded")
        if not self.maps:
            raise ValueError("No map data loaded")

        self._build_lookups()

    def _build_lookups(self):
        self._operator_names = {op["name"].lower(): op["name"] for op in self.operators.values()}
        self._operator_aliases = {
            alias.lower(): op["name"]
            for op in self.operators.values()
            for alias in op.get("aliases", [])
        }
        self._map_names = {m["name"].lower(): m["name"] for m in self.maps.values()}
        self._map_aliases = {
            alias.lower(): m["name"]
            for m in self.maps.values()
            for alias in m.get("aliases", [])
        }

    async def map_autocomplete_callback(self, ctx: discord.AutocompleteContext):
        current = ctx.value.lower()
        choices = []

        for name in self._map_names.values():
            if current in name.lower():
                choices.append(name)

        for alias, name in self._map_aliases.items():
            if current in alias.lower():
                choices.append(f"{name} ({alias})")

        return choices[:25]

    async def operator_autocomplete_callback(self, ctx: discord.AutocompleteContext):
        current = ctx.value.lower()
        choices = []

        for name_lower, name in self._operator_names.items():
            if current in name_lower:
                choices.append(name)

        for alias_lower, name in self._operator_aliases.items():
            if current in alias_lower:
                choices.append(f"{name} ({alias_lower})")

        return choices[:25]

    @staticmethod
    def create_op_embed(op_data: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"Operator: {op_data['name']}",
            description=op_data.get("bio", ""),
            color=0x8B0000
        )
        embed.set_thumbnail(url=op_data.get("icon_url"))
        embed.set_image(url=op_data.get("image_url"))

        embed.add_field(name="Role", value=op_data.get('role', 'Unknown'), inline=True)
        embed.add_field(name="Squad", value=op_data.get('squad', '—'), inline=True)
        embed.add_field(name="Stats", value=f"Health: {op_data.get('health', '—')}\nSpeed: {op_data.get('speed', '—')}", inline=True)
        embed.add_field(name="Primary Weapons", value="\n".join(op_data.get('primary_weapons', [])) or "—", inline=False)
        embed.add_field(name="Secondary Weapons", value="\n".join(op_data.get('secondary_weapons', [])) or "—", inline=False)
        embed.add_field(name="Primary Gadget", value=op_data.get('primary_gadget', "—") or "—", inline=False)
        embed.add_field(name="Secondary Gadgets", value="\n".join(op_data.get('secondary_gadgets', [])) or "—", inline=False)
        return embed

    @staticmethod
    def _build_news_embed(news_data):
        embed = discord.Embed(title="📰 Rainbow Six Siege News", color=0x8B0000)
        for entry in news_data:
            embed.add_field(
                name=f"{entry['title']} ({entry['published']})",
                value=f"{entry['summary']}\n[Read more]({entry['link']})",
                inline=False
            )
        embed.set_footer(text="Source: Steam News")
        return embed

def setup(bot: commands.Bot):
    bot.add_cog(R6Cog(bot))
