import discord
import random
import aiohttp
import json
import feedparser

from discord import app_commands
from discord.ext import commands
from config import TRACKER_API_KEY
from typing import List
from utils.helpers import find_match
TEST_GUILD_ID = 989558855023362110
r6_group = app_commands.Group(name="r6", description="Rainbow Six Siege commands")
class R6Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.operators = {}
        self.maps = {}
        try:
            with open("data/operators.json", "r", encoding="utf-8") as f:
                self.operators = json.load(f)
        except FileNotFoundError:
            print("operators.json not found.")
        except json.JSONDecodeError:
            print("operators.json is corrupted.")

        try:
            with open("data/maps.json", "r", encoding="utf-8") as f:
                self.maps = json.load(f)
        except FileNotFoundError:
            print("maps.json not found.")
        except json.JSONDecodeError:
            print("maps.json is corrupted.")
    @staticmethod
    def create_op_embed(op: dict) -> discord.Embed:
        embed = discord.Embed(title=op['name'], description=op['bio'], color=0x8B0000)
        embed.add_field(name="Role", value=op['role'], inline=True)
        embed.add_field(name="Health", value=op['health'], inline=True)
        embed.add_field(name="Speed", value=op['speed'], inline=True)
        embed.add_field(name="Squad", value=op['squad'], inline=True)
        embed.add_field(name="Primary Weapons", value=", ".join(op['primary_weapons']), inline=False)
        embed.add_field(name="Secondary Weapons", value=", ".join(op['secondary_weapons']), inline=False)
        embed.add_field(name="Primary Gadget", value=op['primary_gadget'], inline=False)
        embed.add_field(name="Secondary Gadgets", value=", ".join(op['secondary_gadgets']), inline=False)
        if op.get('image_url'):
            embed.set_image(url=op['image_url'])
        if op.get('icon_url'):
            embed.set_thumbnail(url=op['icon_url'])
        return embed

    async def operator_autocomplete(self, _interaction: discord.Interaction, current: str):
        current = current.lower()
        suggestions = []
        for op in self.operators.values():
            name_match = op["name"].lower().startswith(current)
            alias_match = any(current in alias.lower() for alias in op.get("aliases", []))

            if name_match:
                suggestions.append(app_commands.Choice(name=op["name"], value=op["name"]))
            elif alias_match:
                suggestions.append(app_commands.Choice(
                    name=f"{op['aliases'][0]} (alias for {op['name']})",
                    value=op["name"]
            ))

        return suggestions[:25]

    async def map_autocomplete(self, _interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        suggestions = []
        for m in self.maps.values():
            if "name" in m and current.lower() in m["name"].lower():
                suggestions.append(app_commands.Choice(name=m["name"], value=m["name"]))
            for alias in m.get("aliases", []):
                if current.lower() in alias.lower():
                    suggestions.append(app_commands.Choice(name=f"{alias} (alias for {m['name']})", value=m["name"]))
        return suggestions[:25]

    @r6_group.command(name="stats", description="Get R6 stats for a player")
    @app_commands.describe(platform="uplay / xbox / psn", username="Player username")
    async def stats(self, interaction: discord.Interaction, platform: str, username: str):
        await interaction.response.defer(thinking=True)
        url = f"https://public-api.tracker.gg/v2/r6/standard/profile/{platform}/{username}"
        headers = {"TRN-Api-Key": TRACKER_API_KEY}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    await interaction.followup.send(f"❌ Could not find stats for `{username}` on `{platform}`.", ephemeral=True)
                    return
                data = await resp.json()

        stats = data['data']['segments'][0]['stats']
        rank_data = stats.get('rankedRank', {})
        rank_value = rank_data.get('displayValue', 'N/A')
        rank_icon = rank_data.get('metadata', {}).get('iconUrl')

        stats = data['data']['segments'][0]['stats']
        embed = discord.Embed(title=f"R6 Stats for {username}", color=0x00ff00)
        embed.add_field(name="Platform", value=platform.upper(), inline=True)
        embed.add_field(name="Rank", value=rank_value, inline=True)
        embed.add_field(name="K/D Ratio", value=stats.get('killsDeathRatio', {}).get('displayValue', 'N/A'), inline=True)
        embed.add_field(name="Win/Loss Ratio", value=stats.get('winLossRatio', {}).get('displayValue', 'N/A'), inline=True)

        if rank_icon:
            embed.set_thumbnail(url=rank_icon)

        await interaction.followup.send(embed=embed)

    @r6_group.command(name="op", description="Get information about an R6 operator")
    @app_commands.describe(name="Name of the operator")
    @app_commands.autocomplete(name=operator_autocomplete)
    async def op_command(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        op_data = find_match(self.operators, name)
        if not op_data:
            await interaction.followup.send(f"❌ Operator `{name}` not found.", ephemeral=True)
            return
        embed = self.create_op_embed(op_data)
        await interaction.followup.send(embed=embed)

    @r6_group.command(name="oprandom", description="Get a random R6 operator")
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

    @r6_group.command(name="oplist", description="List all R6 operators")
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
        for i, col in enumerate(columns):
            embed.add_field(name=f"Column {i+1}", value="\n".join(col), inline=True)
        await interaction.response.send_message(embed=embed)

    @r6_group.command(name="map", description="Get info about a map")
    @app_commands.describe(name="Map name")
    @app_commands.autocomplete(name=map_autocomplete)
    async def map_lookup(self, interaction: discord.Interaction, name: str):
        m = find_match(self.maps, name)
        if not m:
            await interaction.response.send_message(f"❌ Map `{name}` not found.")
            return
        floors = m.get("floors", [])
        if not floors:
            await interaction.response.send_message("❌ No floor data.")
            return

        def make_embed(idx):
            floor = floors[idx]
            return discord.Embed(
                title=f"{m['name']} – {floor['name']}",
                description=f"Floor {idx+1}/{len(floors)}",
                color=0x8B0000
            ).set_image(url=floor.get("image", ""))

        class FloorView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.i = 0
                self.message = None

            @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
            async def back(self, interaction2: discord.Interaction, _):
                self.i = (self.i - 1) % len(floors)
                await interaction2.response.edit_message(embed=make_embed(self.i), view=self)

            @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
            async def forward(self, interaction2: discord.Interaction, _):
                self.i = (self.i + 1) % len(floors)
                await interaction2.response.edit_message(embed=make_embed(self.i), view=self)

        view = FloorView()
        await interaction.response.send_message(embed=make_embed(0), view=view)
        view.message = await interaction.original_response()

    @r6_group.command(name="maplist", description="List all ranked maps")
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

    @r6_group.command(name="news", description="Get the latest Rainbow Six Siege news from Steam")
    async def news(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        feed_url = "https://steamcommunity.com/games/359550/rss/"
        feed = feedparser.parse(feed_url)

        if not feed.entries:
            await interaction.followup.send("❌ Could not fetch R6 news right now. Please try again later.", ephemeral=True)
            return

        embed = discord.Embed(title="📰 Rainbow Six Siege News", color=0x00aff0)

        for entry in feed.entries[:3]:
            title = entry.title
            link = entry.link
            published = entry.published
            summary = entry.summary[:200] + "..." if len(entry.summary) > 200 else entry.summary

            embed.add_field(
                name=f"{title} ({published})",
                value=f"{summary}\n[Read more]({link})",
                inline=False
            )

        embed.set_footer(text="Source: Steam News")
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    bot.tree.add_command(r6_group)
    await bot.add_cog(R6Cog(bot))
    await bot.tree.sync(guild=discord.Object(id=TEST_GUILD_ID))
    print("Added r6_group to command tree")
