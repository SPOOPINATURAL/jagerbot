#standard stuff
import os, re, json, random, asyncio, logging, warnings, tracemalloc
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import List

#3rd party
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from discord import ButtonStyle, app_commands
import aiohttp
import dateparser
import pytz
from pytz.exceptions import UnknownTimeZoneError
from dateutil.tz import UTC
from bs4 import BeautifulSoup
from dateparser.conf import settings as dp_settings
from dotenv import load_dotenv

#local
import webserver
import config
from config import (
    DISCORD_TOKEN,
    ALLOWED_GUILD_IDS,
    WEATHER_API_KEY,
    TRACKER_API_KEY,
    TIMEZONES,
    DATA_FOLDER,
    ALERTS_FILE,
    SCORES_FILE,
)
from views.trivia import TriviaView
from views.rps import RPSView
from commands.r6 import r6, operators, maps
import utils.helpers as helpers
from utils.alerts import AlertChecker
from views.timezone_paginator import TimezonePaginator
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

bot = commands.Bot(command_prefix='>', intents=intents)
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

#trivia
user_scores = {}


#bot start events
@bot.event
async def on_ready():
    logger.info("Bot is ready, loading alerts and scores...")

    load_alerts()
    load_scores()

    if not check_alerts.is_running():
        check_alerts.start()

    activity = discord.Activity(type=discord.ActivityType.watching, name="Everything")
    await bot.change_presence(status=discord.Status.online, activity=activity)

    global sessions, cooldowns
    sessions.clear()
    cooldowns.clear()
    logger.info("✅ Cleared caches")

    logger.info("Ready :)")

def load_alerts():
    logger.info("Loaded alerts")

def load_scores():
    logger.info("Loaded scores")

async def setup_hook():
    await bot.tree.sync()
    await bot.tree.add_command(r6)
    logger.info(f"✅ Synced slash commands")

