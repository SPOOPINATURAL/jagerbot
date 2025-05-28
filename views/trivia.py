import discord
from discord.ui import View, Button
from discord import Interaction
from typing import Callable, Dict

class TriviaView(discord.ui.View):
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
        self.answered = False
        self.message = None

        for letter in ["A", "B", "C", "D"]:
            self.add_item(TriviaButton(letter, self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⌛ Time's up! No answer was submitted.", view=self)
            except discord.NotFound:
                pass

    async def process_answer(self, interaction: Interaction, letter: str):
        if self.answered:
            await interaction.response.send_message("❌ You already answered.", ephemeral=True)
            return

        self.answered = True
        for child in self.children:
            child.disabled = True

        is_correct = (letter == self.correct_letter)
        await self.answer_callback(interaction.user.id, is_correct)

        response_text = (
            f"✅ Correct! 🎉" if is_correct else
            f"❌ Wrong! The correct answer was **{self.correct_answer}**."
        )

        try:
            await interaction.edit_original_response(content=response_text, view=self)
        except discord.NotFound:
            pass

        self.stop()


class TriviaButton(Button):
    def __init__(self, letter: str, parent_view: TriviaView):
        super().__init__(label=letter, style=discord.ButtonStyle.primary)
        self.letter = letter
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.parent_view.author_id:
            await interaction.response.send_message("❌ This is not your trivia question!", ephemeral=True)
            return
        await self.parent_view.process_answer(interaction, self.letter)