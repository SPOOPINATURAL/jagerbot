import logging
import traceback
import discord
import aiohttp
from bs4 import BeautifulSoup
from discord.ext import commands, bridge
from discord import Option

from config import ALLOWED_GUILD_IDS, API_TIMEOUT, MINECRAFT_WIKI_BASE
from utils.embed_builder import EmbedBuilder

logger = logging.getLogger(__name__)
class MinecraftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wiki_base_url = MINECRAFT_WIKI_BASE
        super().__init__()
    @bridge.bridge_group(name="mc", description="Minecraft commands")
    async def mc(self, ctx: discord.ApplicationContext):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Minecraft Commands",
                description="Use `/mc <command>` to get help on a specific command.",
                color=0x8B0000
            )
            embed.add_field(name="Available Commands", value="`wiki`, `recipe`, `advancement`, `enchant`, `biome`, `structure`, `player`, `serverstatus`", inline=False)
            await ctx.respond(embed=embed)
    @mc.command(name="wiki", description="Search Minecraft Wiki")
    async def mc_wiki(
        self,
        ctx: discord.ApplicationContext,
        query: str = Option(str, "The wiki page to search")
    ):
        embed = self.create_wiki_embed(
            f"📖 Minecraft Wiki: {query.title()}",
            query.replace(" ", "_")
        )
        await ctx.respond(embed=embed)

    @mc.command(name="recipe", description="Get crafting recipe from Minecraft Wiki")
    async def mc_recipe(self, ctx: discord.ApplicationContext, item: str = Option(str, "The item to get recipe for")):
        await ctx.defer()
        item_name = item.replace(" ", "_").title()
        wiki_url = f"{self.wiki_base_url}/{item_name}"

        recipe_image_url = None
        try:
            timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(wiki_url) as resp:
                    if resp.status != 200:
                        await ctx.followup.send(f"❌ Could not fetch wiki page for `{item}`.")
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
        await ctx.followup.send(embed=embed)

    @mc.command(name="advancement", description="Get advancement info from Minecraft Wiki")
    async def mc_advancement(
        self,
        ctx: discord.ApplicationContext,
        name: str = Option(str, "Advancement name")
    ):
        url = f"https://minecraft.wiki/w/{name.replace(' ', '_')}"
        embed = discord.Embed(
            title=f"🏆 Info on advancement {name.title()}",
            description=f"[View on wiki]({url})",
            color=0x55a630
        )
        await ctx.respond(embed=embed)

    @mc.command(name="enchant", description="Get enchantment info from Minecraft Wiki")
    async def mc_enchant(
        self,
        ctx: discord.ApplicationContext,
        name: str = Option(str, "Enchantment name")
    ):
        url = f"https://minecraft.wiki/w/{name.replace(' ', '_')}"
        embed = discord.Embed(
            title=f"✨ Enchantment {name.title()} details",
            description=f"[View on wiki]({url})",
            color=0x55a630
        )
        await ctx.respond(embed=embed)

    @mc.command(name="biome", description="Get biome info from Minecraft Wiki")
    async def mc_biome(
        self,
        ctx: discord.ApplicationContext,
        name: str = Option(str, "Biome name")
    ):
        url = f"https://minecraft.wiki/w/{name.replace(' ', '_')}"
        embed = discord.Embed(
            title=f"🌲 Biome {name.title()} info",
            description=f"[View on wiki]({url})",
            color=0x55a630
        )
        await ctx.respond(embed=embed)

    @mc.command(name="structure", description="Get structure info from Minecraft Wiki")
    async def mc_structure(
        self,
        ctx: discord.ApplicationContext,
        name: str = Option(str, "Structure name")
    ):
        url = f"https://minecraft.wiki/w/{name.replace(' ', '_')}"
        embed = discord.Embed(
            title=f"🏛️ Structure {name.title()}",
            description=f"[View on wiki]({url})",
            color=0x55a630
        )
        await ctx.respond(embed=embed)

    @mc.command(name="player", description="Get Minecraft player info")
    async def mc_player(
        self,
        ctx: discord.ApplicationContext,
        username: str = Option(str, "Minecraft IGN")
    ):
        await ctx.defer()
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with self.session.get(
                f"https://api.mojang.com/users/profiles/minecraft/{username}", headers=headers
            ) as resp:
                if resp.status != 200:
                    await ctx.followup.send("❌ Could not find that player.")
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
            await ctx.followup.send(embed=embed)
        except Exception as e:
            await ctx.followup.send(f"❌ Error: `{e}`")

    @mc.command(name="serverstatus", description="Get the status of the VDSMP")
    async def mc_serverstatus(self, ctx: discord.ApplicationContext):
        if ctx.guild and ctx.guild.id not in ALLOWED_GUILD_IDS:
            await ctx.respond(
                "❌ This command is not available in this server.",
                ephemeral=True
            )
            return

        await ctx.defer()

        server_ip = "vdsmp.mc.gg"

        try:
            async with self.session.get(f"https://api.mcsrvstat.us/2/{server_ip}") as resp:
                if resp.status != 200:
                    await ctx.followup.send("❌ Error contacting the status API.")
                    return
                data = await resp.json()

            if not data.get("online", False):
                await ctx.followup.send("❌ The server is currently **offline**.")
                return

            # MOTD
            motd = "No MOTD"
            motd_data = data.get("motd", {})
            if motd_data:
                motd_clean = motd_data.get("clean")
                if motd_clean and isinstance(motd_clean, list):
                    motd = " ".join(motd_clean)

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
            if icon and not icon.startswith("data:image"):
                embed.set_thumbnail(url=icon)

            await ctx.followup.send(embed=embed)

        except Exception as e:
            tb = traceback.format_exc()
            await ctx.followup.send(f"❌ Error in mcserverstatus:\n```\n{tb}\n```")

    async def create_wiki_embed(self, title: str, page: str) -> discord.Embed:
        url = f"{self.wiki_base_url}/{page}"
        return EmbedBuilder.info(
            title=title,
            description=f"[Click here to view the wiki page]({url})",
            color=0x55a630
        )

    async def _find_recipe_image(self, soup: BeautifulSoup) -> str:
        for selector in [("table", "crafting-table"), ("div", "crafting"), ("img", None)]:
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

async def setup(bot: commands.Bot):
    cog = MinecraftCog(bot)
    await bot.add_cog(cog)
    
