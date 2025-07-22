import discord
import feedparser
import config
import logging
from discord.ext import bridge, commands
from utils.embed_builder import EmbedBuilder
from utils.helpers import FileHelper, Datahelper
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Ultracog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.ukranks = bot.ukranks
        self.ukweapons = bot.ukweapons
        self._news_cache = {
            "data": None,
            "timestamp": None,
        }
        super().__init__()

    @bridge.bridge_group(name='ultrakill', description="Ultrakill commands")
    async def ultrakill(self, ctx: discord.ApplicationContext):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Ultrakill Commands",
                description="Use `/ultrakill <command>` to get help on a specific command.",
                color=0x8B0000
            )
            embed.add_field(name="Available Commands", value="`prank`, `weapon`, `weaponlist`, `news`", inline=False)
            await ctx.respond(embed=embed)
    
    @ultrakill.command(name='prank', description="P-Rank info")
    @discord.option(
        "name",
        str,
        description="Level number",
        autocomplete=lambda ctx: ctx.cog.prank_autocomplete_callback(ctx)
    )
    async def prank(self, ctx: discord.ApplicationContext, name: str):
        await ctx.defer()
        level_info = Datahelper.find_match(self.ukranks, name)
        if not level_info:
            embed = EmbedBuilder.error_embed("Invalid level number.")
            return
        embed = self.create_prank_embed(level_info)
        await ctx.respond(embed=embed)
    @ultrakill.command(name='weapon', description="Weapon info")
    @discord.option(
        "name",
        str,
        description="Weapon name",
        autocomplete=lambda ctx: ctx.cog.weapon_autocomplete_callback(ctx)
    )
    async def weapon(self, ctx: discord.ApplicationContext, name: str):
        await ctx.defer()
        weapon_info = Datahelper.find_match(self.ukweapons, name)
        if not weapon_info:
            embed = EmbedBuilder.error_embed("Invalid weapon name.")
            return
        embed = EmbedBuilder.create_weapon_embed(weapon_info)
        await ctx.respond(embed=embed)
    
    @ultrakill.command(name='weaponlist', description="List all weapons")
    async def weaponlist(self, ctx: discord.ApplicationContext):
        revolvers = sorted([weapon["name"] for weapon in self.ukweapons.values() if weapon["type"].lower() == "revolver"])
        shotguns = sorted([weapon["name"] for weapon in self.ukweapons.values() if weapon["type"].lower() == "shotgun"])
        nailguns = sorted([weapon["name"] for weapon in self.ukweapons.values() if weapon["type"].lower() == "nailgun"])
        railcannons = sorted([weapon["name"] for weapon in self.ukweapons.values() if weapon["type"].lower() == "railcannon"])
        rocket_launchers = sorted([weapon["name"] for weapon in self.ukweapons.values() if weapon["type"].lower() == "rocket launcher"])
        arm = sorted([weapon["name"] for weapon in self.ukweapons.values() if weapon["type"].lower() == "arm"])
        embed = discord.Embed(
            title="Ultrakill Weapons",
            description="List of all weapons in Ultrakill, use `/ultrakill weapon <name>` for more info.",
            color=0x8B0000
        )
        embed.add_field(name="Revolvers", value=", ".join(revolvers) if revolvers else "None", inline=False)
        embed.add_field(name="Shotguns", value=", ".join(shotguns) if shotguns else "None", inline=False)
        embed.add_field(name="Nailguns", value=", ".join(nailguns) if nailguns else "None", inline=False)
        embed.add_field(name="Railcannons", value=", ".join(railcannons) if railcannons else "None", inline=False)
        embed.add_field(name="Rocket Launchers", value=", ".join(rocket_launchers) if rocket_launchers else "None", inline=False)
        embed.add_field(name="Arms", value=", ".join(arm) if arm else "None", inline=False)
        await ctx.respond(embed=embed)
    
    @ultrakill.command(name='news', description="Latest Ultrakill news")
    async def news(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        now = datetime.now()
        cache_data = self._news_cache.get("data")
        cache_time = self._news_cache.get("timestamp")

        if cache_data and cache_time and (now - cache_time).total_seconds() < config.CACHE_DURATION:
            embed = self._build_news_embed(cache_data)
            await ctx.followup.send(embed=embed)
            return

        try:
            feed = feedparser.parse(config.UK_STEAM_RSS)
            if not feed.entries:
                await ctx.followup.send("❌ Could not fetch Ultrakill news.", ephemeral=True)
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
            logger.error(f"Error fetching Ultrakill news: {e}")
            await ctx.followup.send("❌ Error fetching news. Please try again later.", ephemeral=True)
    
    #embed +  autocomplete stuff
    @staticmethod
    def create_prank_embed(level_info: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"Level: {level_info['name']}",
            description=level_info.get("wiki", ""),
            color=0x8B0000
        )
        embed.set_image(url="https://ultrakill.wiki.gg/images/thumb/4/41/ULTRAKILL_Poster.webp/1024px-ULTRAKILL_Poster.webp.png?517c07")

        embed.add_field(name="Kills", value=f"Kills: {level_info.get('kills', '—')}", inline=True)
        embed.add_field(name="Time", value="\n".join(level_info.get('time')), inline=False)
        embed.add_field(name="Style", value="\n".join(level_info.get('style')), inline=False)
        return embed
    def prank_autocomplete_callback(self, ctx: discord.AutocompleteContext):
        user_input = ctx.value.lower()
        results = []

        for level_info in self.puklevels.values():
            name = level_info.get("name","")
            all_terms = [name] 
            for term in all_terms:
                if user_input in term.lower():
                    results.append(term)
                    break

        return results[:25]
    
    @staticmethod
    def create_weapon_embed(weapon_info: dict) -> discord.Embed:
        embed = discord.Embed(
            title=weapon_info.get("name", "Unknown Weapon"),
            description=weapon_info.get("description", "No description available."),
            color=0x8B0000
        )
        embed.set_image(url=weapon_info.get("image", "https://example.com/default_image.png"))
        
        embed.add_field(name="Type", value=weapon_info.get("type", "Unknown"), inline=True)
        embed.add_field(name="Wiki Link", value=weapon_info.get("wiki_link", "Unknown"), inline=True)
        embed.add_field(name="Tech", value=weapon_info.get("tech", "Unknown"), inline=True)
        
        aliases = weapon_info.get("aliases", [])
        if aliases:
            embed.add_field(name="Aliases", value=", ".join(aliases), inline=False)

        return embed
    def weapon_autocomplete_callback(self, ctx: discord.AutocompleteContext):
        user_input = ctx.value.lower()
        results = []

        for weapon_info in self.ukweapons:
            name = weapon_info.get("name", "")
            all_terms = [name] + weapon_info.get("aliases", [])
            for term in all_terms:
                if user_input in term.lower():
                    results.append(term)
                    break

        return results[:25]

    @staticmethod
    def _build_news_embed(news_data):
        embed = discord.Embed(title="📰 Ultrakill News", color=0x8B0000)
        for entry in news_data:
            embed.add_field(
                name=f"{entry['title']} ({entry['published']})",
                value=f"{entry['summary']}\n[Read more]({entry['link']})",
                inline=False
            )
        embed.set_footer(text="Source: Steam")
        return embed

def setup(bot: commands.Bot):
    bot.add_cog(Ultracog(bot))
    logger.info("Ultrakill cog loaded.")