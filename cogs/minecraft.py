import discord
from discord.ext import commands
from discord import app_commands
from utils.base_cog import BaseCog
from utils.embed_builder import EmbedBuilder
import aiohttp
import logging
from bs4 import BeautifulSoup
from config import (ALLOWED_GUILD_IDS, API_TIMEOUT, TEST_GUILD_ID, MINECRAFT_WIKI_BASE)

mc_group = app_commands.Group(name="mc", description="Minecraft commands")
logger = logging.getLogger(__name__)
class MinecraftCog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.session_timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        self.wiki_base_url = MINECRAFT_WIKI_BASE

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def cog_unload(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    def create_wiki_embed(self, title: str, page: str) -> discord.Embed:
        url = f"{self.wiki_base_url}/{page}"
        return EmbedBuilder.info(
            title=title,
            description=f"[Click here to view the wiki page]({url})",
            color=0x55a630
        )

    @mc_group.command(name="wiki", description="Search Minecraft Wiki")
    @app_commands.describe(query="The wiki page to search")
    async def mcwiki(self, interaction: discord.Interaction, query: str):
        embed = self.create_wiki_embed(
            f"📖 Minecraft Wiki: {query.title()}",
            query.replace(" ", "_")
        )

        await interaction.response.send_message(embed=embed)

    @mc_group.command(name="recipe", description="Get crafting recipe from Minecraft Wiki")
    @app_commands.describe(item="The item to get recipe for")
    async def mcrecipe(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        item_name = item.replace(" ", "_").title()
        wiki_url = f"{self.wiki_base_url}/{item_name}"


        recipe_image_url = None
        async with aiohttp.ClientSession(timeout=self.session_timeout):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(wiki_url) as resp:
                        if resp.status != 200:
                            await interaction.followup.send(f"❌ Could not fetch wiki page for `{item}`.")
                            return
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    recipe_image_url = self._find_recipe_image(soup)
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

    def _find_recipe_image(self, soup: BeautifulSoup) -> str:
        """Helper method to find recipe image in wiki page"""
        for selector in [
            ("table", "crafting-table"),
            ("div", "crafting"),
            ("img", None)
        ]:
            tag, class_name = selector
            element = soup.find(tag, class_=class_name) if class_name else soup.find(tag)

            if element:
                img = element.find("img") if tag != "img" else element
                if img and img.has_attr("src"):
                    src = img["src"]
                    if src.startswith("//"):
                        return f"https:{src}"
                    elif src.startswith("/"):
                        return f"{self.wiki_base_url}{src}"
                    return src
        return None

    @mc_group.command(name="advancement", description="Get advancement info from Minecraft Wiki")
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

    @mc_group.command(name="enchant", description="Get enchantment info from Minecraft Wiki")
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

    @mc_group.command(name="biome", description="Get biome info from Minecraft Wiki")
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

    @mc_group.command(name="structure", description="Get structure info from Minecraft Wiki")
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

    @mc_group.command(name="player", description="Get Minecraft player info")
    @app_commands.describe(username="Minecraft IGN")
    async def mcplayer(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout
) as session:
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

    @mc_group.command(name="serverstatus", description="Get the status of the VDSMP")
    async def mcserverstatus(self, interaction: discord.Interaction):
        if interaction.guild_id not in ALLOWED_GUILD_IDS:
            await interaction.response.send_message(
                "❌ This command is not available in this server.",
                ephemeral=True
            )
            return
        await interaction.response.defer()
        server_ip = "vdsmp.mc.gg"
        try:

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
                description="The server is **online** ✅",
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
    try:
        cog = MinecraftCog(bot)
        await bot.add_cog(cog)

        if not hasattr(bot, 'added_command_groups'):
            bot.added_command_groups = set()

        if "mc" not in bot.added_command_groups:
            bot.tree.add_command(mc_group)
            bot.added_command_groups.add("mc")

        logger.info(f"{cog.__class__.__name__} loaded and commands synced")
    except Exception as e:
        logger.error(f"Failed to setup {cog.__class__.__name__}: {e}")
        raise
