import discord
import config
from discord import ButtonStyle, Interaction, ui

# info
class InfoPages(ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.pages: list[discord.Embed] = []
        self.current: int = 0
        self.guild_id = guild_id
        self.message: discord.Message | None = None
        self.create_pages()

    def create_pages(self):
        self.pages.clear()
        # r6
        embed1 = discord.Embed(
            title="JägerBot Commands List (Page 1/6)",
            description="**R6 Siege Commands**",
            color=0x8B0000
        )
        embed1.add_field(name="/r6 stats (platform) (username)", value="Fetch R6 Siege stats from a user", inline=False)
        embed1.add_field(name="/quote", value="Get a random Jäger quote", inline=False)
        embed1.add_field(name="/r6 op (operator name)", value="Overview of a Siege Operator.", inline=False)
        embed1.add_field(name="/r6 oplist", value="List of all playable operators.", inline=False)
        embed1.add_field(name="/r6 oprandom (attack / defense)", value="Gives you a random operator.", inline=False)
        embed1.add_field(name="/r6 map (map name)", value="Get a floorplan of a ranked map.", inline=False)
        embed1.add_field(name="/r6 maplist", value="List of ranked maps", inline=False)
        embed1.add_field(name="/r6 news", value="Latest R6 Siege news", inline=False)
        self.pages.append(embed1)

        # mc
        embed2 = discord.Embed(
            title="JägerBot Commands List (Page 2/6)",
            description="**Minecraft Commands**",
            color=0x8B0000
        )
        embed2.add_field(name="/mc wiki (search term)", value="Search Minecraft Wiki.", inline=False)
        embed2.add_field(name="/mc recipe (item)", value="Look up a crafting recipe.", inline=False)
        embed2.add_field(name="/mc advancement (name)", value="Info on advancements.", inline=False)
        embed2.add_field(name="/mc enchant (name)", value="Minecraft enchantment info.", inline=False)
        embed2.add_field(name="/mc biome (name)", value="Info about biomes.", inline=False)
        embed2.add_field(name="/mc structure (name)", value="Info about structures.", inline=False)
        embed2.add_field(name="/mc player (username)", value="Fetch player UUID and skin.", inline=False)
        if self.guild_id in config.ALLOWED_GUILD_IDS:
            embed2.add_field(name="/mc serverstatus", value="Check VDSMP server status.", inline=False)
        self.pages.append(embed2)

        # fun
        embed3 = discord.Embed(
            title="JägerBot Commands List (Page 3/6)",
            description="**Fun / Stupid Stuff**",
            color=0x8B0000
        )
        embed3.add_field(name="/image", value="Get a random image.", inline=False)
        embed3.add_field(name="/longo", value="longo", inline=False)
        embed3.add_field(name="/clancy", value="Obtain a random Clancy image.", inline=False)
        embed3.add_field(name="/trivia", value="Play some trivia.", inline=False)
        embed3.add_field(name="/score", value="Your trivia score.", inline=False)
        embed3.add_field(name="/xkcd", value="Get a random xkcd comic.", inline=False)
        embed3.add_field(name="/8ball (question)", value="8ball makes a decision for you (ex. '/8ball should i take a walk').", inline=False)
        embed3.add_field(name="/d20", value="Roll a d20.", inline=False)
        embed3.add_field(name="/rps", value="Play Rock, Paper, Scissors.", inline=False)
        embed3.add_field(name="/plane", value="Gives a random WW1 plane with specs.", inline=False)
        self.pages.append(embed3)
        # util
        embed4 = discord.Embed(
            title="JägerBot Commands List (Page 4/6)",
            description="**Utility Commands**",
            color=0x8B0000
        )
        embed4.add_field(name="/weather (city)", value="Tells you the current weather in a city (ex.'/weather seattle').", inline=False)
        embed4.add_field(name="/tzconvert (time) (timezone a) to (timezone b)", value="Converts one timezone to another (ex. '/tzconvert now UTC to IST').", inline=False)
        embed4.add_field(name="/timezones", value="Lists every timezone.", inline=False)
        embed4.add_field(name="/date (timezone)", value="Tells you the day and calendar date. Timezone optional.", inline=False)
        embed4.add_field(name="/currency (amount) (currency a) (currency b)", value="Converts one currency to another (ex. '/currency 100 USD EUR').", inline=False)
        embed4.add_field(name="/alert (activity) (time)", value="Creates an alert, bot will DM you when it’s time. Use 'recurring' for repeated alerts (ex.'/alert Event in 10minutes' or '/alert Reminder 2025-06-01 18:00 PST recurring 24h').", inline=False)
        embed4.add_field(name="/listalerts", value="Lists all your alerts.", inline=False)
        embed4.add_field(name="/cancelalerts", value="Cancels all your alerts.", inline=False)
        embed4.add_field(name="/credits", value="See who made / helped with the bot.", inline=False)
        self.pages.append(embed4)

        # wf
        embed5 = discord.Embed(
            title="JägerBot Commands List (Page 5/6)",
            description="**Warframe Commands**",
            color=0x8B0000
        )
        embed5.add_field(name="/wf baro",  value="Tells you when Baro will arrive and where he is.", inline=False)
        embed5.add_field(name="/wf news", value="Latest Warframe news.", inline=False)
        embed5.add_field(name="/wf nightwave", value="Warframe Nightwave quests.", inline=False)
        embed5.add_field(name="/wf price", value="warframe.market item price.", inline=False)
        embed5.add_field(name="/wf streams", value="Upcoming and current Warframe streams/drops on Twitch", inline=False)
        self.pages.append(embed5)
        
        embed6 = discord.Embed(
            title="JägerBot Commands List (Page 6/6)",
            description="**Ultrakill Commands**",
            color=0x8B0000
        )
        embed6.add_field(name="/ultrakill prank (level number)",  value="Tells you the requirements to P-Rank a level.", inline=False)
        embed6.add_field(name="/ultrakill weapon (weapon name)", value="Tells you weapon stats.", inline=False)
        embed6.add_field(name="/ultrakill weaponlist", value="List of all current Ultrakill weapons (special variants not included)", inline=False)
        embed6.add_field(name="/ultrakill news", value="Ultrakill news", inline=False)
        self.pages.append(embed6)

    @ui.button(emoji="⬅️", style = ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.current = (self.current - 1) % len(self.pages)
        await self.update_message(interaction)

    @ui.button(emoji="➡️", style = ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.current = (self.current + 1) % len(self.pages)
        await self.update_message(interaction)
    async def update_message(self, interaction: Interaction):
        if self.message:
            await self.message.edit(embed=self.pages[self.current], view=self)
        else:
            await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass