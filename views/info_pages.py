import discord
import config
from discord import ButtonStyle

# info
class InfoPages(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.pages = []
        self.current = 0
        self.guild_id = guild_id
        self.message = None
        self.create_pages()

    def create_pages(self):
        # Page 1: R6 Siege
        embed1 = discord.Embed(
            title="JägerBot Commands List (Page 1/5)",
            description="**R6 Siege Commands**",
            color=0x8B0000
        )
        embed1.add_field(name="/r6stats (platform) (username)", value="Fetch R6 Siege stats from a user", inline=False)
        embed1.add_field(name="/quote", value="Get a random Jäger quote", inline=False)
        embed1.add_field(name="/op (operator name)", value="Overview of a Siege Operator.", inline=False)
        embed1.add_field(name="/oplist", value="List of all playable operators.", inline=False)
        embed1.add_field(name="/oprandom (attack / defense)", value="Gives you a random operator.", inline=False)
        embed1.add_field(name="/map (map name)", value="Get a floorplan of a ranked map.", inline=False)
        embed1.add_field(name="/maplist", value="List of ranked maps", inline=False)
        self.pages.append(embed1)

        # Page 2: Minecraft
        embed2 = discord.Embed(
            title="JägerBot Commands List (Page 2/5)",
            description="**Minecraft Commands**",
            color=0x8B0000
        )
        embed2.add_field(name="/mcwiki (search term)", value="Search Minecraft Wiki.", inline=False)
        embed2.add_field(name="/mcrecipe (item)", value="Look up a crafting recipe.", inline=False)
        embed2.add_field(name="/mcadvancement (name)", value="Info on advancements.", inline=False)
        embed2.add_field(name="/mcenchant (name)", value="Minecraft enchantment info.", inline=False)
        embed2.add_field(name="/mcbiome (name)", value="Info about biomes.", inline=False)
        embed2.add_field(name="/mcstructure (name)", value="Info about structures.", inline=False)
        embed2.add_field(name="/mcplayer (username)", value="Fetch player UUID and skin.", inline=False)
        if self.guild_id in config.ALLOWED_GUILD_IDS:
            embed2.add_field(name="/mcserverstatus", value="Check VDSMP server status.", inline=False)
        self.pages.append(embed2)

        # Page 3: Fun
        embed3 = discord.Embed(
            title="JägerBot Commands List (Page 3/5)",
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
        # Page 4: Utility
        embed4 = discord.Embed(
            title="JägerBot Commands List (Page 4/5)",
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

        # Page 5: Warframe
        embed5 = discord.Embed(
            title="JägerBot Commands List (Page 5/5)",
            description="**Warframe Commands**",
            color=0x8B0000
        )
        embed5.add_field(name="/wfbaro",  value="Tells you when Baro will arrive and where he is.", inline=False)
        embed5.add_field(name="/wfnews", value="Latest Warframe news.", inline=False)
        embed5.add_field(name="/wfnightwave", value="Warframe Nightwave quests.", inline=False)
        embed5.add_field(name="/wfprice", value="warframe.market item price.", inline=False)
        self.pages.append(embed5)

    async def update_message(self, interaction):
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="⬅️", style = ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.current = (self.current - 1) % len(self.pages)
        await self.update_message(interaction)

    @discord.ui.button(label="➡️", style = ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.current = (self.current + 1) % len(self.pages)
        await self.update_message(interaction)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass