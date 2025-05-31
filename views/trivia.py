import discord
from discord.ui import View, Button
from discord import Interaction
from typing import Callable, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class TriviaView(View):
    def __init__(
        self,
        author_id: int,
        correct_letter: str,
        correct_answer: str,
        answer_callback: Callable[[int, bool], None],
        timeout: float = 15.0
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.correct_letter = correct_letter
        self.correct_answer = correct_answer
        self.answer_callback = answer_callback
        self.answered: bool = False
        self.message: Optional[discord.Message] = None
        
        self._add_answer_buttons()

    def _add_answer_buttons(self) -> None:
        for letter in ["A", "B", "C", "D"]:
            self.add_item(TriviaButton(letter, self))

    def _disable_all_buttons(self) -> None:
        for child in self.children:
            child.disabled = True

    def _get_response_text(self, is_correct: bool) -> str:
        return (
            "✅ Correct! 🎉" if is_correct 
            else f"❌ Wrong! The correct answer was **{self.correct_answer}**."
        )

    async def on_timeout(self) -> None:
        try:
            for child in self.children:
                child.disabled = True
            if self.message:
                await self.message.edit(
                    content="⌛ Time's up! No answer was submitted.", 
                    view=self
                )
        except discord.NotFound:
            logger.warning("Message not found during timeout handling")
        except Exception as e:
            logger.error(f"Error in trivia timeout: {e}")

    async def process_answer(self, interaction: Interaction, letter: str) -> None:
        if self.answered:
            await interaction.response.send_message(
                "❌ You already answered.", 
                ephemeral=True
            )
            return

        try:
            self.answered = True
            self._disable_all_buttons()

            is_correct = (letter == self.correct_letter)
            if self.answer_callback:
                self.answer_callback(interaction.user.id, is_correct)

            response = self._get_response_text(is_correct)
            await interaction.response.send_message(response)

        except Exception as e:
            logger.error(f"Error processing trivia answer: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your answer.",
                ephemeral=True
            )
        finally:
            self.stop()


class TriviaButton(Button):
    def __init__(self, letter: str, parent_view: TriviaView):
        super().__init__(
            label=letter, 
            style=discord.ButtonStyle.primary
        )
        self.letter = letter
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user.id != self.parent_view.author_id:
            await interaction.response.send_message(
                "❌ This is not your trivia question!", 
                ephemeral=True
            )
            return
            
        await self.parent_view.process_answer(interaction, self.letter)