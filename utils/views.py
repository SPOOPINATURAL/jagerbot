from discord.ui import View, Button
from discord import ButtonStyle, Interaction, Embed
import discord

class PaginationView(View):
    def __init__(self, page_count: int, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.current_page = 0
        self.total_pages = page_count
        self.message = discord.Message | None = None

    def create_embed(self, index: int) -> Embed:
        raise NotImplementedError

    @discord.ui.button(label="⬅️", style=ButtonStyle.secondary)
    async def previous(self, interaction: Interaction, _: Button):
        await self.change_page(interaction, -1)

    @discord.ui.button(label="➡️", style=ButtonStyle.secondary)
    async def next(self, interaction: Interaction, _: Button):
        await self.change_page(interaction, 1)

    async def change_page(self, interaction: Interaction, delta: int):
        self.current_page = (self.current_page + delta) % self.total_pages
        embed = self.create_embed(self.current_page),
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass