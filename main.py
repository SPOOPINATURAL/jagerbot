import discord
import random
import aiohttp
import dateparser
import html
import json
import asyncio
from discord.ext import commands, tasks
from discord.ui import View, Button
import logging
from dotenv import load_dotenv
import os
import pytz
from datetime import datetime, timedelta
import re
from dateparser.conf import settings as dp_settings
from types import SimpleNamespace
from dateutil.tz import UTC
import tracemalloc
import warnings
import webserver

#files n shi
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TRACKER_API_KEY = os.getenv('TRACKER_API_KEY')
print(f"[DEBUG] API Key: {TRACKER_API_KEY}")
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
TIMEZONES = sorted(pytz.all_timezones)
ALERTS_FILE = "data/alerts.json"
tracemalloc.start()
warnings.simplefilter('always', RuntimeWarning)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
custom_settings = SimpleNamespace(**dp_settings.__dict__)
custom_settings.RETURN_AS_TIMEZONE_AWARE = False
timeout = aiohttp.ClientTimeout(total=5)

bot = commands.Bot(command_prefix='>', intents=intents)

#who is jason and why am i fetching him
async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return {}

#alerts
alerts = {}
def load_alerts():
    global alerts
    try:
        with open(ALERTS_FILE, "r") as f:
            data = json.load(f)
            # Convert time strings back to datetime
            for user_id, user_alerts in data.items():
                for alert in user_alerts:
                    alert['time'] = datetime.fromisoformat(alert['time'])
            alerts = data
    except FileNotFoundError:
        alerts = {}

def save_alerts():
    with open(ALERTS_FILE, "w") as f:
        to_save = {}
        for user_id, user_alerts in alerts.items():
            to_save[user_id] = []
            for alert in user_alerts:
                a = alert.copy()
                a['time'] = a['time'].isoformat()
                to_save[user_id].append(a)
        json.dump(to_save, f, indent=2)

def parse_time(time_str):
    units = {"s": 1, "m": 60, "h": 3600}
    try:
        amount = int(time_str[:-1])
        unit = time_str[-1].lower()
        return amount * units[unit]
    except (ValueError, KeyError):
        return None

#load jsons
def load_all_json_from_folder(folder="data"):
    data = {}
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            path = os.path.join(folder, filename)
            with open(path, "r", encoding="utf-8") as f:
                key = os.path.splitext(filename)[0]  # filename without .json
                data[key] = json.load(f)
    return data
all_data = load_all_json_from_folder()

maps = all_data.get("maps",{})
operators = all_data.get("operators",{})
planes = all_data.get("planes",[])
alerts = all_data.get("alerts",{})

#aliases function
def find_match(data_dict: dict, user_input: str):
    user_input = user_input.lower()
    for key, entry in data_dict.items():
        if user_input == key:
            return entry
        if "aliases" in entry and user_input in [a.lower() for a in entry["aliases"]]:
            return entry
    return None

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
        if self.page > 0:
            self.page -= 1
            await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_page:
            self.page += 1
            await self.update_message()
        await interaction.response.defer()

#trivia
user_scores = {}
class TriviaView(discord.ui.View):
    def __init__(self, ctx, correct_letter, correct_answer, author_id):
        super().__init__(timeout=15)
        self.ctx = ctx
        self.correct_letter = correct_letter
        self.correct_answer = correct_answer
        self.author_id = author_id
        self.answered = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="A", style=discord.ButtonStyle.primary)
    async def a_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, "A")

    @discord.ui.button(label="B", style=discord.ButtonStyle.primary)
    async def b_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, "B")

    @discord.ui.button(label="C", style=discord.ButtonStyle.primary)
    async def c_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, "C")

    @discord.ui.button(label="D", style=discord.ButtonStyle.primary)
    async def d_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, "D")

    async def process_answer(self, interaction, letter):
        self.answered = True
        for child in self.children:
            child.disabled = True
        if letter == self.correct_letter:
            user_scores[interaction.user.id] = user_scores.get(interaction.user.id, 0) + 1
            await interaction.response.edit_message(content=f"✅ Correct! Total score: **{user_scores[interaction.user.id]}**", view=self)
        else:
            await interaction.response.edit_message(content=f"❌ Wrong! Correct answer: **{self.correct_answer}**", view=self)
        self.stop()

