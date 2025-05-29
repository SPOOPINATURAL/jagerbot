import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import pytz
import random
from datetime import datetime
from pytz.exceptions import UnknownTimeZoneError
from config import WEATHER_API_KEY, SUPPORTED_TZ
from utils.helpers import normalize_tz
from views.info_pages import InfoPages


class CoreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='weather', description="Get the current weather in a city")
    @app_commands.describe(city="Name of the city (e.g. London, Tokyo)")
    async def weather(self, interaction: discord.Interaction, city: str):
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
                humidity = data["main"]["humidity"]
                wind_mps = data["wind"]["speed"]
                wind_mph = round(wind_mps * 2.23694, 1)

                embed = discord.Embed(title=f"🌤 Weather in {name}", color=0x8B0000)
                embed.add_field(name="Temperature", value=f"{temp_c}°C / {temp_f}°F", inline=True)
                embed.add_field(name="Condition", value=desc, inline=True)
                embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
                embed.add_field(name="Wind Speed", value=f"{wind_mps} m/s / {wind_mph} mph", inline=True)

                await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tzconvert", description="Convert time between timezones")
    @app_commands.describe(time="e.g. 14:00 or now", from_tz="From timezone", to_tz="To timezone")
    async def tzconvert(self, interaction: discord.Interaction, time: str, from_tz: str, to_tz: str):
        await interaction.response.defer()
        try:
            from_tz = normalize_tz(from_tz)
            to_tz = normalize_tz(to_tz)

            from_zone = pytz.timezone(from_tz)
            to_zone = pytz.timezone(to_tz)

            if time.lower() == "now":
                input_dt = datetime.now(from_zone)
            else:
                try:
                    native_dt = datetime.strptime(time, "%H:%M")
                    today = datetime.now().date()
                    native_dt = datetime.combine(today, native_dt.time())
                except ValueError:
                    native_dt = datetime.strptime(time, "%Y-%m-%d %H:%M")

                input_dt = from_zone.localize(native_dt)

            converted = input_dt.astimezone(to_zone)

            await interaction.followup.send(
                f"🕒 `{input_dt.strftime('%Y-%m-%d %H:%M')}` in **{from_tz}** is "
                f"`{converted.strftime('%Y-%m-%d %H:%M')}` in **{to_tz}**"
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error: {e}", ephemeral=True)

    @app_commands.command(name="timezones", description="List supported timezones")
    async def timezones(self, interaction: discord.Interaction):
        text = "\n".join([f"**{abbr}** → `{full}`" for abbr, full in SUPPORTED_TZ.items()])
        embed = discord.Embed(title="🕒 Supported Timezones", description=text, color=0x8B0000)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="credits", description="Credits for this bot")
    async def credits(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Bot Credits", description="Made by **SPOOPINATURAL**", color=0x8B0000)
        embed.set_thumbnail(url="https://i.imgur.com/BxmePJZ.png")
        embed.set_image(url="https://i.imgur.com/x6DzWEK.png")
        embed.set_footer(text="Thank you for using the bot!")

        embed.add_field(name="GitHub", value="[Github](https://github.com/SPOOPINATURAL)", inline=True)
        embed.add_field(name="Instagram", value="[Instagram](https://instagram.com/spoopi_natural)", inline=True)
        embed.add_field(name="Tumblr", value="[Tumblr](https://spoopi-natural.tumblr.com)", inline=True)
        embed.add_field(name="VGen", value="[VGen](https://vgen.co/SPOOPINATURAL)", inline=True)
        embed.add_field(name="Discord", value="spoopinatural", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="date", description="Get the current date and time")
    @app_commands.describe(tz="Timezone name (optional)")
    async def date(self, interaction: discord.Interaction, tz: str = None):
        try:
            zone = pytz.timezone(tz) if tz else pytz.UTC
        except pytz.UnknownTimeZoneError:
            await interaction.response.send_message("❌ Unknown timezone.", ephemeral=True)
            return

        now = datetime.now(zone)
        embed = discord.Embed(
            title="📅 Current Date & Time",
            description=f"{now.strftime('%A, %B %d, %Y – %I:%M %p')} ({tz or 'UTC'})",
            color=0x8B0000
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="plane", description="Get a random WW1 plane")
    async def plane(self, interaction: discord.Interaction):
        planes = self.bot.planes or []
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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="currency", description="Convert currency using exchangerate.host")
    @app_commands.describe(amount="Amount to convert", from_currency="Currency to convert from", to_currency="Currency to convert to")
    async def currency(self, interaction: discord.Interaction, amount: float, from_currency: str, to_currency: str):
        """Convert currency using exchangerate.host"""
        url = f"https://api.exchangerate.host/convert?from={from_currency.upper()}&to={to_currency.upper()}&amount={amount}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await interaction.response.send_message("❌ Failed to fetch exchange rate.", ephemeral=True)
                    return
                data = await resp.json()
                if not data.get("success"):
                    await interaction.response.send_message("❌ Conversion failed.", ephemeral=True)
                    return
                result = data.get("result")
                await interaction.response.send_message(
                    f"💱 {amount} {from_currency.upper()} = {result:.2f} {to_currency.upper()}")

    @app_commands.command(name="info", description="Command list")
    async def info(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id if interaction.guild else 0
        view = InfoPages(guild_id)
        view.message = await interaction.response.send_message(embed=view.pages[0], view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(CoreCog(bot))
