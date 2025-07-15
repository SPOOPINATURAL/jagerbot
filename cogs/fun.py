import html
import logging
import random
from typing import Dict, Optional

import aiohttp
import discord
from discord.ext import commands
from config import SCORES_FILE
from utils.embed_builder import EmbedBuilder
from utils.helpers import FileHelper
from views.rps import RPSView
from views.trivia import TriviaView

logger = logging.getLogger(__name__)

class TriviaManager:
    def __init__(self, scores_file: str):
        self.scores_file = scores_file
        self.scores: Dict[str, int] = {}
        self.load_scores()

    def load_scores(self) -> None:
        self.scores = FileHelper.load_json_file(self.scores_file) or {}
        logger.info(f"Loaded {len(self.scores)} trivia scores")

    def save_scores(self) -> None:
        FileHelper.save_json_file(self.scores_file, self.scores)
        logger.info(f"Saved {len(self.scores)} trivia scores")

    def update_score(self, user_id: int, is_correct: bool) -> None:
        uid = str(user_id)
        self.scores[uid] = self.scores.get(uid, 0) + int(is_correct)
        self.save_scores()

    def get_score(self, user_id: int) -> int:
        return self.scores.get(str(user_id), 0)


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trivia_manager = TriviaManager(SCORES_FILE)
        self.session = None
        super().__init__()

    @discord.slash_command(name='quote', description="Get a random Jäger quote")
    async def quote(self, ctx: discord.ApplicationContext):
        selected_quotes = random.choice(self.bot.config.quotes)
        await ctx.respond(selected_quotes)

    @discord.slash_command(name='image', description="Get a random image")
    async def image(self, ctx: discord.ApplicationContext):
        images_url = random.choice(self.bot.config.image_urls)
        await ctx.respond(images_url)

    @discord.slash_command(name='clancy', description="Obtain a random Clancy image")
    async def clancy(self, ctx: discord.ApplicationContext):
        clancy_image = random.choice(self.bot.config.clancy_images)
        await ctx.respond(clancy_image)

    @discord.slash_command(name='longo', description="longo")
    async def longo(self, ctx: discord.ApplicationContext):
        image_url = "https://i.imgur.com/J1P7g5f.jpeg"
        embed = discord.Embed(title="longo")
        embed.set_image(url=image_url)
        await ctx.respond(embed=embed)

    @discord.slash_command(name="8ball", description="Ask the magic 8ball a question")
    async def eight_ball(
        self,
        ctx: discord.ApplicationContext,
        question: discord.Option(str, "Your yes/no question")
    ):
        responses = [
            "🎱 Yes, definitely.",
            "🎱 It is certain.",
            "🎱 Without a doubt.",
            "🎱 Most likely.",
            "🎱 Outlook good.",
            "🎱 Signs point to yes.",
            "🎱 Ask again later.",
            "🎱 Cannot predict now.",
            "🎱 Don't count on it.",
            "🎱 My reply is no.",
            "🎱 Very doubtful.",
            "🎱 Absolutely not.",
        ]
        response = random.choice(responses)
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            description=f"**Question:** {question}\n**Answer:** {response}",
            color=0x8B0000
        )
        await ctx.respond(embed=embed)

    @discord.slash_command(name="xkcd", description="Get a random XKCD comic")
    async def random_xkcd(self, ctx: discord.ApplicationContext):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://c.xkcd.com/random/comic/", allow_redirects=False) as resp:
                if resp.status != 302:
                    await ctx.respond("Couldn't fetch a random XKCD comic.", ephemeral=True)
                    return
                location = resp.headers.get("Location")
                if not location:
                    await ctx.respond("Couldn't get the comic URL.", ephemeral=True)
                    return

            json_url = location + "info.0.json"
            async with session.get(json_url) as resp:
                if resp.status != 200:
                    await ctx.respond("Couldn't fetch XKCD comic info.", ephemeral=True)
                    return
                comic = await resp.json()

        embed = discord.Embed(
            title=comic["title"],
            url=f"https://xkcd.com/{comic['num']}",
            color=0x8B0000,
        )
        embed.set_image(url=comic["img"])
        embed.set_footer(text=f"Comic #{comic['num']}")
        await ctx.respond(embed=embed)

    @discord.slash_command(name="d20", description="Roll d20")
    async def roll_d20(self, ctx: discord.ApplicationContext):
        result = random.randint(1, 20)
        embed = discord.Embed(
            title="🎲 D20 Roll",
            description=f"You rolled a **{result}**!",
            color=0x8B0000
        )
        await ctx.respond(embed=embed)

    @discord.slash_command(name="rps", description="Play Rock, Paper, Scissors")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def rps_command(self, ctx: discord.ApplicationContext):
        try:
            view = RPSView(player_id=ctx.user.id)
            await ctx.respond(
                "🎮 Choose your move:",
                view=view
            )
            view.message = await ctx.interaction.original_response()

        except Exception as e:
            logger.error(f"Error starting RPS game: {e}", exc_info=True)
            await ctx.respond(
                "❌ Failed to start the game. Please try again.",
                ephemeral=True
            )

    @discord.slash_command(name='trivia', description="Get a trivia question, multiple choice answers")
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def trivia(self, ctx: discord.ApplicationContext):
        try:
            question_data = await self._fetch_trivia_question()
            if not question_data:
                await ctx.respond(
                    "❌ Failed to fetch trivia question. Try again later.",
                    ephemeral=True
                )
                return

            question, correct, answers = self._prepare_question(question_data)
            correct_letter = self._get_correct_letter(answers, correct)

            embed = self._create_trivia_embed(question, answers)
            view = TriviaView(
                author_id=ctx.user.id,
                correct_letter=correct_letter,
                correct_answer=correct,
                answer_callback=self.trivia_manager.update_score
            )

            await ctx.respond(embed=embed, view=view)
            view.message = await ctx.interaction.original_response()
            await view.wait()

        except Exception as e:
            logger.error(f"Error in trivia command: {e}")
            await ctx.respond(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )

    async def _fetch_trivia_question(self) -> Optional[dict]:
        try:
            async with self.session.get(
                    "https://opentdb.com/api.php?amount=1&type=multiple"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["results"][0]
        except Exception as e:
            logger.error(f"Failed to fetch trivia: {e}")
        return None

    @staticmethod
    def _prepare_question(data: dict) -> tuple[str, str, dict]:
        question = html.unescape(data["question"])
        correct = html.unescape(data["correct_answer"])
        incorrect = [html.unescape(ans) for ans in data["incorrect_answers"]]

        all_answers = incorrect + [correct]
        random.shuffle(all_answers)

        answers = dict(zip(['A', 'B', 'C', 'D'], all_answers))
        return question, correct, answers

    @staticmethod
    def _get_correct_letter(answers: dict, correct: str) -> str:
        return next(k for k, v in answers.items() if v == correct)

    @staticmethod
    def _create_trivia_embed(question: str, answers: dict) -> discord.Embed:
        embed = EmbedBuilder.info(
            title="🧠 Trivia",
            description=question
        )
        for letter, answer in answers.items():
            embed.add_field(name=letter, value=answer, inline=False)
        embed.set_footer(text="Click the button that matches your answer.")
        return embed

    @commands.slash_command(name='score', description="Get your trivia score")
    async def score(self, ctx: discord.ApplicationContext):
        score = self.trivia_manager.get_score(ctx.user.id)
        await ctx.respond(
            f"🏆 {ctx.user.display_name}, your trivia score is: **{score}**"
        )

def setup(bot: commands.Bot):
    bot.add_cog(Fun(bot))
