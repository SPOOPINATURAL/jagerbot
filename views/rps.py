import logging
from typing import Optional
from enum import Enum

import discord
import random
from discord.ui import View, Button
from discord import ButtonStyle, Interaction

logger = logging.getLogger(__name__)

class RPSChoice(Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"

    @property
    def emoji(self) -> str:
        return {
            self.ROCK: "🪨",
            self.PAPER: "📄",
            self.SCISSORS: "✂️"
        }[self]

    def beats(self, other: 'RPSChoice') -> bool:
        return (
            (self == self.ROCK and other == self.SCISSORS) or
            (self == self.PAPER and other == self.ROCK) or
            (self == self.SCISSORS and other == self.PAPER)
        )

class RPSButton(Button):

    def __init__(self, choice: RPSChoice, view: 'RPSView'):
        super().__init__(
            label=f"{choice.emoji} {choice.name.title()}", 
            style=ButtonStyle.secondary,
            custom_id=f"rps_{choice.value}"
        )
        self.choice = choice
        self.rps_view = view

    async def callback(self, interaction: Interaction) -> None:
        try:
            await self.rps_view.handle_choice(interaction, self.choice)
        except Exception as e:
            logger.error(f"Error in RPS button callback: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ An error occurred processing your choice.",
                ephemeral=True
            )

class RPSView(View):

    def __init__(self, player_id: int):
        super().__init__(timeout=15.0)
        self.player_id = player_id
        self.message: Optional[discord.Message] = None
        self._add_buttons()

    def _add_buttons(self) -> None:
        for choice in RPSChoice:
            self.add_item(RPSButton(choice=choice, view=self))

    def _create_result_embed(
        self,
        user_choice: RPSChoice,
        bot_choice: RPSChoice,
        result: str
    ) -> discord.Embed:
        return discord.Embed(
            title="🎮 Rock Paper Scissors",
            description=(
                f"**You:** {user_choice.emoji} {user_choice.name.title()}\n"
                f"**Bot:** {bot_choice.emoji} {bot_choice.name.title()}\n\n"
                f"**{result}**"
            ),
            color=0x2F3136
        )

    async def on_timeout(self) -> None:
        try:
            for item in self.children:
                item.disabled = True
            if self.message:
                await self.message.edit(
                    content="⏰ Game timed out!",
                    view=self
                )
        except Exception as e:
            logger.error(f"Error handling RPS timeout: {e}")

    async def handle_choice(
        self,
        interaction: Interaction,
        user_choice: RPSChoice
    ) -> None:
        try:
            if interaction.user.id != self.player_id:
                await interaction.response.send_message(
                    "❌ This isn't your game!",
                    ephemeral=True
                )
                return

            bot_choice = RPSChoice(random.choice([c.value for c in RPSChoice]))
            
            if user_choice == bot_choice:
                result = "It's a draw! 🤝"
            elif user_choice.beats(bot_choice):
                result = "You win! 🎉"
            else:
                result = "You lose! 😢"

            embed = self._create_result_embed(user_choice, bot_choice, result)
            await interaction.response.edit_message(embed=embed, view=None)

        except Exception as e:
            logger.error(f"Error handling RPS choice: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ An error occurred during the game.",
                ephemeral=True
            )