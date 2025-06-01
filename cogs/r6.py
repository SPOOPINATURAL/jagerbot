import discord
import random
import aiohttp
import feedparser
import logging
from typing import Dict, Any, List
from discord import app_commands
from discord.ext import commands

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


class R6Cog(commands.GroupCog, group_name="r6"):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.cache = {}
        self.operators: Dict[str, Any] = {}
        self.maps: Dict[str, Any] = {}
        self._operator_names: Dict[str, str] = {}
        self._operator_aliases: Dict[str, str] = {}
        self._map_names: Dict[str, str] = {}
        self._map_aliases: Dict[str, str] = {}

    async def cog_load(self):
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                headers={"TRN-Api-Key": TRACKER_API_KEY}
            )
            await self.load_game_data()
            logger.info("R6Cog loaded and commands synced")
        except Exception as e:
            if self.session and not self.session.closed:
                await self.session.close()
            logger.error(f"Error during cog load: {e}")
            raise

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()
        if self.cache:
            self.cache.cleanup_expired(CACHE_DURATION)
        logger.info("R6Cog unloaded")

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

    async def map_autocomplete_callback(self, interaction: discord.Interaction, current: str):
        current = current.lower()
        choices = []

        for name in self._map_names.values():
            if current in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))

        for alias, name in self._map_aliases.items():
            if current in alias.lower():
                choices.append(app_commands.Choice(name=f"{name} ({alias})", value=name))

        return choices[:25]

    async def operator_autocomplete_callback(self, interaction: discord.Interaction, current: str):
        current = current.lower()
        choices = []

        # Match primary names
        for name_lower, name in self._operator_names.items():
            if current in name_lower:
                choices.append(app_commands.Choice(name=name, value=name))

        # Match aliases
        for alias_lower, name in self._operator_aliases.items():
            if current in alias_lower:
                choices.append(app_commands.Choice(name=f"{name} ({alias_lower})", value=name))

        return choices[:25]

    def create_op_embed(self, op_data: dict) -> discord.Embed:
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

    @app_commands.command(name="map", description="Look up map information")
    @app_commands.describe(name="Name of the map")
    async def map_lookup(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        map_data = DataHelper.find_match(self.maps, name)
        if not map_data:
            await interaction.followup.send(f"❌ Map `{name}` not found.")
            return

        floors = map_data.get("floors", [])
        if not floors:
            await interaction.followup.send("❌ No floor data available.")
            return

        view = MapFloorView(floors=floors, map_name=map_data['name'])
        await interaction.followup.send(embed=view.create_embed(0), view=view)
        view.message = await interaction.original_response()

    @map_lookup.autocomplete('name')
    async def map_name_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.map_autocomplete_callback(interaction, current)

    @app_commands.command(name="op", description="Look up operator information")
    @app_commands.describe(name="Name of the operator")
    async def op_command(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        op_data = DataHelper.find_match(self.operators, name)
        if not op_data:
            await interaction.followup.send(f"❌ Operator `{name}` not found.", ephemeral=True)
            return
        embed = self.create_op_embed(op_data)
        await interaction.followup.send(embed=embed)

    @op_command.autocomplete('name')
    async def op_name_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.operator_autocomplete_callback(interaction, current)

    @app_commands.command(name="oprandom", description="Get a random operator")
    @app_commands.describe(role="Optional: attacker or defender")
    async def oprandom(self, interaction: discord.Interaction, role: str = None):
        await interaction.response.defer()
        role = role.lower() if role else None
        filtered = [op for op in self.operators.values() if not role or op["role"].lower() == role]
        if not filtered:
            await interaction.followup.send("❌ No operators found.")
            return
        op_data = random.choice(filtered)
        embed = self.create_op_embed(op_data)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="oplist", description="List all operators")
    async def oplist(self, interaction: discord.Interaction):
        attackers = sorted([op["name"] for op in self.operators.values() if op["role"].lower() == "attacker"])
        defenders = sorted([op["name"] for op in self.operators.values() if op["role"].lower() == "defender"])

        embed = discord.Embed(
            title="Operators by Role",
            description="Use `/r6 op [name]` to view detailed info.",
            color=0x8B0000
        )
        embed.add_field(name="Attackers", value="\n".join(attackers) or "—", inline=True)
        embed.add_field(name="Defenders", value="\n".join(defenders) or "—", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="maplist", description="List all maps")
    async def maplist(self, interaction: discord.Interaction):
        names = sorted(m["name"] for m in self.maps.values())
        half = len(names) // 2
        embed = discord.Embed(
            title="Available Ranked Maps",
            description="Use `/r6 map (name)` to view floorplans.",
            color=0x8B0000
        )
        embed.add_field(name="Maps A–M", value="\n".join(names[:half]) or "—", inline=True)
        embed.add_field(name="Maps N–Z", value="\n".join(names[half:]) or "—", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="news", description="Get latest R6 news")
    async def news(self, interaction: discord.Interaction):
        await interaction.response.defer()
        cache_key = "r6_news"

        cached_news = self.cache.get(cache_key, CACHE_DURATION)
        if cached_news:
            embed = discord.Embed(title="📰 Rainbow Six Siege News", color=0x8B0000)
            for entry in cached_news:
                embed.add_field(
                    name=f"{entry['title']} ({entry['published']})",
                    value=f"{entry['summary']}\n[Read more]({entry['link']})",
                    inline=False
                )
            embed.set_footer(text="Source: Steam News")
            await interaction.followup.send(embed=embed)
            return

        try:
            feed = feedparser.parse(R6_STEAM_RSS)
            if not feed.entries:
                await interaction.followup.send("❌ Could not fetch R6 news.", ephemeral=True)
                return

            news_data = []
            for entry in feed.entries[:3]:
                summary = entry.summary[:200] + "..." if len(entry.summary) > 200 else entry.summary
                news_data.append({
                    "title": entry.title,
                    "published": entry.published,
                    "summary": summary,
                    "link": entry.link
                })

            self.cache.set(cache_key, news_data)

            embed = discord.Embed(title="📰 Rainbow Six Siege News", color=0x8B0000)
            for entry in news_data:
                embed.add_field(
                    name=f"{entry['title']} ({entry['published']})",
                    value=f"{entry['summary']}\n[Read more]({entry['link']})",
                    inline=False
                )
            embed.set_footer(text="Source: Steam News")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching R6 news: {e}")
            await interaction.followup.send("❌ Error fetching news. Please try again later.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(R6Cog(bot))