#quote list
quotes = [
    "Birthdays. Proposals. These should be surprises. No one wants a grenade to the face.",
    "Is there sarcasm in this?",
    "Remember, I can't fix you like I fix your cars.",
    "I'm an engineer, not a medic!",
    "You can stop worrying about grenades now!",
    "Your plan is as good as your intel!",
    "Before we start, does anyone want to bail out?",
    "I would not have said it like that, but, it is cool.",
    "Stay alert and watch for trouble, yes?",
    "Just let me know when grenades start flying.",
    "Someone owes me a steak dinner!",
    "They said it could not be done. They said it was designed for tanks. They said, I could not make it smaller and more accurate. They were wrong.",
    "One of my better tactical strategies is to stay alive. So far, so good.",
]
#images
image_urls = [
    "https://i.imgur.com/3ZIBxuh.png",
    "https://i.imgur.com/fafftDC.jpeg",
    "https://i.imgur.com/iUjJyba.png",
    "https://i.imgur.com/wltqqd0.jpeg",
    "https://i.imgur.com/rC6bxUS.jpeg",
    "https://i.imgur.com/UAlUh4W.jpeg",
    "https://i.imgur.com/K60KP2c.jpeg",
    "https://i.imgur.com/2slTvIy.jpeg",
    "https://i.imgur.com/tpr9aoW.png",
    "https://i.imgur.com/wSFVwgg.jpeg",
    "https://i.imgur.com/y3BlmVT.jpeg",
    "https://i.imgur.com/MDp5v9G.jpeg",
    "https://i.imgur.com/OB9X52Y.png",
    "https://ibb.co/QFzhXkHy",
    "https://i.imgur.com/jSbZjnG.jpeg",
    "https://i.imgur.com/AA6zTQ7.jpeg",
    "https://i.imgur.com/im4dYj2.jpeg",
    "https://i.imgur.com/sdkffat.png",
    "https://i.imgur.com/zho3DZM.png",
    "https://i.imgur.com/4PRVmsz.png",
    "https://i.imgur.com/yGfu5OD.png",
    "https://i.imgur.com/KLTuASH.jpeg",
    "https://i.imgur.com/FDog6KT.png",

]

#images
clancy_images = [
    "https://i.imgur.com/1cuthyS.jpeg",
    "https://i.imgur.com/3QqKqky.jpeg",
    "https://i.imgur.com/Pypy5Um.jpeg",
    "https://i.imgur.com/pTxuW0k.jpeg",
    "https://i.imgur.com/5N5SICy.jpeg",
    "https://i.imgur.com/lAAkcZv.jpeg",
    "https://i.imgur.com/1gRZP6B.jpeg",
    "https://i.imgur.com/1Zmsj69.jpeg",
    "https://i.imgur.com/T86njLU.jpeg",
    "https://i.imgur.com/HWqnDQV.jpeg",
    "https://i.imgur.com/9sRRahk.jpeg",
    "https://i.imgur.com/FZdxbbg.jpeg",
    "https://i.imgur.com/k9U1xsD.jpeg",
    "https://i.imgur.com/Eb57KeJ.jpeg",
    "https://i.imgur.com/KhiDgPa.jpeg",
    "https://i.imgur.com/lL9YYDe.jpeg",
    "https://i.imgur.com/CunLaFJ.jpeg",
    "https://i.imgur.com/Eo0RxHB.jpeg",
    "https://i.imgur.com/4ETJuvy.jpeg",

]