#prefix err
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not recognized. Use `/help` or `/info` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing argument: `{error.param.name}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument type. Please check your input.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You don't have permission to run this command.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("⚠️ I’m missing the necessary permissions to run that command.")
    else:
        print(f"Unhandled prefix command error: {error}")
        raise error

# / err
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "🚫 You don't have permission to use this command.", ephemeral=True
        )
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message(
            "⚠️ I’m missing the required permissions to do that.", ephemeral=True
        )
    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message(
            "❌ Slash command not found.", ephemeral=True
        )
    elif isinstance(error, app_commands.TransformerError):
        await interaction.response.send_message(
            "❌ Invalid input. Please check your command options.", ephemeral=True
        )
    else:
        print(f"Unhandled slash command error: {error}")
        try:
            await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)


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

@bot.tree.command(name='clancy', description="Obtain a random Clancy image")
async def clancy(interaction: discord.Interaction):
    clancy_image = random.choice(config.clancy_images)
    await interaction.response.send_message(clancy_image)

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

#alert commands
@bot.tree.command(name="alert", description="Set an alert for a specific event")
@app_commands.describe(input_str="Alert details, e.g. 'Meeting at 15:00 recurring 1h'")
async def alert(interaction: discord.Interaction, *, input_str: str):
    recurring = None
    if "recurring" in input_str:
        parts = input_str.rsplit("recurring", 1)
        input_str = parts[0].strip()
        recurring = parts[1].strip()

        if parse_time(recurring) is None:
            await interaction.response.send_message("❌ Invalid recurring time format! Use number + s/m/h.")
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
        await interaction.response.send_message("❌ Couldn't parse the date/time. Try a different format.")
        return

    now = datetime.now(UTC)
    if date < now:
        await interaction.response.send_message("❌ The specified time is in the past.")
        return

    user_id = str(interaction.user.id)
    if user_id not in alerts:
        alerts[user_id] = []

    alerts[user_id].append({
        "event": event,
        "time": date,
        "recurring": recurring
    })

    save_alerts()

    await interaction.response.send_message(f"✅ Alert for **{event}** set at {date.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                   + (f", recurring every {recurring}" if recurring else "") + ".")

@bot.tree.command(name="cancelalerts", description="Cancel all your active alerts")
async def cancelalerts(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in alerts:
        del alerts[user_id]
        save_alerts()
        await interaction.response.send_message("🛑 All your alerts have been cancelled.")
    else:
        await interaction.response.send_message("ℹ️ You have no active alerts.")

@bot.tree.command(name="listalerts", description="List all your active alerts")
async def listalerts(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id not in alerts or len(alerts[user_id]) == 0:
        await interaction.response.send_message("ℹ️ You have no active alerts.")
        return

    embed = discord.Embed(title=f"{interaction.user.name}'s Alerts", color=0x2ecc71)
    for i, alert in enumerate(alerts[user_id], 1):
        time_left = alert['time'] - datetime.now(UTC)
        minutes, seconds = divmod(int(time_left.total_seconds()), 60)
        hours, minutes = divmod(minutes, 60)
        time_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
        recur = f" (recurring every {alert['recurring']})" if alert.get('recurring') else ""
        embed.add_field(name=f"{i}. {alert['event']}", value=f"Triggers in {time_str}{recur}", inline=False)

    await interaction.response.send_message(embed=embed)
#r6 op info
@bot.tree.command(name='op', description="Get information about an R6 operator")
@app_commands.describe(name="Name of the operator")
@app_commands.autocomplete(name=operator_autocomplete)
async def operator_command(interaction: discord.Interaction, name: str):
    op = find_match(operators, name)
    if not op:
        await interaction.response.send_message(f"❌ Operator `{name}` not found.", ephemeral=True)
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

    await interaction.response.send_message(embed=embed)

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

#mcwiki search
@bot.tree.command(name="mcwiki", description="Search Minecraft Wiki")
@app_commands.describe(query="The wiki page to search")
async def mcwiki(interaction: discord.Interaction, query: str):
    search = query.replace(" ", "_")
    url = f"https://minecraft.wiki/w/{search}"
    embed = discord.Embed(
        title=f"📖 Minecraft Wiki: {query.title()}",
        description=f"[Click here to view the wiki page]({url})",
        color=0x55a630
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mcrecipe", description="Get crafting recipe from Minecraft Wiki")
@app_commands.describe(item="The item to get recipe for")
async def mcrecipe(interaction: discord.Interaction, item: str):
    await interaction.response.defer()  # Acknowledge and allow more time

    item_name = item.replace(" ", "_").title()
    wiki_url = f"https://minecraft.wiki/w/{item_name}"

    recipe_image_url = None

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(wiki_url) as resp:
                if resp.status != 200:
                    await interaction.followup.send(f"❌ Could not fetch wiki page for `{item}`.")
                    return
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                crafting_table = soup.find("table", class_="crafting-table")
                if crafting_table:
                    img = crafting_table.find("img")
                    if img and img.has_attr("src"):
                        recipe_image_url = img["src"]

                # fallback
                if not recipe_image_url:
                    crafting_div = soup.find(lambda tag: tag.name == "div" and ("crafting" in tag.get("id", "") or "crafting" in tag.get("class", [])))
                    if crafting_div:
                        img = crafting_div.find("img")
                        if img and img.has_attr("src"):
                            recipe_image_url = img["src"]

                # fallback2
                if not recipe_image_url:
                    img = soup.find("img")
                    if img and img.has_attr("src"):
                        recipe_image_url = img["src"]

                # url normalize
                if recipe_image_url and recipe_image_url.startswith("//"):
                    recipe_image_url = "https:" + recipe_image_url
                elif recipe_image_url and recipe_image_url.startswith("/"):
                    recipe_image_url = "https://minecraft.wiki" + recipe_image_url

        except Exception:
            recipe_image_url = None

    embed = discord.Embed(
        title=f"Crafting Recipe for {item.title()}",
        url=wiki_url,
        color=0x55a630,
        description=f"[View full page on Minecraft Wiki]({wiki_url})"
    )
    if recipe_image_url:
        embed.set_image(url=recipe_image_url)
    else:
        embed.set_footer(text="Recipe image not found, please check the wiki page link.")

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="mcadvancement", description="Get advancement info from Minecraft Wiki")
@app_commands.describe(name="Advancement name")
async def mcadvancement(interaction: discord.Interaction, name: str):
    search = name.replace(" ", "_")
    url = f"https://minecraft.wiki/w/{search}"
    embed = discord.Embed(
        title=f"🏆 Info on advancement {name.title()}",
        description=f"[View on wiki]({url})",
        color=0x55a630
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mcenchant", description="Get enchantment info from Minecraft Wiki")
@app_commands.describe(name="Enchantment name")
async def mcenchant(interaction: discord.Interaction, name: str):
    search = name.replace(" ", "_")
    url = f"https://minecraft.wiki/w/{search}"
    embed = discord.Embed(
        title=f"✨ Enchantment {name.title()} details",
        description=f"[View on wiki]({url})",
        color=0x55a630
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mcbiome", description="Get biome info from Minecraft Wiki")
@app_commands.describe(name="Biome name")
async def mcbiome(interaction: discord.Interaction, name: str):
    search = name.replace(" ", "_")
    url = f"https://minecraft.wiki/w/{search}"
    embed = discord.Embed(
        title=f"🌲 Biome {name.title()} info",
        description=f"[View on wiki]({url})",
        color=0x55a630
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mcstructure", description="Get structure info from Minecraft Wiki")
@app_commands.describe(name="Structure name")
async def mcstructure(interaction: discord.Interaction, name: str):
    search = name.replace(" ", "_")
    url = f"https://minecraft.wiki/w/{search}"
    embed = discord.Embed(
        title=f"🏛️ Structure {name.title()}",
        description=f"[View on wiki]({url})",
        color=0x55a630
    )
    await interaction.response.send_message(embed=embed)
# >mcplayer [username]
@bot.tree.command(name="mcplayer",description="Get Minecraft player info")
@app_commands.describe(username="Minecraft IGN")
async def mcplayer(interaction: discord.Interaction, username: str):
    try:
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{username}", headers=headers) as resp:
                if resp.status != 200:
                    await interaction.followup.send("❌ Could not find that player.")
                    return
                data = await resp.json()
                uuid = data["id"]
        head_url = f"https://minotar.net/helm/{uuid}/128.png"
        skin_url = f"https://visage.surgeplay.com/full/512/{uuid}.png"

        embed = discord.Embed(
            title=f"Minecraft Player: {username}",
            description=f"UUID: `{uuid}`",
            color=0x8B0000
        )
        embed.set_image(url=skin_url)
        embed.set_thumbnail(url=head_url)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{e}`")

