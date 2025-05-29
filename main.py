#standard stuff
import os, re, random, logging, warnings, tracemalloc
from datetime import datetime
from types import SimpleNamespace

#3rd party
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import dateparser
import pytz
from pytz.exceptions import UnknownTimeZoneError
from dateutil.tz import UTC
from dateparser.conf import settings as dp_settings
import html

#local
import webserver
import config
from config import (
    DISCORD_TOKEN,
    WEATHER_API_KEY,
    TRACKER_API_KEY,
)
from views.trivia import TriviaView
from views.rps import RPSView
import utils.helpers as helpers
from views.info_pages import InfoPages

#files n shi
print(f"[DEBUG] API Key: {TRACKER_API_KEY}")
user_scores = {}
tracemalloc.start()
warnings.simplefilter('always', RuntimeWarning)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
custom_settings = SimpleNamespace(**dp_settings.__dict__)
custom_settings.RETURN_AS_TIMEZONE_AWARE = False
timeout = aiohttp.ClientTimeout(total=5)
sessions = {}

alerts = helpers.load_alerts()
helpers.save_alerts(alerts)

all_data = load_all_json_from_folder()

r6.operators.update(all_data.get("operators", {}))
r6.maps.update(all_data.get("maps", {}))
planes = all_data.get("planes",[])
alerts = all_data.get("alerts",{})
user_scores = all_data.get("trivia_scores",{})

UTC = pytz.UTC
alert_checker = AlertChecker(bot, alerts, UTC, parse_time, save_alerts)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
user_scores = {}


#bot start events
class JagerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=">",
            intents=intents,
            help_command = None
        )
        self.user_scores = {}
        self.alerts = {}
        self.planes = []

    async def setup_hook(self):
        # cogs
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        await self.tree.sync()
        logger.info("✅ Synced slash commands")

    async def on_ready(self):
        logger.info("Bot is ready, loading alerts and scores...")
        self.load_alerts()
        self.load_scores()
        sessions.clear()
        cooldowns.clear()
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.watching, name="Everything")
        )
        logger.info("✅ Cleared caches")
        logger.info("Ready :)")

    def load_alerts(self):
        logger.info("Loaded alerts")

    def load_scores(self):
        logger.info("Loaded scores")
bot = JagerBot()
@bot.tree.command(name='hello', description="Hello!")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hallo {interaction.user.mention} :)")

#quote
@bot.tree.command(name='quote', description="Get a random Jäger quote")
async def quote(interaction: discord.Interaction):
    selected_quotes = random.choice(config.quotes)
    await interaction.response.send_message(selected_quotes)
#images
@bot.tree.command(name='image', description="Get a random image")
async def image(interaction: discord.Interaction):
    images_url = random.choice(config.image_urls)
    await interaction.response.send_message(images_url)
#clanc
@bot.tree.command(name='clancy', description="Obtain a random Clancy image")
async def clancy(interaction: discord.Interaction):
    clancy_image = random.choice(config.clancy_images)
    await interaction.response.send_message(clancy_image)
#longo
@bot.tree.command(name='longo', description="longo")
async def longo(interaction: discord.Interaction):
    image_url = "https://i.imgur.com/J1P7g5f.jpeg"
    embed = discord.Embed(title="longo")
    embed.set_image(url=image_url)
    await interaction.response.send_message(embed=embed)

#weather
@bot.tree.command(name='weather', description="Get the current weather in a city")
@app_commands.describe(city="Name of the city (e.g. London, Tokyo)")
async def weather(interaction: discord.Interaction, city: str):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                await interaction.response.send_message(f"❌ Could not find weather for `{city}`.")
                return

            data = await resp.json()

            name = data["name"]
            temp_c = data["main"]["temp"]
            temp_f = round((temp_c * 9 / 5) + 32, 1)
            desc = data["weather"][0]["description"].title()
            emoji = get_weather_emoji(desc)
            humidity = data["main"]["humidity"]
            wind_mps = data["wind"]["speed"]
            wind_mph = round(wind_mps * 2.23694, 1)

            embed = discord.Embed(
                title=f"{emoji} Weather in {name}",
                color=0x8B0000
            )
            embed.add_field(name="Temperature", value=f"{temp_c}°C / {temp_f}°F", inline=True)
            embed.add_field(name="Condition", value=desc, inline=True)
            embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
            embed.add_field(name="Wind Speed", value=f"{wind_mps} m/s /{wind_mph} mph", inline=True)

            await interaction.response.send_message(embed=embed)

