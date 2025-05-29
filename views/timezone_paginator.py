import discord
from config import TIMEZONES


#timezone list
class TimezonePaginator(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.page = 0
        self.items_per_page = 10
        self.max_page = len(TIMEZONES) // self.items_per_page
        self.message = None

    def get_page_content(self):
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        page_items = TIMEZONES[start:end]
        desc = "\n".join(page_items)
        return desc

    async def update_message(self):
        embed = discord.Embed(
            title=f"Timezones (Page {self.page + 1}/{self.max_page + 1})",
            description=self.get_page_content(),
            color=0x3498db,
        )
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page == 0:
            self.page = self.max_page
        else:
            self.page -= 1
            await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page == self.max_page:
            self.page = 0
        else:
            self.page += 1
            await self.update_message()
        await interaction.response.defer()