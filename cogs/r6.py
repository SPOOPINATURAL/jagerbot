import discord
import random
import aiohttp
import json
import os
import feedparser
import logging
from discord import Option
from typing import Dict, Any, List
from discord.ext import bridge, commands
from datetime import datetime
from pathlib import Path

from utils.views import PaginationView
from utils.helpers import DataHelper
from config import (
    TRACKER_API_KEY,
    R6_API_BASE,
    R6_STEAM_RSS,
    R6_VIEW_TIMEOUT,
    CACHE_DURATION,
)

logger = logging.getLogger(__name__)

class MapFloorView(PaginationView):
    def __init__(self, floors: List[dict], map_name: str):
        super().__init__(page_count=len(floors),timeout=R6_VIEW_TIMEOUT)
        self.floors = floors
        self.map_name = map_name

    def create_embed(self, index: int) -> discord.Embed:
        floor = self.floors[index]
        embed = discord.Embed(
            title=f"{self.map_name} – {floor['name']}",
            description=f"Floor {index + 1}/{len(self.floors)}",
            color=0x8B0000
        )
        
        image_path = floor.get("image", "")
        file_obj = None
        
        if image_path.startswith("http://") or image_path.startswith("https://"):
            embed.set_image(url=image_path)
        else:
            # Normalize path and attempt to resolve relative to project root
            image_path = image_path.replace("\\", "/")
            candidate = Path(image_path)
            if not candidate.exists():
                repo_root = Path(__file__).resolve().parents[1]
                candidate = (repo_root / image_path).resolve()

            if candidate.exists():
                filename = os.path.basename(str(candidate))
                # include map name in filename to avoid clashes
                safe_map = self.map_name.lower().replace(" ", "_")
                filename = f"{safe_map}_{filename}"
                file_obj = discord.File(str(candidate), filename=filename)
                embed.set_image(url=f"attachment://{filename}")
            else:
                embed.description += "\n image not found."
        return embed, file_obj
        
async def platform_autocomplete(ctx: discord.AutocompleteContext):
        return ["uplay", "psn", "xbl"]

class R6Cog(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.cache = {}
        self.operators: Dict[str, Any] = {}
        self.maps: Dict[str, Any] = {}
        self._operator_names: Dict[str, str] = {}
        self._operator_aliases: Dict[str, str] = {}
        self._map_names: Dict[str, str] = {}
        self._map_aliases: Dict[str, str] = {}
        self.maps = bot.maps
        self.operators = bot.operators
        self._news_cache = {
            "data": None,
            "timestamp": None,
        }
    def load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    @bridge.bridge_group(name="r6", description="Rainbow Six Siege commands")
    async def r6(self, ctx: discord.ApplicationContext):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="R6 Siege Commands",
                description="Use `/r6 <command>` to get help on a specific command.",
                color=0x8B0000
            )
            embed.add_field(name="Available Commands", value="`stats`, `op`, `oplist`, `oprandom`, `map`, `maplist`, `news`", inline=False)
            await ctx.respond(embed=embed)
    
    @r6.command(name="stats", description="Look up R6 player stats")
    @discord.option("platform", str, description="uplay / psn / xbl", autocomplete=platform_autocomplete)
    @discord.option("username", str, description="Player username")
    async def stats(
        self,
        ctx: discord.ApplicationContext,
        platform: str,
        username: str
    ):
        await ctx.defer()
        url = f"{R6_API_BASE}/profile/{platform}/{username}"
        headers = {
            "TRN-Api-Key": TRACKER_API_KEY,
            "Accept": "application/json"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
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
            await ctx.followup.send("Error fetching stats.")
    @r6.command(name="map", description="Look up map information")
    @discord.option(
        "name",
        str,
        description="Name of the map"
    )
    async def map_lookup(
        self,
        ctx: discord.ApplicationContext,
        name: str
    ):
        try:
            await ctx.defer()
            if not self.maps:
                await ctx.followup.send("No map data available.", ephemeral=True)
                return
            map_data = DataHelper.find_match(self.maps, name)
            if not map_data:
                await ctx.followup.send(f" Map `{name}` not found.")
                return

            floors = map_data.get("floors", [])
            if not floors:
                await ctx.followup.send("No floor data available.")
                return
            view = MapFloorView(floors=floors, map_name=map_data['name'])
            embed, file_obj = view.create_embed(0)
            if file_obj:
                message = await ctx.followup.send(embed=embed, file=file_obj, view=view)
            else:
                message = await ctx.followup.send(embed=embed, view=view)
            view.message = message
    
        except Exception as e:
            logger.error(f"Error in R6 map command: {e}")
            await ctx.followup.send("Error while processing.", ephemeral=True)

    @r6.command(name="op", description="Look up operator information")
    @discord.option(
        "name",
        str,
        description="Name of the operator"
    )
    async def op_command(
        self,
        ctx: discord.ApplicationContext,
        name: str
    ):
        await ctx.defer()
        op_data = DataHelper.find_match(self.operators, name)
        if not op_data:
            await ctx.followup.send(f"Operator `{name}` not found.", ephemeral=True)
            return
        embed, files = self.create_op_embed(op_data)
        if files:
            await ctx.followup.send(embed=embed, files=files)
        else:
            await ctx.followup.send(embed=embed)

    @r6.command(name="oprandom", description="Get a random operator")
    async def oprandom(
        self,
        ctx: discord.ApplicationContext,
        role: str = Option(str, "Attacker or Defender", required=False)
    ):
        
        await ctx.defer()
        role_val = role.lower() if role else None
        filtered = [op for op in self.operators.values() if not role_val or op["role"].lower() == role_val]
        if not filtered:
            await ctx.followup.send("❌ No operators found.")
            return
        op_data = random.choice(filtered)
        embed, files = self.create_op_embed(op_data)
        if files:
            await ctx.followup.send(embed=embed, files=files)
        else:
            await ctx.followup.send(embed=embed)

    @r6.command(name="oplist", description="List all operators")
    async def oplist(self, ctx: discord.ApplicationContext):
        attackers = sorted([op["name"] for op in self.operators.values() if op["role"].lower() == "attacker"])
        defenders = sorted([op["name"] for op in self.operators.values() if op["role"].lower() == "defender"])

        embed = discord.Embed(
            title="Operators by Role",
            description="Use `/r6 op [name]` to view detailed info or /r6 oprandom for a random operator.",
            color=0x8B0000
        )
        embed.add_field(name="Attackers", value="\n".join(attackers) or "—", inline=True)
        embed.add_field(name="Defenders", value="\n".join(defenders) or "—", inline=True)

        await ctx.respond(embed=embed)

    @r6.command(name="maplist", description="List all maps")
    async def maplist(self, ctx: discord.ApplicationContext):
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

    @r6.command(name="news", description="Get latest R6 news")
    async def news(self, ctx: discord.ApplicationContext):
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

    async def _build_lookups(self):
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

    async def map_name_autocomplete(self, ctx: discord.AutocompleteContext):
        user_input = ctx.value.lower()
        matches = []

        for map_data in self.maps.values():
            name = map_data.get("name", "")
            aliases = map_data.get("aliases",[])
            all_terms = [name] + aliases
            for term in all_terms:
                if user_input in term.lower():
                    matches.append(term)
                    break

        return matches[:25]

    async def operator_name_autocomplete(self, ctx: discord.AutocompleteContext):
        user_input = ctx.value.lower()
        results = []

        for op in self.operators.values():
            name = op.get("name","")
            aliases = op.get("aliases", [])
            all_terms = [name] + aliases
            for term in all_terms:
                if user_input in term.lower():
                    results.append(term)
                    break

        return results[:25]

    @staticmethod
    def create_op_embed(op_data: dict):
        embed = discord.Embed(
            title=f"Operator: {op_data['name']}",
            description=op_data.get("bio", ""),
            color=0x8B0000
        )
        files_to_attach = []

        def process_image(path_or_url: str, is_thumbnail=False):
            nonlocal files_to_attach
            if not path_or_url:
                return None
            if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
                return path_or_url
            # Normalize path and attempt to resolve relative to project root if needed
            path_or_url = path_or_url.replace("\\", "/")
            candidate = Path(path_or_url)
            if not candidate.exists():
                # Try resolving relative to repository root (two levels up from this file)
                repo_root = Path(__file__).resolve().parents[1]
                candidate = (repo_root / path_or_url).resolve()

            if candidate.exists():
                # Make filename unique per operator to avoid clashes
                base_name = candidate.name
                safe_prefix = op_data.get("name", "op").lower().replace(" ", "_")
                filename = f"{safe_prefix}_{base_name}"
                files_to_attach.append(discord.File(str(candidate), filename=filename))
                return f"attachment://{filename}"
            return None

        thumb_url = process_image(op_data.get("icon_url"), is_thumbnail=True)
        img_url = process_image(op_data.get("image_url"))

        if thumb_url:
            embed.set_thumbnail(url=thumb_url)
        if img_url:
            embed.set_image(url=img_url)

        embed.add_field(name="Role", value=op_data.get('role', 'Unknown'), inline=True)
        embed.add_field(name="Squad", value=op_data.get('squad', '—'), inline=True)
        embed.add_field(name="Stats", value=f"Health: {op_data.get('health', '—')}\nSpeed: {op_data.get('speed', '—')}", inline=True)
        embed.add_field(name="Primary Weapons", value="\n".join(op_data.get('primary_weapons', [])) or "—", inline=False)
        embed.add_field(name="Secondary Weapons", value="\n".join(op_data.get('secondary_weapons', [])) or "—", inline=False)
        embed.add_field(name="Primary Gadget", value=op_data.get('primary_gadget', "—") or "—", inline=False)
        embed.add_field(name="Secondary Gadgets", value="\n".join(op_data.get('secondary_gadgets', [])) or "—", inline=False)
        return embed, files_to_attach

    @staticmethod
    def _build_news_embed(news_data):
        embed = discord.Embed(title="📰 Rainbow Six Siege News", color=0x8B0000)
        for entry in news_data:
            embed.add_field(
                name=f"{entry['title']} ({entry['published']})",
                value=f"{entry['summary']}\n[Read more]({entry['link']})",
                inline=False
            )
        embed.set_footer(text="Source: Steam")
        return embed

def setup(bot: commands.Bot):
    cog = R6Cog(bot)
    bot.add_cog(cog)
