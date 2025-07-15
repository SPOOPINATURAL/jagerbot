import discord
import logging
from typing import Optional
from discord.ext import commands
from discord.ui import View, Button
from config import (
    WF_API_BASE,
    WF_MARKET_API,
    WF_STREAMS_API,
    CACHE_DURATION,
    WF_COLOR
)

logger = logging.getLogger(__name__)

def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

class BaroPaginator(View):
    def __init__(self, items: list[dict], location: str, end_str: str):
        super().__init__(timeout=180)
        self.items = items
        self.location = location
        self.end_str = end_str
        self.per_page = 10
        self.pages = list(chunk_list(self.items, self.per_page))
        self.current_page = 0
        self.total_pages = len(self.pages)

        self.prev_button = Button(label="Previous", style=discord.ButtonStyle.secondary)
        self.next_button = Button(label="Next", style=discord.ButtonStyle.secondary)

        self.prev_button.callback = self.go_prev
        self.next_button.callback = self.go_next

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def go_prev(self, interaction: discord.Interaction):
        self.current_page = (self.current_page - 1) % self.total_pages
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def go_next(self, interaction: discord.Interaction):
        self.current_page = (self.current_page + 1) % self.total_pages
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(title=f"Baro Ki'Teer at {self.location}", color=WF_COLOR)
        embed.description = f"Leaving in {self.end_str}\n\nPage {self.current_page + 1} / {self.total_pages}"
        for item in self.pages[self.current_page]:
            embed.add_field(
                name=item['item'],
                value=f"{item['ducats']} Ducats\n{item['credits']} Credits",
                inline=True
            )
        return embed

class WarframeCog(commands.Cog):
    wf_group = discord.SlashCommandGroup("wf", "Warframe related commands")
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.cache = {}
        super().__init__()


    @wf_group.command(name="baro", description="Check Baro Ki'Teer's status and inventory")
    async def baro(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        data = await self.get_cached_data("voidTrader")
        if not data:
            await ctx.followup.send("❌ Failed to fetch Baro data.", ephemeral=True)
            return

        if data.get("active"):
            inventory = data.get("inventory", [])
            if not inventory:
                await ctx.followup.send("Baro has no inventory currently.", ephemeral=True)
                return
            paginator = BaroPaginator(
                items=inventory,
                location=data.get("location", "Unknown"),
                end_str=data.get("endString", "Unknown time")
            )
            embed = paginator.create_embed()
            await ctx.followup.send(embed=embed, view=paginator)
        else:
            embed = discord.Embed(title="Baro Ki'Teer", color=WF_COLOR)
            embed.description = f"Next visit: {data.get('startString', 'Unknown')}\nLocation: {data.get('location', 'Unknown')}"
            await ctx.followup.send(embed=embed)

    @wf_group.command(name="news", description="Show latest Warframe news")
    async def wfnews(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        try:
            data = await self.get_cached_data("news")
            if not data:
                await ctx.followup.send("❌ Failed to fetch news.", ephemeral=True)
                return
            embed = discord.Embed(title="Warframe News", color=WF_COLOR)
            for news in data[:5]:
                embed.add_field(
                    name=news['message'],
                    value=f"[Read More]({news['link']})",
                    inline=False
                )
            await ctx.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in news command: {e}")
            await ctx.followup.send("❌ Error fetching news.", ephemeral=True)

    @wf_group.command(name="nightwave", description="Show current Nightwave challenges")
    async def nightwave(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        try:
            data = await self.get_cached_data("nightwave")
            if not data:
                await ctx.followup.send("❌ Failed to fetch Nightwave data.", ephemeral=True)
                return
            embed = discord.Embed(title="Nightwave Challenges", color=WF_COLOR)
            for challenge in data.get("activeChallenges", []):
                embed.add_field(
                    name=f"{challenge['title']} ({challenge['reputation']} Rep)",
                    value=challenge.get('desc', 'No description'),
                    inline=False
                )
            await ctx.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in nightwave command: {e}")
            await ctx.followup.send("❌ Error fetching Nightwave data.", ephemeral=True)

    @wf_group.command(name="price", description="Check item prices from warframe.market")
    async def wfprice(
        self,
        ctx: discord.ApplicationContext,
        item: discord.Option(str, "Item name to check prices for")
    ):
        await ctx.defer()
        item_url = item.replace(" ", "_").lower()
        url = f"{WF_MARKET_API}/items/{item_url}/orders"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    await ctx.followup.send("❌ Item not found.", ephemeral=True)
                    return
                data = await resp.json()
                sell_orders = [
                    order for order in data.get("payload", {}).get("orders", [])
                    if order.get("order_type") == "sell" and order.get("user", {}).get("status") == "ingame"
                ]
                if not sell_orders:
                    await ctx.followup.send("❌ No active sellers found.")
                    return

                cheapest = sorted(sell_orders, key=lambda x: x.get("platinum", 9999))[:5]
                embed = discord.Embed(title=f"Prices for {item}", color=WF_COLOR)
                for order in cheapest:
                    embed.add_field(
                           name=f"{order.get('platinum')}p",
                        value=f"Seller: {order.get('user', {}).get('ingame_name', 'Unknown')}",
                        inline=True
                    )
                await ctx.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error fetching price for {item}: {e}")
            await ctx.followup.send("❌ Error fetching prices.", ephemeral=True)

    @wf_group.command(name="streams", description="Show current and upcoming Warframe streams")
    async def streams(self, ctx: discord.ApplicationContext):
        await ctx.defer(thinking=True)
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

            await ctx.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error fetching streams: {e}")
            await ctx.followup.send("❌ Error fetching stream data.", ephemeral=True)

    async def get_cached_data(self, endpoint: str, max_age: int = CACHE_DURATION) -> Optional[dict]:
        cache_key = f"wf_{endpoint}"
        cached = self.cache.get(cache_key)
        if cached:
            data, timestamp = cached
            if (discord.utils.utcnow() - timestamp).total_seconds() < max_age:
                return data

        url = f"{WF_API_BASE}/{endpoint}"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"API error for {endpoint}: {resp.status}")
                    return None
                data = await resp.json()
                self.cache[cache_key] = (data, discord.utils.utcnow())
                return data
        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
            return None

def setup(bot: commands.Bot):
    cog = WarframeCog(bot)
    bot.add_cog(cog)
    bot.add_application_command(cog.wf_group)
