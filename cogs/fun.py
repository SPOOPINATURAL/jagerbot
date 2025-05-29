import random
import os
import discord
from discord.ext import commands
from discord import app_commands
import json
import html
import aiohttp
from config import SCORES_FILE
from utils.helpers import check_cooldown, start_cooldown
from views.trivia import TriviaView

user_scores = {}
def load_scores():
    if not os.path.exists(SCORES_FILE):
        return {}
    with open(SCORES_FILE, "r") as f:
        return json.load(f)

def save_scores(scores):
    os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
    with open(SCORES_FILE, "w") as f:
        json.dump(scores, f, indent=4)

async def handle_trivia_answer(user_id: int, is_correct: bool):
    user_scores[user_id] = user_scores.get(user_id, 0) + int(is_correct)
    save_scores(user_scores)

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='hello', description="Hello!")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Hallo {interaction.user.mention} :)")

    @app_commands.command(name='quote', description="Get a random Jäger quote")
    async def quote(self, interaction: discord.Interaction):
        selected_quotes = random.choice(self.bot.config.quotes)
        await interaction.response.send_message(selected_quotes)

    @app_commands.command(name='image', description="Get a random image")
    async def image(self, interaction: discord.Interaction):
        images_url = random.choice(self.bot.config.image_urls)
        await interaction.response.send_message(images_url)

    @app_commands.command(name='clancy', description="Obtain a random Clancy image")
    async def clancy(self, interaction: discord.Interaction):
        clancy_image = random.choice(self.bot.config.clancy_images)
        await interaction.response.send_message(clancy_image)

    @app_commands.command(name='longo', description="longo")
    async def longo(self, interaction: discord.Interaction):
        image_url = "https://i.imgur.com/J1P7g5f.jpeg"
        embed = discord.Embed(title="longo")
        embed.set_image(url=image_url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="8ball", description="Ask the magic 8ball a question")
    @app_commands.describe(question="Your yes/no question")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="xkcd", description="Get a random XKCD comic")
    async def random_xkcd(self, interaction: discord.Interaction):
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("https://c.xkcd.com/random/comic/", allow_redirects=False) as resp:
                if resp.status != 302:
                    await interaction.response.send_message("Couldn't fetch a random XKCD comic.", ephemeral=True)
                    return
                location = resp.headers.get("Location")
                if not location:
                    await interaction.response.send_message("Couldn't get the comic URL.", ephemeral=True)
                    return

            json_url = location + "info.0.json"
            async with session.get(json_url) as resp:
                if resp.status != 200:
                    await interaction.response.send_message("Couldn't fetch XKCD comic info.", ephemeral=True)
                    return
                comic = await resp.json()

        embed = discord.Embed(
            title=comic["title"],
            url=f"https://xkcd.com/{comic['num']}",
            color=0x8B0000,
        )
        embed.set_image(url=comic["img"])
        embed.set_footer(text=f"Comic #{comic['num']}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="d20", description="Roll d20")
    async def roll_d20(self, interaction: discord.Interaction):
        result = random.randint(1, 20)
        embed = discord.Embed(
            title="🎲 D20 Roll",
            description=f"You rolled a **{result}**!",
            color=0x8B0000
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rps", description="Play Rock, Paper, Scissors")
    async def rps_command(self, interaction: discord.Interaction):
        from views.rps import RPSView
        view = RPSView(player_id=interaction.user.id)
        await interaction.response.send_message("Choose your move:", view=view)

    @app_commands.command(name='trivia', description="Get a trivia question, multiple choice answers")
    async def trivia(self, interaction: discord.Interaction):
        on_cooldown, retry_after = check_cooldown(interaction.user.id, "trivia")
        if on_cooldown:
            await interaction.response.send_message(
                f"Please wait {retry_after} seconds before using this command again.", ephemeral=True)
            return

        url = "https://opentdb.com/api.php?amount=1&type=multiple"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        question_data = data["results"][0]
        question = html.unescape(question_data["question"])
        correct = html.unescape(question_data["correct_answer"])
        incorrect = [html.unescape(ans) for ans in question_data["incorrect_answers"]]
        all_answers = incorrect + [correct]
        random.shuffle(all_answers)

        letters = ['A', 'B', 'C', 'D']
        answer_map = dict(zip(letters, all_answers))
        correct_letter = next(k for k, v in answer_map.items() if v == correct)

        embed = discord.Embed(title="🧠 Trivia", description=question, color=0x8B0000)
        for letter, answer in answer_map.items():
            embed.add_field(name=letter, value=answer, inline=False)
        embed.set_footer(text="Click the button that matches your answer.")

        view = TriviaView(
            author_id=interaction.user.id,
            correct_letter=correct_letter,
            correct_answer=correct,
            answer_callback=handle_trivia_answer
        )
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
        await view.wait()

    @app_commands.command(name='score', description="Get your trivia score")
    async def score(self, interaction: discord.Interaction):
        uid = interaction.user.id
        score = user_scores.get(uid, 0)
        await interaction.response.send_message(
            f"🏆 {interaction.user.display_name}, your trivia score is: **{score}**"
        )


async def setup(bot):
    bot.config = __import__("config")
    await bot.add_cog(Fun(bot))