#mcserverstatus
@bot.tree.command(name="mcserverstatus", description="Get the status of the VDSMP")
async def mcserverstatus(interaction: discord.Interaction):
    if interaction.guild_id not in ALLOWED_GUILD_IDS:
        await interaction.response.send_message(
            "❌ This command is not available in this server.",
            ephemeral=True
        )
        return
    await interaction.response.defer()
    try:
        server_ip = "vdsmp.mc.gg"

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mcsrvstat.us/2/{server_ip}") as resp:
                if resp.status != 200:
                    await interaction.response.send_message("❌ Error contacting the status API.")
                    return
                data = await resp.json()

        if not data.get("online"):
            await interaction.response.send_message("❌ The server is currently **offline**.")
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
            pass
        elif icon:
            embed.set_thumbnail(url=icon)

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error in mcserverstatus: `{e}`")

#wf baro
@bot.tree.command(name="wfbaro", description="Warframe Baro status")
async def wfbaro(interaction: discord.Interaction):
    await interaction.response.defer()

    async def fetch_json(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    data = await fetch_json("https://api.warframestat.us/pc/voidTrader")
    if data.get("active"):
        inventory = "\n".join([f"{item['item']} - {item['ducats']} Ducats, {item['credits']} Cr" for item in data["inventory"]])
        msg = f"**Baro Ki'Teer is at {data['location']} until {data['endString']}**\n\n{inventory}"
    else:
        msg = f"**Baro is not here right now.** Next visit: {data['startString']}"

    await interaction.followup.send(msg)

#wfnews
@bot.tree.command(name="wfnews", description="Warframe News")
async def wfnews(interaction: discord.Interaction):
    async def fetch_json(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    news = await fetch_json("https://api.warframestat.us/pc/news")
    items = [f"**{n['message']}**\n<{n['link']}>" for n in news[:5]]
    await interaction.response.send_message("\n\n".join(items))

#wf nightwave
@bot.tree.command(name="wfnightwave", description="Warframe Nightwave status")
async def wfnightwave(interaction: discord.Interaction):
    async def fetch_json(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()
    data = await fetch_json("https://api.warframestat.us/pc/nightwave")
    missions = [f"**{m['title']}** - {m['reputation']} Rep" for m in data.get("activeChallenges", [])]
    await interaction.response.send_message("**Nightwave Challenges:**\n" + "\n".join(missions))

#wf prices
@bot.tree.command(name="wfprice",description="Warframe prices from warframe.market")
async def wfprice(interaction: discord.Interaction, item: str):
    item_url = item.replace(" ", "_").lower()
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.warframe.market/v1/items/{item_url}/orders") as resp:
            if resp.status != 200:
                await interaction.response.send_message("❌ Item not found or API issue.")
                return
            data = await resp.json()
            sell_orders = [o for o in data["payload"]["orders"] if o["order_type"] == "sell" and o["user"]["status"] == "ingame"]
            if sell_orders:
                cheapest = sorted(sell_orders, key=lambda x: x["platinum"])[0]
                await interaction.response.send_message(f"💰 Cheapest in-game seller: {cheapest['platinum']}p ({cheapest['user']['ingame_name']})")
            else:
                await interaction.response.send_message("❌ No in-game sellers found.")
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