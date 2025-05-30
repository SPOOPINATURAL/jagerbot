import logging
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import pytz
import random
from datetime import datetime
from typing import Optional, Dict, Any
from pytz.exceptions import UnknownTimeZoneError

from config import WEATHER_API_KEY, SUPPORTED_TZ
from utils.helpers import DataHelper, TimeHelper
from utils.embed_builder import EmbedBuilder
from views.info_pages import InfoPages


logger = logging.getLogger(__name__)


class WeatherService:
    def __init__(self):
        self.api_key = WEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    async def get_weather(self, city: str, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}?q={city}&appid={self.api_key}&units=metric"
        return await DataHelper.fetch_json(url, session=session)

    def create_weather_embed(self, data: Dict[str, Any]) -> discord.Embed:
        temp_c = data["main"]["temp"]
        temp_f = round((temp_c * 9 / 5) + 32, 1)
        wind_mps = data["wind"]["speed"]
        wind_mph = round(wind_mps * 2.23694, 1)

        return EmbedBuilder.info(
            title=f"🌤 Weather in {data['name']}",
            fields=[
                ("Temperature", f"{temp_c}°C / {temp_f}°F", True),
                ("Condition", data["weather"][0]["description"].title(), True),
                ("Humidity", f"{data['main']['humidity']}%", True),
                ("Wind Speed", f"{wind_mps} m/s / {wind_mph} mph", True)
            ], color = 0x8B0000
        )


class CurrencyService:
    def __init__(self):
        self.base_url = "https://api.exchangerate.host/convert"

    async def convert_currency(
            self,
            amount: float,
            from_currency: str,
            to_currency: str,
            session: aiohttp.ClientSession
    ) -> Optional[float]:
        try:
            url = (f"{self.base_url}?"
                   f"from={from_currency.upper()}&"
                   f"to={to_currency.upper()}&"
                   f"amount={amount}")

            data = await DataHelper.fetch_json(url)
            if not data or not data.get("success"):
                return None

            return data.get("result")

        except Exception as e:
            logger.error(f"Currency conversion error: {e}")
            return None


class CoreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.weather_service = WeatherService()
        self.currency_service = CurrencyService()

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def cog_unload(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    @app_commands.command(name='weather', description="Get the current weather in a city")
    @app_commands.describe(city="Name of the city (e.g. London, Tokyo)")
    async def weather(self, interaction: discord.Interaction, city: str):
        await interaction.response.defer()

        try:
            weather_data = await self.weather_service.get_weather(city, self.session)
            if not weather_data:
                await interaction.followup.send(
                    f"❌ Could not find weather for `{city}`.",
                    ephemeral=True
                )
                return

            embed = self.weather_service.create_weather_embed(weather_data)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Weather command error: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching weather data.",
                ephemeral=True
            )

    @app_commands.command(name="tzconvert", description="Convert time between timezones")
    @app_commands.describe(time="e.g. 14:00 or now", from_tz="From timezone", to_tz="To timezone")
    async def tzconvert(
            self,
            interaction: discord.Interaction,
            time: str,
            from_tz: str,
            to_tz: str
    ):
        await interaction.response.defer()

        try:
            from_zone = pytz.timezone(TimeHelper.normalize_tz(from_tz))
            to_zone = pytz.timezone(TimeHelper.normalize_tz(to_tz))

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

        except UnknownTimeZoneError:
            await interaction.followup.send(
                "❌ Invalid timezone specified.",
                ephemeral=True
            )
        except ValueError:
            await interaction.followup.send(
                "❌ Invalid time format. Use HH:MM or YYYY-MM-DD HH:MM",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Timezone conversion error: {e}")
            await interaction.followup.send(
                "❌ An error occurred during conversion.",
                ephemeral=True
            )

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
    async def currency(
            self,
            interaction: discord.Interaction,
            amount: float,
            from_currency: str,
            to_currency: str
    ):
        await interaction.response.defer()

        try:
            result = await self.currency_service.convert_currency(
                amount,
                from_currency,
                to_currency,
                self.session
            )

            if result is None:
                await interaction.followup.send(
                    "❌ Currency conversion failed.",
                    ephemeral=True
                )
                return

            await interaction.followup.send(
                f"💱 {amount} {from_currency.upper()} = {result:.2f} {to_currency.upper()}"
            )

        except Exception as e:
            logger.error(f"Currency conversion error: {e}")
            await interaction.followup.send(
                "❌ An error occurred during conversion.",
                ephemeral=True
            )

    @app_commands.command(name="info", description="Command list")
    async def info(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id if interaction.guild else 0
        view = InfoPages(guild_id)
        view.message = await interaction.response.send_message(embed=view.pages[0], view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(CoreCog(bot))
