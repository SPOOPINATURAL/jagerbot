import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

class WarframeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    wf_group = app_commands.Group(name="warframe", description="Warframe commands")
    @staticmethod
    async def fetch_json(url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()

    @wf_group.command(name="baro", description="Warframe Baro status")
    async def wfbaro(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await self.fetch_json("https://api.warframestat.us/pc/voidTrader")
        if data.get("active"):
            inventory = "\n".join(
                f"{item['item']} - {item['ducats']} Ducats, {item['credits']} Cr"
                for item in data["inventory"]
            )
            msg = f"**Baro Ki'Teer is at {data['location']} until {data['endString']}**\n\n{inventory}"
        else:
            msg = f"**Baro is not here right now.** Next visit: {data['startString']}"
        await interaction.followup.send(msg)

    @wf_group.command(name="news", description="Warframe News")
    async def wfnews(self, interaction: discord.Interaction):
        news = await self.fetch_json("https://api.warframestat.us/pc/news")
        items = [f"**{n['message']}**\n<{n['link']}>" for n in news[:5]]
        await interaction.response.send_message("\n\n".join(items))

    @wf_group.command(name="nightwave", description="Warframe Nightwave status")
    async def wfnightwave(self, interaction: discord.Interaction):
        data = await self.fetch_json("https://api.warframestat.us/pc/nightwave")
        missions = [f"**{m['title']}** - {m['reputation']} Rep" for m in data.get("activeChallenges", [])]
        await interaction.response.send_message("**Nightwave Challenges:**\n" + "\n".join(missions))

    @wf_group.command(name="price", description="Warframe prices from warframe.market")
    @app_commands.describe(item="Item name")
    async def wfprice(self, interaction: discord.Interaction, item: str):
        item_url = item.replace(" ", "_").lower()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.warframe.market/v1/items/{item_url}/orders") as resp:
                if resp.status != 200:
                    await interaction.response.send_message("❌ Item not found or API issue.")
                    return
                data = await resp.json()
                sell_orders = [
                    o for o in data["payload"]["orders"]
                    if o["order_type"] == "sell" and o["user"]["status"] == "ingame"
                ]
                if sell_orders:
                    cheapest = sorted(sell_orders, key=lambda x: x["platinum"])[0]
                    await interaction.response.send_message(
                        f"💰 Cheapest in-game seller: {cheapest['platinum']}p ({cheapest['user']['ingame_name']})"
                    )
                else:
                    await interaction.response.send_message("❌ No in-game sellers found.")

async def setup(bot: commands.Bot):
    cog = WarframeCog(bot)
    await bot.add_cog(cog)
