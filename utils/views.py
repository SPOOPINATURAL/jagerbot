from discord.ui import View, Button
from discord import ButtonStyle, Interaction
import discord

class PaginationView(View):
    def __init__(self, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.current_page = 0
        self.message = None

    def create_embed(self, index: int) -> discord.Embed:
        raise NotImplementedError

    @discord.ui.button(label="⬅️", style=ButtonStyle.secondary)
    async def previous(self, interaction: Interaction, _: Button):
        await self.change_page(interaction, -1)

    @discord.ui.button(label="➡️", style=ButtonStyle.secondary)
    async def next(self, interaction: Interaction, _: Button):
        await self.change_page(interaction, 1)

    async def change_page(self, interaction: Interaction, delta: int):
        self.current_page = (self.current_page + delta) % len(self.floors)
        await interaction.response.edit_message(
            embed=self.create_embed(self.current_page),
            view=self
        )