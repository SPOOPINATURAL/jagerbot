import discord
import config
from discord.ext import bridge, commands
from utils.embed_builder import EmbedBuilder
from utils.helpers import FileHelper, Datahelper

class Ultracog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.ukranks = bot.ukranks
        self.ukweapons = bot.ukweapons
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