#trivia
@commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
@bot.tree.command(name='trivia', description="Get a trivia question, multiple choice answers")
async def trivia(interaction: discord.Interaction):
    on_cooldown, retry_after = check_cooldown(interaction.user.id, "trivia", 10)
    if on_cooldown:
        await interaction.response.send_message(f"Please wait {retry_after} seconds before using this command again.", ephemeral=True)
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

    if not view.answered:
        for child in view.children:
            child.disabled = True
        try:
            await view.message.edit(content=f"⏰ Time's up! The correct answer was **{correct}**.", view=view)
        except discord.NotFound:
            pass
async def handle_trivia_answer(user_id: int, is_correct: bool):
    user_scores[user_id] = user_scores.get(user_id, 0) + int(is_correct)
    save_scores(user_scores)

@bot.tree.command(name='score', description="Get your trivia score")
async def score(interaction: discord.Interaction):
    uid = interaction.user.id
    score = user_scores.get(uid, 0)
    await interaction.response.send_message(f"🏆 {interaction.user.display_name}, your trivia score is: **{score}**")

#timezone conversion
@bot.tree.command(name='tzconvert', description="Convert a time from one timezone to another")
@app_commands.describe(
    time="Time to convert (now, HH:MM, or YYYY-MM-DD HH:MM)",
    from_tz="Source timezone",
    to_tz="Target timezone"
)
async def tzconvert(interaction: discord.Interaction, time: str, from_tz: str, to_tz: str):
    await interaction.response.defer()
    try:
        from_tz = normalize_tz(from_tz)
        to_tz = normalize_tz(to_tz)

        from_zone = pytz.timezone(from_tz)
        to_zone = pytz.timezone(to_tz)

        if time.lower() == "now":
            input_dt = datetime.now(from_zone)
        else:
            if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", time):
                native_dt = datetime.strptime(time, "%Y-%m-%d %H:%M")
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                native_dt = datetime.strptime(f"{today} {time}", "%Y-%m-%d %H:%M")

            input_dt = from_zone.localize(native_dt)

        converted = input_dt.astimezone(to_zone)

        await interaction.followup.send(
            f"🕒 `{input_dt.strftime('%Y-%m-%d %H:%M')}` in **{from_tz}** is "
            f"`{converted.strftime('%Y-%m-%d %H:%M')}` in **{to_tz}**"
        )
    except UnknownTimeZoneError:
        await interaction.followup.send("⚠️ Unknown timezone provided.", ephemeral=True)
    except ValueError:
        await interaction.followup.send("⚠️ Invalid time format. Use 'now', 'HH:MM' or 'YYYY-MM-DD HH:MM'.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ An unexpected error occurred: {e}", ephemeral=True)
#tzlist
@bot.tree.command(name='timezones', description='List supported timezones')
async def timezones(interaction: discord.Interaction):
    tz_list = [f"**{abbr}** → `{full}`" for abbr, full in config.SUPPORTED_TZ.items()]
    tz_text = "\n".join(tz_list)

    embed = discord.Embed(
        title="🕒 Supported Timezones",
        description=tz_text,
        color=0x8B0000,
    )
    await interaction.response.send_message(embed=embed)

#currency
@bot.tree.command(name='currency',description="Get the current exchange rate for a currency")
@app_commands.describe(
    amount="Amount of money to convert",
    from_currency="Currency code to convert from (e.g., USD)",
    to_currency="Currency code to convert to (e.g., EUR)"
)
async def currency(interaction: discord.Interaction, amount: float, from_currency: str, to_currency: str):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    url = f"https://open.er-api.com/v6/latest/{from_currency}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await interaction.response.send_message(f"❌ API request failed with status code: {resp.status}")
                    return
                data = await resp.json()
        except Exception as e:
            await interaction.response.send_message(f"❌ Error fetching exchange rate: {e}")
            return

    if data.get("result") != "success":
        await interaction.response.send_message(f"❌ API error: {data.get('error-type', 'Unknown error.')}")
        return

    rates = data.get("rates", {})
    if to_currency not in rates:
        await interaction.response.send_message(f"❌ Unsupported or invalid currency: `{to_currency}`")
        return

    converted = amount * rates[to_currency]
    await interaction.response.send_message(f"💱 {amount} {from_currency} = {converted:.2f} {to_currency}")

#8ball
@bot.tree.command(name="8ball", description="Ask the magic 8ball a question")
@app_commands.describe(question="Your yes/no question")
async def eight_ball(interaction: discord.Interaction, question: str):
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

