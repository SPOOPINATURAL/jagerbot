import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from bs4 import BeautifulSoup
from config import ALLOWED_GUILD_IDS

class MinecraftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mcwiki", description="Search Minecraft Wiki")
    @app_commands.describe(query="The wiki page to search")
    async def mcwiki(self, interaction: discord.Interaction, query: str):
        search = query.replace(" ", "_")
        url = f"https://minecraft.wiki/w/{search}"
        embed = discord.Embed(
            title=f"📖 Minecraft Wiki: {query.title()}",
            description=f"[Click here to view the wiki page]({url})",
            color=0x55a630
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mcrecipe", description="Get crafting recipe from Minecraft Wiki")
    @app_commands.describe(item="The item to get recipe for")
    async def mcrecipe(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        item_name = item.replace(" ", "_").title()
        wiki_url = f"https://minecraft.wiki/w/{item_name}"

        recipe_image_url = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(wiki_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(f"❌ Could not fetch wiki page for `{item}`.")
                        return
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")

                    crafting_table = soup.find("table", class_="crafting-table")
                    if crafting_table:
                        img = crafting_table.find("img")
                        if img and img.has_attr("src"):
                            recipe_image_url = img["src"]

                    if not recipe_image_url:
                        crafting_div = soup.find(lambda tag: tag.name == "div" and ("crafting" in tag.get("id", "") or "crafting" in tag.get("class", [])))
                        if crafting_div:
                            img = crafting_div.find("img")
                            if img and img.has_attr("src"):
                                recipe_image_url = img["src"]

                    if not recipe_image_url:
                        img = soup.find("img")
                        if img and img.has_attr("src"):
                            recipe_image_url = img["src"]

                    if recipe_image_url and recipe_image_url.startswith("//"):
                        recipe_image_url = "https:" + recipe_image_url
                    elif recipe_image_url and recipe_image_url.startswith("/"):
                        recipe_image_url = "https://minecraft.wiki" + recipe_image_url
        except Exception:
            recipe_image_url = None

        embed = discord.Embed(
            title=f"Crafting Recipe for {item.title()}",
            url=wiki_url,
            color=0x55a630,
            description=f"[View full page on Minecraft Wiki]({wiki_url})"
        )
        if recipe_image_url:
            embed.set_image(url=recipe_image_url)
        else:
            embed.set_footer(text="Recipe image not found, please check the wiki page link.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="mcadvancement", description="Get advancement info from Minecraft Wiki")
    @app_commands.describe(name="Advancement name")
    async def mcadvancement(self, interaction: discord.Interaction, name: str):
        search = name.replace(" ", "_")
        url = f"https://minecraft.wiki/w/{search}"
        embed = discord.Embed(
            title=f"🏆 Info on advancement {name.title()}",
            description=f"[View on wiki]({url})",
            color=0x55a630
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mcenchant", description="Get enchantment info from Minecraft Wiki")
    @app_commands.describe(name="Enchantment name")
    async def mcenchant(self, interaction: discord.Interaction, name: str):
        search = name.replace(" ", "_")
        url = f"https://minecraft.wiki/w/{search}"
        embed = discord.Embed(
            title=f"✨ Enchantment {name.title()} details",
            description=f"[View on wiki]({url})",
            color=0x55a630
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mcbiome", description="Get biome info from Minecraft Wiki")
    @app_commands.describe(name="Biome name")
    async def mcbiome(self, interaction: discord.Interaction, name: str):
        search = name.replace(" ", "_")
        url = f"https://minecraft.wiki/w/{search}"
        embed = discord.Embed(
            title=f"🌲 Biome {name.title()} info",
            description=f"[View on wiki]({url})",
            color=0x55a630
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mcstructure", description="Get structure info from Minecraft Wiki")
    @app_commands.describe(name="Structure name")
    async def mcstructure(self, interaction: discord.Interaction, name: str):
        search = name.replace(" ", "_")
        url = f"https://minecraft.wiki/w/{search}"
        embed = discord.Embed(
            title=f"🏛️ Structure {name.title()}",
            description=f"[View on wiki]({url})",
            color=0x55a630
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mcplayer", description="Get Minecraft player info")
    @app_commands.describe(username="Minecraft IGN")
    async def mcplayer(self, interaction: discord.Interaction, username: str):
        try:
            await interaction.response.defer()
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "Mozilla/5.0"}
                async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{username}", headers=headers) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("❌ Could not find that player.")
                        return
                    data = await resp.json()
                    uuid = data["id"]

            head_url = f"https://minotar.net/helm/{uuid}/128.png"
            skin_url = f"https://visage.surgeplay.com/full/512/{uuid}.png"

            embed = discord.Embed(
                title=f"Minecraft Player: {username}",
                description=f"UUID: `{uuid}`",
                color=0x8B0000
            )
            embed.set_image(url=skin_url)
            embed.set_thumbnail(url=head_url)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: `{e}`")

    @app_commands.command(name="mcserverstatus", description="Get the status of the VDSMP")
    async def mcserverstatus(self, interaction: discord.Interaction):
        if interaction.guild_id not in ALLOWED_GUILD_IDS:
            await interaction.response.send_message(
                "❌ This command is not available in this server.",
                ephemeral=True
            )
            return
        await interaction.response.defer()
        try:
            server_ip = "vdsmp.mc.gg"

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.mcsrvstat.us/2/{server_ip}") as resp:
                    if resp.status != 200:
                        await interaction.response.send_message("❌ Error contacting the status API.")
                        return
                    data = await resp.json()

            if not data.get("online"):
                await interaction.response.send_message("❌ The server is currently **offline**.")
                return

            motd = " ".join(data["motd"]["clean"]) if "motd" in data else "No MOTD"
            players = data.get("players", {})
            online = players.get("online", 0)
            max_players = players.get("max", 0)
            version = data.get("version", "Unknown")

            embed = discord.Embed(
                title="🌐 Minecraft Server Status",
                description="Your private server is **online** ✅",
                color=0x00cc66
            )
            embed.add_field(name="📃 MOTD", value=motd, inline=False)
            embed.add_field(name="👥 Players", value=f"{online}/{max_players}", inline=True)
            embed.add_field(name="🛠 Version", value=version, inline=True)

            icon = data.get("icon")
            if icon and icon.startswith("data:image/png;base64,"):
                pass
            elif icon:
                embed.set_thumbnail(url=icon)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error in mcserverstatus: `{e}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(MinecraftCog(bot))