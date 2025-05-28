
import discord
from discord.ui import View, Button
import random

class RPSView(View):
    def __init__(self, player_id: int):
        super().__init__(timeout=15)
        self.player_id = player_id

        self.options = {
            "rock": "🪨 Rock",
            "paper": "📄 Paper",
            "scissors": "✂️ Scissors"
        }

        for option, label in self.options.items():
            self.add_item(RPSButton(label=label, choice=option, view=self))

    async def handle_choice(self, interaction: discord.Interaction, user_choice: str):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ You're not the original player!", ephemeral=True)
            return

        bot_choice = random.choice(list(self.options.keys()))

        if user_choice == bot_choice:
            result = "It's a draw!"
        elif (
            (user_choice == "rock" and bot_choice == "scissors") or
            (user_choice == "paper" and bot_choice == "rock") or
            (user_choice == "scissors" and bot_choice == "paper")
        ):
            result = "You win!"
        else:
            result = "You lose!"

        embed = discord.Embed(
            title="🪨📄✂️ Rock Paper Scissors",
            description=(
                f"**You:** {user_choice.capitalize()}\n"
                f"**Bot:** {bot_choice.capitalize()}\n\n**{result}**"
            ),
            color=0x8B0000
        )

        await interaction.response.edit_message(embed=embed, view=None)


class RPSButton(Button):
    def __init__(self, label: str, choice: str, view: RPSView):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.choice = choice
        self.custom_view = view

    async def callback(self, interaction: discord.Interaction):
        await self.custom_view.handle_choice(interaction, self.choice)