#xkcd
@bot.tree.command(name="xkcd", description="Get a random XKCD comic")
async def random_xkcd(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://c.xkcd.com/random/comic/", allow_redirects=False) as resp:
            if resp.status != 302:
                await interaction.response.send_message("Couldn't fetch a random XKCD comic.",ephemeral=True)
                return
            location = resp.headers.get("Location")
            if not location:
                await interaction.response.send_message("Couldn't get the comic URL.",ephemeral=True)
                return

        json_url = location + "info.0.json"
        async with session.get(json_url) as resp:
            if resp.status != 200:
                await interaction.response.send_message("Couldn't fetch XKCD comic info.",ephemeral=True)
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
#credits
@bot.tree.command(name="credits",description="Get the credits for this bot")
async def credit(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Credits",
        description="Made by **SPOOPINATURAL**",
        color=0x8B0000
    )
    embed.add_field(
        name="GitHub",
        value="[Github](https://github.com/SPOOPINATURAL)",
        inline=True
    )
    embed.add_field(
        name="Instagram",
        value="[Instagram](https://instagram.com/spoopi_natural)",
        inline=True
    )
    embed.add_field(
        name="Tumblr",
        value="[Tumblr](https://spoopi-natural.tumblr.com)",
        inline=True
    )
    embed.add_field(
        name="VGen",
        value="[VGen](https://vgen.co/SPOOPINATURAL)",
        inline=True
    )
    embed.add_field(
        name="Discord",
        value="spoopinatural",
        inline=True
    )

    #icon
    embed.set_thumbnail(url="https://i.imgur.com/BxmePJZ.png")

    #banner
    embed.set_image(url="https://i.imgur.com/x6DzWEK.png")

    embed.set_footer(text="Thank you for using the bot!")

    await interaction.response.send_message(embed=embed)
#dice
@bot.tree.command(name="d20", description="Roll d20")
async def roll_d20(interaction: discord.Interaction):
    result = random.randint(1, 20)
    embed = discord.Embed(
        title="🎲 D20 Roll",
        description=f"You rolled a **{result}**!",
        color=0x8B0000
    )
    await interaction.response.send_message(embed=embed)

#rps
@bot.tree.command(name="rps", description="Play Rock, Paper, Scissors")
async def rps_command(interaction: discord.Interaction):
    view = RPSView(player_id=interaction.user.id)
    await interaction.response.send_message("Choose your move:", view=view)

#date
@bot.tree.command(name="date", description="Get the current date")
@app_commands.describe(tz="Timezone name (e.g. Europe/London). Defaults to UTC.")
async def date_command(interaction: discord.Interaction, tz: str = None):
    try:
        timezone = pytz.timezone(tz) if tz else pytz.UTC
    except pytz.UnknownTimeZoneError:
        await interaction.response.send_message(f"❌ Unknown timezone: `{tz}`. Use `/timezones` for a list.")
        return

    now = datetime.now(timezone)
    day = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%I:%M %p")

    embed = discord.Embed(
        title="📅 Date & Time",
        description=f"**{day}**, {date_str} — {time_str} ({tz})",
        color=0x8B0000
    )
    await interaction.response.send_message(embed=embed)

#random plane
@bot.tree.command(name="plane",description="Get a random WW1 plane")
async def airplane(interaction: discord.Interaction):
    try:
        if not planes:
            await interaction.response.send_message("❌ No plane data loaded.")
            return

        plane = random.choice(planes)
        specs = plane.get("specs", {})
        embed = discord.Embed(
            title=plane.get("name", "Unknown"),
            description=(
                f"**Nation:** {plane.get('nation', 'N/A')}\n"
                f"**Year:** {plane.get('year', 'N/A')}\n"
                f"**Crew:** {specs.get('crew', 'N/A')}\n"
                f"**Wingspan:** {specs.get('wingspan', 'N/A')}\n"
                f"**Speed:** {specs.get('speed', 'N/A')}\n"
                f"**Engine:** {specs.get('engine', 'N/A')}\n"
                f"**Armament:** {specs.get('armament', 'N/A')}"
            ),
            color=discord.Color.red()
        )
        embed.set_image(url=plane.get("image", ""))
        embed.set_footer(text="Random WW1 Plane")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to fetch plane data: {e}")

#help
@bot.tree.command(name='info', description='Command list')
async def info(interaction: discord.Interaction):
    guild_id = interaction.guild.id if interaction.guild.id else 0
    view = InfoPages(guild_id)
    view.message = await interaction.response.send_message(embed=view.pages[0], view=view)
if __name__ == "__main__":
    webserver.keep_alive()
    bot.run(config.DISCORD_TOKEN, log_handler=handler, log_level=logging.INFO)