# info
class InfoPages(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.pages = []
        self.current = 0
        self.create_pages()

    def create_pages(self):
        # Page 1: R6 Siege
        embed1 = discord.Embed(
            title="JägerBot Commands List (Page 1/5)",
            description="**R6 Siege Commands**",
            color=0x8B0000
        )
        embed1.add_field(name=">r6stats (platform) (username)", value="Fetch R6 Siege stats from a user", inline=False)
        embed1.add_field(name=">quote", value="Get a random Jäger quote", inline=False)
        embed1.add_field(name=">operator (operator name)", value="Overview of a Siege Operator.", inline=False)
        embed1.add_field(name=">operatorlist", value="List of all playable operators.", inline=False)
        embed1.add_field(name=">operatorrandom (attack of defense)", value="Gives you a random operator.", inline=False)
        embed1.add_field(name=">map (map name)", value="Get a floorplan of a ranked map.", inline=False)
        embed1.add_field(name=">maplist", value="List of ranked maps", inline=False)
        self.pages.append(embed1)

        # Page 2: Minecraft
        embed2 = discord.Embed(
            title="JägerBot Commands List (Page 2/5)",
            description="**Minecraft Commands**",
            color=0x8B0000
        )
        embed2.add_field(name=">mcwiki (search term)", value="Search Minecraft Wiki.", inline=False)
        embed2.add_field(name=">mcrecipe (item)", value="Look up a crafting recipe.", inline=False)
        embed2.add_field(name=">mcadvancement (name)", value="Info on advancements.", inline=False)
        embed2.add_field(name=">mcenchant (name)", value="Minecraft enchantment info.", inline=False)
        embed2.add_field(name=">mcbiome (name)", value="Info about biomes.", inline=False)
        embed2.add_field(name=">mcstructure (name)", value="Info about structures.", inline=False)
        embed2.add_field(name=">mcplayer (username)", value="Fetch player UUID and skin.", inline=False)
        embed2.add_field(name=">mcserverstatus", value="Check VDSMP server status.", inline=False)
        self.pages.append(embed2)

        # Page 3: Fun
        embed3 = discord.Embed(
            title="JägerBot Commands List (Page 3/5)",
            description="**Fun / Stupid Stuff**",
            color=0x8B0000
        )
        embed3.add_field(name=">image", value="Get a random image.", inline=False)
        embed3.add_field(name=">longo", value="longo", inline=False)
        embed3.add_field(name=">clancy", value="Obtain a random Clancy image.", inline=False)
        embed3.add_field(name=">trivia", value="Play some trivia.", inline=False)
        embed3.add_field(name=">score", value="Your trivia score.", inline=False)
        embed3.add_field(name=">xkcd", value="Get a random xkcd comic.", inline=False)
        embed3.add_field(name=">8ball (question)", value="8ball makes a decision for you (ex. '>8ball should i take a walk').", inline=False)
        embed3.add_field(name=">d20", value="Roll a d20.", inline=False)
        embed3.add_field(name=">rps", value="Play Rock, Paper, Scissors.", inline=False)
        embed3.add_field(name=">plane", value="Gives a random WW1 plane with specs.", inline=False)
        self.pages.append(embed3)
        # Page 4: Utility
        embed4 = discord.Embed(
            title="JägerBot Commands List (Page 4/5)",
            description="**Utility Commands**",
            color=0x8B0000
        )
        embed4.add_field(name=">weather (city)",
                         value="Tells you the current weather in a city (ex.'>weather seattle').", inline=False)
        embed4.add_field(name=">convert (time) (timezone a) to (timezone b)",
                         value="Converts one timezone to another (ex. '>convert now UTC to IST').", inline=False)
        embed4.add_field(name=">timezones", value="Lists every timezone.", inline=False)
        embed4.add_field(name=">date (timezone)", value="Tells you the day and calendar date. Timezone optional.",
                         inline=False)
        embed4.add_field(name=">currency (amount) (currency a) (currency b)",
                         value="Converts one currency to another (ex. '>currency 100 USD EUR').", inline=False)
        embed4.add_field(name=">alert (activity) (time)",
                         value="Creates an alert, bot will DM you when it’s time. Use 'recurring' for repeated alerts (ex.'>alert Event in 10minutes' or '>alert Reminder 2025-06-01 18:00 PST recurring 24h').",
                         inline=False)
        embed4.add_field(name=">listalerts", value="Lists all your alerts.", inline=False)
        embed4.add_field(name=">cancelalerts", value="Cancels all your alerts.", inline=False)
        embed4.add_field(name=">credits", value="See who made/helped with the bot.", inline=False)
        self.pages.append(embed4)

        # Page 5: Warframe
        embed5 = discord.Embed(
            title="JägerBot Commands List (Page 5/5)",
            description="**Warframe Commands**",
            color=0x8B0000
        )
        embed5.add_field(name=">wfbaro",
                         value="Tells you when Baro will arrive and where he is.", inline=False)
        embed5.add_field(name=">wfnews",
                         value="Latest Warframe news.", inline=False)
        embed5.add_field(name=">wfnightwave", value="Warframe Nightwave quests.", inline=False)
        embed5.add_field(name=">date (timezone)", value="Tells you the day and calendar date. Timezone optional.",
                         inline=False)
        embed5.add_field(name=">wfprice",
                         value="warframe.market item price.", inline=False)
        self.pages.append(embed5)

    async def update_message(self, interaction):
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current > 0:
            self.current -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current < len(self.pages) - 1:
            self.current += 1
            await self.update_message(interaction)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass
#weather
def get_weather_emoji(condition):
    condition = condition.lower()
    if "clear" in condition:
        return "☀️"
    elif "cloud" in condition:
        return "☁️"
    elif "rain" in condition:
        return "🌧️"
    elif "storm" in condition or "thunder" in condition:
        return "⛈️"
    elif "snow" in condition:
        return "❄️"
    elif "fog" in condition or "mist" in condition:
        return "🌫️"
    else:
        return "🌈"

@bot.event
async def on_ready():
    print(f"Ready :)")
    load_alerts()
    check_alerts.start()
    activity = discord.Game(name=">info")
    await bot.change_presence(status=discord.Status.online, activity=activity)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not recognized. Use `>info` to see the list of commands.")
    else:
        raise error

#alerts and stuff
@tasks.loop(seconds=30)
async def check_alerts():
    now = datetime.now(UTC)
    to_remove = []

    for user_id, user_alerts in list (alerts.items()):
        user = bot.get_user(int(user_id))
        if not user:
            continue
        for alarm in list(user_alerts):
            if alarm['time'] <= now:
                user = bot.get_user(int(user_id))
                if user:
                    try:
                        await user.send(f"⏰ Reminder: **{alarm['event']}**")
                    except Exception:
                        # Could not DM
                        pass
                if alarm.get('recurring'):
                    # Reschedule alert
                    seconds = parse_time(alarm['recurring'])
                    if seconds:
                        alarm['time'] = alarm['time'] + timedelta(seconds=seconds)
                else:
                    to_remove.append((user_id, alarm))

    for user_id, alarm in to_remove:
        alerts[user_id].remove(alarm)
        if len(alerts[user_id]) == 0:
            del alerts[user_id]

    save_alerts()


@bot.command()
async def hello(ctx):
    await ctx.send(f"Hallo {ctx.author.mention} :)")

#quote
@bot.command(name='quote')
async def quote(ctx):
    selected_quotes = random.choice(quotes)
    await ctx.send(selected_quotes)
#images
@bot.command(name='image')
async def image(ctx):
    images_url = random.choice(image_urls)
    await ctx.send(images_url)

@bot.command(name='clancy')
async def clancy(ctx):
    clancy_image = random.choice(clancy_images)
    await ctx.send(clancy_image)

@bot.command(name='longo')
async def longo(ctx):
    image_url = "https://i.imgur.com/J1P7g5f.jpeg"
    embed = discord.Embed(title="longo")
    embed.set_image(url=image_url)
    await ctx.send(embed=embed)

#r6stats
@bot.command(name='r6stats')
async def r6stats(ctx, platform: str, *, username: str):
    url = f"https://public-api.tracker.gg/v2/r6/standard/profile/{platform}/{username}"
    headers = {
        "TRN-Api-Key": TRACKER_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            status = resp.status
            text = await resp.text()
            print(f"[DEBUG] Status: {resp.status}")
            print(f"[DEBUG] Response: {await resp.text()}")
            if resp.status != 200:
                await ctx.send(f"Could not find stats for `{username}` on `{platform}`.")
                return
            data = await resp.json()

    stats = data['data']['segments'][0]['stats']
    rank = stats.get('rankedRank', {}).get('displayValue', 'N/A')
    kd = stats.get('killsDeathRatio', {}).get('displayValue', 'N/A')
    win = stats.get('winLossRatio', {}).get('displayValue', 'N/A')

    embed = discord.Embed(title=f"R6 Stats for {username}", color=0x00ff00)
    embed.add_field(name="Platform", value=platform.upper(), inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="K/D Ratio", value=kd, inline=True)
    embed.add_field(name="Win/Loss Ratio", value=win, inline=True)

    await ctx.send(embed=embed)

#weather
@bot.command(name='weather')
async def weather(ctx, *, city: str):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                await ctx.send(f"❌ Could not find weather for `{city}`.")
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

            await ctx.send(embed=embed)

#trivia
@bot.command(name='trivia')
async def trivia(ctx):
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

    view = TriviaView(ctx, correct_letter, correct, ctx.author.id)
    message = await ctx.send(embed=embed, view=view)

    await view.wait()

    if not view.answered:
        for child in view.children:
            child.disabled = True
        await message.edit(content=f"⏰ Time's up! The correct answer was **{correct}**.", view=view)


@bot.command(name='score')
async def score(ctx):
    scores = user_scores.get(ctx.author.id, 0)
    await ctx.send(f"🏆 {ctx.author.display_name}, your trivia score is: **{scores}**")

#timezone conversion
@bot.command(name='convert')
async def convert(ctx, *args):
    try:
        args = list(args)
        if "to" not in args:
            return await ctx.send("⚠️ Usage: `!convert [now|HH:MM|YYYY-MM-DD HH:MM] FROM_TZ to TO_TZ`")

        to_index = args.index("to")
        from_tz = args[to_index - 1].upper()
        to_tz = args[to_index + 1].upper()

        if args[0].lower() == "now":
            base_dt = datetime.now(UTC)
            input_dt = base_dt
            from_zone = pytz.timezone(from_tz)
            input_dt = pytz.utc.localize(base_dt).astimezone(from_zone)
        else:
            time_part = args[0]
            date_part = None
            if re.match(r"\d{4}-\d{2}-\d{2}", args[0]):
                date_part = args[0]
                time_part = args[1]
                from_tz = args[2].upper()
                to_tz = args[4].upper()

            if date_part:
                dt_str = f"{date_part} {time_part}"
                input_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                input_dt = datetime.strptime(f"{today} {time_part}", "%Y-%m-%d %H:%M")

            from_zone = pytz.timezone(from_tz)
            input_dt = from_zone.localize(input_dt)

        to_zone = pytz.timezone(to_tz)
        converted = input_dt.astimezone(to_zone)

        await ctx.send(
            f"🕒 `{input_dt.strftime('%Y-%m-%d %H:%M')}` in **{from_tz}** is "
            f"`{converted.strftime('%Y-%m-%d %H:%M')}` in **{to_tz}**"
        )

    except Exception as e:
        await ctx.send("⚠️ Invalid format or timezone. Try: `!convert now UTC to IST`, `!convert 15:30 UTC to EST`")

#tz list
@bot.command(name='timezones')
async def timezones(ctx):
    paginator = TimezonePaginator(ctx)
    embed = discord.Embed(
        title=f"Timezones (Page 1/{paginator.max_page + 1})",
        description="\n".join(TIMEZONES[:paginator.items_per_page]),
        color=0x3498db,
    )
    paginator.message = await ctx.send(embed=embed, view=paginator)

#currency
@bot.command(name='currency')
async def currency(ctx, amount: float, from_currency: str, to_currency: str):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    url = f"https://open.er-api.com/v6/latest/{from_currency}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await ctx.send(f"❌ API request failed with status code: {resp.status}")
                    return
                data = await resp.json()
        except Exception as e:
            await ctx.send(f"❌ Error fetching exchange rate: {e}")
            return

    if data.get("result") != "success":
        await ctx.send(f"❌ API error: {data.get('error-type', 'Unknown error.')}")
        return

    rates = data.get("rates", {})
    if to_currency not in rates:
        await ctx.send(f"❌ Unsupported or invalid currency: `{to_currency}`")
        return

    converted = amount * rates[to_currency]
    await ctx.send(f"💱 {amount} {from_currency} = {converted:.2f} {to_currency}")

#alert commands
@bot.command(name="alert")
async def alert(ctx, *, input_str: str):
    recurring = None
    if "recurring" in input_str:
        parts = input_str.rsplit("recurring", 1)
        input_str = parts[0].strip()
        recurring = parts[1].strip()

        if parse_time(recurring) is None:
            await ctx.send("❌ Invalid recurring time format! Use number + s/m/h.")
            return

    keywords = [' in ', ' at ', ' on ', ' tomorrow', ' today', ' next ', ' this ']
    split_pos = None
    for kw in keywords:
        pos = input_str.lower().find(kw)
        if pos != -1:
            split_pos = pos
            break

    if split_pos is not None:
        event = input_str[:split_pos].strip()
        datetime_str = input_str[split_pos:].strip()
    else:
        # fallback
        parts = input_str.split(maxsplit=1)
        event = parts[0]
        datetime_str = parts[1] if len(parts) > 1 else ""

    date = dateparser.parse(datetime_str, settings={'RETURN_AS_TIMEZONE_AWARE': True, 'TO_TIMEZONE': 'UTC'})

    if date is None:
        await ctx.send("❌ Couldn't parse the date/time. Try a different format.")
        return

    now = datetime.now(UTC)
    if date < now:
        await ctx.send("❌ The specified time is in the past.")
        return

    user_id = str(ctx.author.id)
    if user_id not in alerts:
        alerts[user_id] = []

    alerts[user_id].append({
        "event": event,
        "time": date,
        "recurring": recurring
    })

    save_alerts()

    await ctx.send(f"✅ Alert for **{event}** set at {date.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                   + (f", recurring every {recurring}" if recurring else "") + ".")

@bot.command(name="cancelalerts")
async def cancelalerts(ctx):
    user_id = str(ctx.author.id)
    if user_id in alerts:
        del alerts[user_id]
        save_alerts()
        await ctx.send("🛑 All your alerts have been cancelled.")
    else:
        await ctx.send("ℹ️ You have no active alerts.")

@bot.command(name="listalerts")
async def listalerts(ctx):
    user_id = str(ctx.author.id)
    if user_id not in alerts or len(alerts[user_id]) == 0:
        await ctx.send("ℹ️ You have no active alerts.")
        return

    embed = discord.Embed(title=f"{ctx.author.name}'s Alerts", color=0x2ecc71)
    for i, alert in enumerate(alerts[user_id], 1):
        time_left = alert['time'] - datetime.now(UTC)
        minutes, seconds = divmod(int(time_left.total_seconds()), 60)
        hours, minutes = divmod(minutes, 60)
        time_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
        recur = f" (recurring every {alert['recurring']})" if alert.get('recurring') else ""
        embed.add_field(name=f"{i}. {alert['event']}", value=f"Triggers in {time_str}{recur}", inline=False)

    await ctx.send(embed=embed)
#r6 op info
@bot.command(name='operator', aliases=["op"])
async def operator_command(ctx, *, name: str):
    op = find_match(operators, name)
    if not op:
        await ctx.send(f"❌ Operator `{name}` not found.")
        return

    embed = discord.Embed(
        title=op['name'],
        description=op['bio'],
        color=0x8B0000
    )
    embed.add_field(name="Role", value=op['role'], inline=True)
    embed.add_field(name="Health", value=op['health'], inline=True)
    embed.add_field(name="Speed", value=op['speed'], inline=True)
    embed.add_field(name="Squad", value=op['squad'], inline=True)
    embed.add_field(name="Primary Weapons", value=", ".join(op['primary_weapons']), inline=False)
    embed.add_field(name="Secondary Weapons", value=", ".join(op['secondary_weapons']), inline=False)
    embed.add_field(name="Primary Gadget", value=op['primary_gadget'], inline=False)
    embed.add_field(name="Secondary Gadgets", value=", ".join(op['secondary_gadgets']), inline=False)

    if op.get('image_url'):
        embed.set_image(url=op['image_url'])
    if op.get('icon_url'):
        embed.set_thumbnail(url=op['icon_url'])

    await ctx.send(embed=embed)

#op list
@bot.command(name="operatorlist", aliases=["oplist","listops"])
async def operator_list(ctx):
    names = sorted(op_data["name"] for op in operators)

    columns = [[], [], []]
    for i, name in enumerate(names):
        columns[i % 3].append(name)

    embed = discord.Embed(
        title="Available Operators",
        description="Use `>operator [name]` to view detailed info.",
        color=0x8B0000
    )
    embed.add_field(name="Operators A–H", value=col_text[0] or "None", inline=True)
    embed.add_field(name="Operators I–R", value=col_text[1] or "None", inline=True)
    embed.add_field(name="Operators S–Z", value=col_text[2] or "None", inline=True)

    await ctx.send(embed=embed)

#random op
@bot.command(name="operatorrandom", aliases=["oprandom", "randomop", "randomoperator"])
async def r6_operator(ctx, role: str = None):
    try:
        role_aliases = {
            "attacker": ["attack", "attacker", "atk", "attk"],
            "defender": ["defense", "defender", "def"],
        }
        selected_role = None

        if role:
            role = role.lower()
            for key, aliases in role_aliases.items():
                if role in aliases:
                    selected_role = key
                    break
            if not selected_role:
                await ctx.send("❌ Invalid role! Use `attack` or `defense` (or aliases like `atk`, `def`).")
                return

        operators_list = list(operators.values()) if isinstance(operators, dict) else operators

        filtered = [op for op in operators_list if op.get("role", "").lower() == selected_role] if selected_role else operators_list

        if not filtered:
            await ctx.send("❌ No operators found for that role.")
            return

        op = random.choice(filtered)

        embed = discord.Embed(
            title=op.get('name', 'Unknown'),
            description=op.get('bio', 'No bio available.'),
            color=0x8B0000
        )
        embed.add_field(name="Role", value=op.get('role', 'N/A'), inline=True)
        embed.add_field(name="Health", value=op.get('health', 'N/A'), inline=True)
        embed.add_field(name="Speed", value=op.get('speed', 'N/A'), inline=True)
        embed.add_field(name="Squad", value=op.get('squad', 'N/A'), inline=True)
        embed.add_field(name="Primary Weapons", value=", ".join(op.get('primary_weapons', [])), inline=False)
        embed.add_field(name="Secondary Weapons", value=", ".join(op.get('secondary_weapons', [])), inline=False)
        embed.add_field(name="Primary Gadget", value=op.get('primary_gadget', 'N/A'), inline=False)
        embed.add_field(name="Secondary Gadgets", value=", ".join(op.get('secondary_gadgets', [])), inline=False)

        if op.get('image_url'):
            embed.set_image(url=op['image_url'])
        if op.get('icon_url'):
            embed.set_thumbnail(url=op['icon_url'])

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Failed to load operator: {e}")

#map info
@bot.command(name="map")
async def map(ctx, *, name: str):
    try:
        if not isinstance(maps, dict):
            await ctx.send("❌ Map data is not in the correct format.")
            return

        m = find_match(maps, name)
        if not m:
            await ctx.send(f"❌ Map `{name}` not found.")
            return

        floors = m.get("floors", [])
        total = len(floors)
        if total == 0:
            await ctx.send(f"❌ Map `{m.get('name', name)}` has no floors data.")
            return

        def make_embed(idx: int) -> discord.Embed:
            fl = floors[idx]
            embed = discord.Embed(
                title=f"{m.get('name', 'Unknown')} – {fl.get('name', 'Floor')}",
                description=f"Floor {idx+1} / {total}",
                color=0x8B0000
            )
            embed.set_image(url=fl.get("image", ""))
            return embed

        class FloorView(View):
            def __init__(self):
                super().__init__(timeout=60)
                self.i = 0

            @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
            async def back(self, interaction: discord.Interaction, button: Button):
                self.i = (self.i - 1) % total
                await interaction.response.edit_message(embed=make_embed(self.i), view=self)

            @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
            async def forward(self, interaction: discord.Interaction, button: Button):
                self.i = (self.i + 1) % total
                await interaction.response.edit_message(embed=make_embed(self.i), view=self)

        await ctx.send(embed=make_embed(0), view=FloorView())

    except Exception as e:
        await ctx.send(f"❌ Error during map lookup: `{e}`")

#maplist
@bot.command(name="maplist")
async def map_list(ctx):
    try:
        if isinstance(maps, dict):
            map_names = sorted(m["name"] for m in maps.values() if "name" in m)
        else:
            map_names = sorted(m["name"] for m in maps if "name" in m)
    except Exception as e:
        await ctx.send(f"❌ Failed to load map data: `{e}`")
        return

    half = (len(map_names) + 1) // 2
    col1 = map_names[:half]
    col2 = map_names[half:]

    embed = discord.Embed(
        title="Available Ranked Maps",
        description="Use `>map <name>` to view floorplans.",
        color=0x8B0000
    )
    embed.add_field(name="Maps A–M", value="\n".join(col1) or "—", inline=True)
    embed.add_field(name="Maps N–Z", value="\n".join(col2) or "—", inline=True)

    await ctx.send(embed=embed)

#8ball
@bot.command(name="8ball")
async def eight_ball(ctx, *, question: str):
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
    await ctx.send(embed=embed)

#xkcd
@bot.command(name="xkcd")
async def random_xkcd(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://c.xkcd.com/random/comic/", allow_redirects=False) as resp:
            if resp.status != 302:
                await ctx.send("Couldn't fetch a random XKCD comic.")
                return
            location = resp.headers.get("Location")
            if not location:
                await ctx.send("Couldn't get the comic URL.")
                return

        json_url = location + "info.0.json"
        async with session.get(json_url) as resp:
            if resp.status != 200:
                await ctx.send("Couldn't fetch XKCD comic info.")
                return
            comic = await resp.json()

    embed = discord.Embed(
        title=comic["title"],
        url=f"https://xkcd.com/{comic['num']}",
        color=0x8B0000,
    )
    embed.set_image(url=comic["img"])
    embed.set_footer(text=f"Comic #{comic['num']}")

    await ctx.send(embed=embed)
#credits
@bot.command(name="credits")
async def credit(ctx):
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

    # Icon
    embed.set_thumbnail(url="https://i.imgur.com/BxmePJZ.png")

    # Banner
    embed.set_image(url="https://i.imgur.com/x6DzWEK.png")

    embed.set_footer(text="Thank you for using the bot!")

    await ctx.send(embed=embed)
#dice
@bot.command(name="d20")
async def roll_d20(ctx):
    result = random.randint(1, 20)

    embed = discord.Embed(
        title="🎲 D20 Roll",
        description=f"You rolled a **{result}**!",
        color=0x8B0000
    )

    # Optional: special messages for crit success/fail
    if result == 20:
        embed.add_field(name="Critical Success!", value="🎉 You nailed it!", inline=False)
    elif result == 1:
        embed.add_field(name="Critical Fail!", value="💀 Oof... try again!", inline=False)

    await ctx.send(embed=embed)

#rps
@bot.command(name="rps")
async def rps_command(ctx):
    class RPSView(View):
        def __init__(self):
            super().__init__(timeout=15)

        @discord.ui.button(label="🪨 Rock", style=discord.ButtonStyle.secondary)
        async def rock(self, interaction: discord.Interaction, button: Button):
            await handle_choice(interaction, "rock")

        @discord.ui.button(label="📄 Paper", style=discord.ButtonStyle.secondary)
        async def paper(self, interaction: discord.Interaction, button: Button):
            await handle_choice(interaction, "paper")

        @discord.ui.button(label="✂️ Scissors", style=discord.ButtonStyle.secondary)
        async def scissors(self, interaction: discord.Interaction, button: Button):
            await handle_choice(interaction, "scissors")

    async def handle_choice(interaction, user_choice):
        bot_choice = random.choice(["rock", "paper", "scissors"])

        if user_choice == bot_choice:
            result = "It's a draw!"
        elif (
            (user_choice == "rock" and bot_choice == "scissors") or
            (user_choice == "paper" and bot_choice == "rock") or
            (user_choice == "scissors" and bot_choice == "paper")
        ):
            result = "You win! 🎉"
        else:
            result = "You lose! 💀"

        embed = discord.Embed(
            title="🪨📄✂️ Rock Paper Scissors",
            description=f"**You:** {user_choice.capitalize()}\n**Bot:** {bot_choice.capitalize()}\n\n**{result}**",
            color=0x8B0000
        )
        await interaction.response.edit_message(embed=embed, view=None)

    await ctx.send("Choose your move:", view=RPSView())

#date
@bot.command(name="date")
async def date_command(ctx, tz: str = "UTC"):
    try:
        timezone = pytz.timezone(tz)
    except pytz.UnknownTimeZoneError:
        await ctx.send(f"❌ Unknown timezone: `{tz}`. Use `>timezones` for a list.")
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
    await ctx.send(embed=embed)
#mcwiki search
@bot.command(name="mcwiki")
async def mcwiki(ctx, *, query: str):
    search = query.replace(" ", "_")
    url = f"https://minecraft.wiki/w/{search}"
    embed = discord.Embed(
        title=f"Minecraft Wiki: {query.title()}",
        description=f"[Click here to view the wiki page]({url})",
        color=0x55a630
    )
    await ctx.send(embed=embed)

# >mcrecipe [item]
@bot.command(name="mcrecipe")
async def mcrecipe(ctx, *, item: str):
    await ctx.send(f"🔧 Crafting recipe for **{item.title()}**: [View on wiki](https://minecraft.wiki/w/{item.replace(' ', '_')})")

# >mcadvancement [name]
@bot.command(name="mcadvancement")
async def mcadvancement(ctx, *, name: str):
    await ctx.send(f"🏆 Info on advancement **{name.title()}**: [View on wiki](https://minecraft.wiki/w/{name.replace(' ', '_')})")

# >mcenchant [name]
@bot.command(name="mcenchant")
async def mcenchant(ctx, *, name: str):
    await ctx.send(f"✨ Enchantment **{name.title()}** details: [View on wiki](https://minecraft.wiki/w/{name.replace(' ', '_')})")

# >mcbiome [name]
@bot.command(name="mcbiome")
async def mcbiome(ctx, *, name: str):
    await ctx.send(f"🌲 Biome **{name.title()}** info: [View on wiki](https://minecraft.wiki/w/{name.replace(' ', '_')})")

# >mcstructure [name]
@bot.command(name="mcstructure")
async def mcstructure(ctx, *, name: str):
    await ctx.send(f"🏛️ Structure **{name.title()}**: [View on wiki](https://minecraft.wiki/w/{name.replace(' ', '_')})")

# >mcplayer [username]
@bot.command(name="mcplayer")
async def mcplayer(ctx, username: str):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{username}", headers=headers) as resp:
                if resp.status != 200:
                    await ctx.send("❌ Could not find that player.")
                    return
                data = await resp.json()
                uuid = data["id"]
        head_url = f"https://visage.surgeplay.com/head/128/{uuid}.png"
        skin_url = f"https://visage.surgeplay.com/full/512/{uuid}.png"

        embed = discord.Embed(
            title=f"Minecraft Player: {username}",
            description=f"UUID: `{uuid}`",
            color=0x8B0000
        )
        embed.set_image(url=skin_url)
        embed.set_thumbnail(url=head_url)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error: `{e}`")

#mcserverstatus
@bot.command(name="mcserverstatus")
async def mcserverstatus(ctx):
    try:
        server_ip = "vdsmp.mc.gg"

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mcsrvstat.us/2/{server_ip}") as resp:
                if resp.status != 200:
                    await ctx.send("❌ Error contacting the status API.")
                    return
                data = await resp.json()

        if not data.get("online"):
            await ctx.send("❌ The server is currently **offline**.")
            return

        motd = " ".join(data["motd"]["clean"]) if "motd" in data else "No MOTD"
        players = data.get("players", {})
        online = players.get("online", 0)
        max_players = players.get("max", 0)
        version = data.get("version", "Unknown")

        embed = discord.Embed(
            title="🌐 Minecraft Server Status",
            description="Your private server is **online** ✅",
            color=0x00cc66
        )
        embed.add_field(name="📃 MOTD", value=motd, inline=False)
        embed.add_field(name="👥 Players", value=f"{online}/{max_players}", inline=True)
        embed.add_field(name="🛠 Version", value=version, inline=True)

        icon = data.get("icon")
        if icon and icon.startswith("data:image/png;base64,"):
            pass  # Skip setting the thumbnail because Discord doesn't support base64
        elif icon:
            embed.set_thumbnail(url=icon)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error in mcserverstatus: `{e}`")

#wf baro
@bot.command(name="wfbaro")
async def wfbaro(ctx):
    data = await fetch_json("https://api.warframestat.us/pc/voidTrader")
    if data.get("active"):
        inventory = "\n".join([f"{item['item']} - {item['ducats']} Ducats, {item['credits']} Cr" for item in data["inventory"]])
        msg = f"**Baro Ki'Teer is at {data['location']} until {data['endString']}**\n\n{inventory}"
    else:
        msg = f"**Baro is not here right now.** Next visit: {data['startString']}"

    await ctx.send(msg)

#wfnews
@bot.command(name="wfnews")
async def wfnews(ctx):
    news = await fetch_json("https://api.warframestat.us/pc/news")
    items = [f"**{n['message']}**\n<n{n['link']}>" for n in news[:5]]
    await ctx.send("\n\n".join(items))

#wf nightwave
@bot.command(name="wfnightwave")
async def wfnightwave(ctx):
    data = await fetch_json("https://api.warframestat.us/pc/nightwave")
    missions = [f"**{m['title']}** - {m['reputation']} Rep" for m in data.get("activeChallenges", [])]
    await ctx.send("**Nightwave Challenges:**\n" + "\n".join(missions))

#wf prices
@bot.command(name="wfprice")
async def wfprice(ctx, *, item: str):
    item_url = item.replace(" ", "_").lower()
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.warframe.market/v1/items/{item_url}/orders") as resp:
            if resp.status != 200:
                await ctx.send("❌ Item not found or API issue.")
                return
            data = await resp.json()
            sell_orders = [o for o in data["payload"]["orders"] if o["order_type"] == "sell" and o["user"]["status"] == "ingame"]
            if sell_orders:
                cheapest = sorted(sell_orders, key=lambda x: x["platinum"])[0]
                await ctx.send(f"💰 Cheapest in-game seller: {cheapest['platinum']}p ({cheapest['user']['ingame_name']})")
            else:
                await ctx.send("❌ No in-game sellers found.")
#random plane
@bot.command(name="plane")
async def airplane(ctx):
    try:
        if not planes:
            await ctx.send("❌ No plane data loaded.")
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

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Failed to fetch plane data: {e}")

#help
@bot.command(name='info')
async def info(ctx):
    view = InfoPages()
    message = await ctx.send(embed=view.pages[0], view=view)
    view.message = message
webserver.keep_alive()
bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)