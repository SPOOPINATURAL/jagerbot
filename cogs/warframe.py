import discord
import aiohttp
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands
from utils.base_cog import BaseCog
from config import (
    TEST_GUILD_ID,
    WF_API_BASE,
    WF_MARKET_API,
    WF_STREAMS_API,
    CACHE_DURATION,
    WF_COLOR
)

wf_group = app_commands.Group(name="wf", description="Warframe commands")

logger = logging.getLogger(__name__)
class WarframeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.cache = {}

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def cog_unload(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_cached_data(self, endpoint: str, max_age: int = CACHE_DURATION) -> Optional[dict]:
        cache_key = f"wf_{endpoint}"
        cached = self.cache.get(cache_key, CACHE_DURATION)
        if cached:
            return cached

        url = f"{WF_API_BASE}/{endpoint}"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"API error for {endpoint}: {resp.status}")
                    return None
                data = await resp.json()
                self.cache.set(cache_key, data)
                return data
        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
            return None

    def create_baro_embed(self, data: dict) -> discord.Embed:
        embed = discord.Embed(color=WF_COLOR)
        if data.get("active"):
            embed.title = f"Baro Ki'Teer at {data['location']}"
            embed.description = f"Leaving in {data['endString']}"

            for item in data["inventory"]:
                embed.add_field(
                    name=item['item'],
                    value=f"{item['ducats']} Ducats\n{item['credits']} Credits",
                    inline=True
                )
        else:
            embed.title = "Baro Ki'Teer"
            embed.description = f"Next visit: {data['startString']}\nLocation: {data['location']}"

        return embed

    @wf_group.command(name="baro", description="Check Baro Ki'Teer's status and inventory")
    async def baro(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            data = await self.get_cached_data("voidTrader")
            if not data:
                await interaction.followup.send("❌ Failed to fetch Baro data.", ephemeral=True)
                return

            embed = self.create_baro_embed(data)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in baro command: {e}")
            await interaction.followup.send("❌ Error fetching Baro data.", ephemeral=True)


    @wf_group.command(name="news", description="Show latest Warframe news")
    async def wfnews(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await self.get_cached_data("news")
        if not data:
            await interaction.followup.send("❌ Failed to fetch news.", ephemeral=True)
            return

        embed = discord.Embed(title="Warframe News", color=WF_COLOR)
        for news in data[:5]:
            embed.add_field(
                name=news['message'],
                value=f"[Read More]({news['link']})",
                inline=False
            )
        await interaction.followup.send(embed=embed)

    @wf_group.command(name="nightwave", description="Show current Nightwave challenges")
    async def nightwave(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await self.get_cached_data("nightwave")
        if not data:
            await interaction.followup.send("❌ Failed to fetch Nightwave data.", ephemeral=True)
            return

        embed = discord.Embed(title="Nightwave Challenges", color=WF_COLOR)
        for challenge in data.get("activeChallenges", []):
            embed.add_field(
                name=f"{challenge['title']} ({challenge['reputation']} Rep)",
                value=challenge.get('desc', 'No description'),
                inline=False
            )
        await interaction.followup.send(embed=embed)

    @wf_group.command(name="price", description="Check item prices from warframe.market")
    @app_commands.describe(item="Item name to check prices for")
    async def wfprice(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        item_url = item.replace(" ", "_").lower()
        url = f"{WF_MARKET_API}/items/{item_url}/orders"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    await interaction.followup.send("❌ Item not found.", ephemeral=True)
                    return

                data = await resp.json()
                sell_orders = [
                    order for order in data["payload"]["orders"]
                    if order["order_type"] == "sell" and
                       order["user"]["status"] == "ingame"
                ]

                if not sell_orders:
                    await interaction.followup.send("❌ No active sellers found.")
                    return

                cheapest = sorted(sell_orders, key=lambda x: x["platinum"])[:5]
                embed = discord.Embed(title=f"Prices for {item}", color=WF_COLOR)
                for order in cheapest:
                    embed.add_field(
                        name=f"{order['platinum']}p",
                        value=f"Seller: {order['user']['ingame_name']}",
                        inline=True
                    )
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching price for {item}: {e}")
            await interaction.followup.send("❌ Error fetching prices.", ephemeral=True)

    @wf_group.command(name="streams", description="Show current and upcoming Warframe streams")
    async def streams(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            async with self.session.get(f"{WF_STREAMS_API}/streams/upcoming") as resp:
                upcoming = await resp.json() if resp.status == 200 else []

            async with self.session.get(f"{WF_STREAMS_API}/streams/active") as resp:
                active = await resp.json() if resp.status == 200 else []

            embed = discord.Embed(title="Warframe Streams", color=WF_COLOR)
            if upcoming:
                value = ""
                for stream in upcoming[:5]:
                    drops = ", ".join(stream.get('drops', [])) or "No drops"
                    value += f"**{stream['title']}**\n{drops}\nStarts: {stream['startTime']}\n\n"
                embed.add_field(name="Upcoming Streams", value=value or "None", inline=False)

            if active:
                value = ""
                for stream in active[:5]:
                    drops = ", ".join(stream.get('drops', [])) or "No drops"
                    value += f"[{stream['title']}]({stream['url']})\n{drops}\n\n"
                embed.add_field(name="Active Streams", value=value or "None", inline=False)

            if not upcoming and not active:
                embed.description = "No streams found."

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching streams: {e}")
            await interaction.followup.send("❌ Error fetching stream data.", ephemeral=True)

async def setup(bot: commands.Bot):
    try:
        cog = WarframeCog(bot)
        
        bot.tree.add_command(wf_group)
        
        await bot.add_cog(cog)
        
        logger.info("WarframeCog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to setup WarframeCog: {e}")
        raise