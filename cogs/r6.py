import discord
import random
import aiohttp
import json
import feedparser
import logging
from typing import Dict, Optional, List, Any
from discord import app_commands
from discord.ext import commands
from utils.base_cog import BaseCog
from utils.autocomplete import AutocompleteMixin
from utils.views import PaginationView
from utils.helpers import DataHelper, FileHelper
from config import (
    TEST_GUILD_ID,
    TRACKER_API_KEY,
    R6_API_BASE,
    R6_STEAM_RSS,
    R6_VIEW_TIMEOUT,
    CACHE_DURATION,
    API_TIMEOUT
)

r6_group = app_commands.Group(name="r6", description="Rainbow Six Siege commands")
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

class R6Cog(BaseCog, AutocompleteMixin):
    def __init__(self, bot):
        super().__init__(bot)
        self.operators: Dict[str, Any] = {}
        self.maps: Dict[str, Any] = {}
        self._operator_names: Dict[str, str] = {}
        self._operator_aliases: Dict[str, str] = {}
        self._map_names: Dict[str, str] = {}
        self._map_aliases: Dict[str, str] = {}
        self.bot = bot
        self.session = None
        self.cache = {}
        self.r6_data = {}

    async def load_game_data(self):
        try:
            operators_data = await DataHelper.load_json_file("data/operators.json")
            maps_data = await DataHelper.load_json_file("data/maps.json")
            
            if not isinstance(operators_data, dict):
                raise ValueError("Operators data must be a dictionary")
            if not isinstance(maps_data, dict):
                raise ValueError("Maps data must be a dictionary")

            for op_id, op_data in operators_data.items():
                if not isinstance(op_data, dict):
                    raise ValueError(f"Invalid operator data format for {op_id}")
                required_fields = ['name', 'role', 'health', 'speed', 'squad', 'primary_weapons', 'secondary_weapons', 'primary_gadget', 'secondary_gadgets']
                missing_fields = [field for field in required_fields if field not in op_data]
                if missing_fields:
                    raise ValueError(f"Operator {op_id} missing required fields: {', '.join(missing_fields)}")

            for map_id, map_data in maps_data.items():
                if not isinstance(map_data, dict):
                    raise ValueError(f"Invalid map data format for {map_id}")
                if 'name' not in map_data:
                    raise ValueError(f"Map {map_id} missing required field: name")

            self.operators = operators_data
            self.maps = maps_data
            
            if not self.operators:
                raise ValueError("No operator data loaded")
            if not self.maps:
                raise ValueError("No map data loaded")
            
            self._build_lookups()
            logger.info("R6 data loaded successfully")
        
        except FileNotFoundError as e:
            logger.error(f"Required data file not found: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in data files: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid data structure: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading R6 data: {e}")
            self.operators = {}
            self.maps = {}
            raise

    async def cog_load(self):
        await super().cog_load()
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
                headers={"TRN-Api-Key": TRACKER_API_KEY}
            )
            await self.load_game_data()
        except Exception as e:
            if self.session and not self.session.closed:
                await self.session.close()
            logger.error(f"Error during cog load: {e}")
            raise

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        if self.cache:
            self.cache.cleanup_expired(CACHE_DURATION)
        await super().cog_unload()
        logger.info("R6Cog unloaded")

    async def _load_json_file(self, path: str) -> dict:
        cached = self.cache.get(path, CACHE_DURATION)
        if cached:
            return cached

        return await DataHelper.safe_json_operation(
            FileHelper.load_json_file,
            path
        )

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

    async def map_autocomplete_callback(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        choices = []
        current = current.lower()

        for name in self._map_names.values():
            if current in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))

        for alias, name in self._map_aliases.items():
            if current in alias.lower():
                choices.append(app_commands.Choice(name=f"{name} ({alias})", value=name))

        return choices[:25]

    async def operator_autocomplete_callback(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        return self.get_suggestions(
            current=current,
            primary_dict=self._operator_names,
            alias_dict=self._operator_aliases,
            cache_prefix="op_autocomplete"
        )
    def create_op_embed(self, op_data: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"Operator: {op_data['name']}",
            color=0x8B0000
        )
        embed.add_field(name="Role", value=op_data['role'], inline=True)
        embed.add_field(name="Squad", value=op_data['squad'], inline=True)
        embed.add_field(name="Stats", value=f"Health: {op_data['health']}\nSpeed: {op_data['speed']}", inline=True)

        embed.add_field(name="Primary Weapons", value="\n".join(op_data['primary_weapons']) or "—", inline=False)
        embed.add_field(name="Secondary Weapons", value="\n".join(op_data['secondary_weapons']) or "—", inline=False)
        embed.add_field(name="Primary Gadget", value=op_data['primary_gadget'] or "—", inline=False)
        embed.add_field(name="Secondary Gadgets", value="\n".join(op_data['secondary_gadgets']) or "—", inline=False)

        return embed

    @r6_group.command(name="map", description="Look up map information")
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
    async def map_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.map_autocomplete_callback(interaction, current)

    @r6_group.command(name="op")
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
    async def op_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        return await self.operator_autocomplete_callback(interaction, current)

    @r6_group.command(name="oprandom")
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

    @r6_group.command(name="oplist")
    async def oplist(self, interaction: discord.Interaction):
        names = sorted(op["name"] for op in self.operators.values())
        columns = [[], [], []]
        for i, name in enumerate(names):
            columns[i % 3].append(name)

        embed = discord.Embed(
            title="Available Operators",
            description="Use `/r6 op [name]` to view detailed info.",
            color=0x8B0000
        )
        
        for i, col in enumerate(columns, 1):
            embed.add_field(name=f"Column {i}", value="\n".join(col), inline=True)
            
        await interaction.response.send_message(embed=embed)

    @r6_group.command(name="maplist")
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

    @r6_group.command(name="news")
    async def news(self, interaction: discord.Interaction):
        await interaction.response.defer()
        cache_key = "r6_news"
        cached_news = self.cache.get(cache_key, CACHE_DURATION)

        if cached_news:
            await interaction.followup.send(embed=cached_news)
            return

        try:
            feed = feedparser.parse(R6_STEAM_RSS)
            if not feed.entries:
                await interaction.followup.send(
                    "❌ Could not fetch R6 news right now. Please try again later.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(title="📰 Rainbow Six Siege News", color=0x8B0000)
            for entry in feed.entries[:3]:
                summary = entry.summary[:200] + "..." if len(entry.summary) > 200 else entry.summary
                embed.add_field(
                    name=f"{entry.title} ({entry.published})",
                    value=f"{summary}\n[Read more]({entry.link})",
                    inline=False
                )

            embed.set_footer(text="Source: Steam News")
            self.cache.set(cache_key, embed)
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error fetching R6 news: {e}")
            await interaction.followup.send("❌ Error fetching news. Please try again later.", ephemeral=True)


async def setup(bot: commands.Bot):
    try:
        cog = R6Cog(bot)
        await bot.add_cog(cog)

        if not hasattr(bot, 'added_command_groups'):
            bot.added_command_groups = set()

        if "r6" not in bot.added_command_groups:
            bot.tree.add_command(r6_group)
            bot.added_command_groups.add("r6")

        logger.info(f"{cog.__class__.__name__} loaded and commands synced")
    except Exception as e:
        logger.error(f"Failed to setup {cog.__class__.__name__}: {e}")
        raise
