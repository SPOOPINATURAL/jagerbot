import logging
import discord
from discord.ext import commands, bridge
import aiohttp
import os
import pytz
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from discord import Option
from pytz.exceptions import UnknownTimeZoneError

from config import WEATHER_API_KEY, SUPPORTED_TZ, EXCHANGE_API_KEY
from utils.helpers import DataHelper, TimeHelper
from utils.embed_builder import EmbedBuilder
from views.info_pages import InfoPages

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class WeatherService:
    def __init__(self):
        self.api_key = WEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    async def get_weather(self, city: str, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}?q={city}&appid={self.api_key}&units=metric"
        return await DataHelper.fetch_json(url, session=session)

    @staticmethod
    def create_weather_embed(data: dict) -> discord.Embed:
        temp_c = round(data['main']['temp'], 1)
        temp_f = round(temp_c * 9 / 5 + 32, 1)

        wind_speed_ms = data['wind']['speed']
        wind_kmh = round(wind_speed_ms * 3.6, 1)
        wind_mph = round(wind_speed_ms * 2.237, 1)

        tz_offset = timedelta(seconds=data.get("timezone", 0))
        local_time = lambda ts: datetime.fromtimestamp(ts).replace(tzinfo=timezone.utc).astimezone(
            timezone(tz_offset))

        sunrise = local_time(data['sys']['sunrise']).strftime("%H:%M %p")
        sunset = local_time(data['sys']['sunset']).strftime("%H:%M %p")

        city = data['name']
        weather_desc = data['weather'][0]['description'].title()
        icon_url = f"http://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png"

        embed = EmbedBuilder.info(
            title=f"Weather in {city}",
            description=weather_desc,
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url=icon_url)
        embed.add_field(name="🌡 Temperature", value=f"{temp_c}°C / {temp_f}°F", inline=True)
        embed.add_field(name="💧 Humidity", value=f"{data['main']['humidity']}%", inline=True)
        embed.add_field(name="🌬 Wind Speed", value=f"{wind_kmh} km/h / {wind_mph} mph", inline=True)
        embed.add_field(name="🌅 Sunrise", value=sunrise, inline=True)
        embed.add_field(name="🌇 Sunset", value=sunset, inline=True)

        return embed

class CurrencyService:
    def __init__(self):
        self.base_url = "https://api.exchangerate.host/convert"
        self.api_key = EXCHANGE_API_KEY

    async def convert_currency(
            self,
            amount: float,
            from_currency: str,
            to_currency: str,
            session: aiohttp.ClientSession
    ) -> Optional[float]:
        try:
            url = (
                f"{self.base_url}?"
                f"from={from_currency.upper()}&"
                f"to={to_currency.upper()}&"
                f"amount={amount}"
            )

            if self.api_key:
                url += f"&access_key={self.api_key}"

            logger.info(f"CurrencyService: fetching URL: {url}")

            data = await DataHelper.fetch_json(url, session=session)
            if not data or not data.get("success", True):
                logger.warning(f"Currency API returned failure or no data: {data}")
                return None

            return data.get("result")

        except Exception as e:
            logger.error(f"Currency conversion error: {e}", exc_info=True)
            return None

class CoreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.weather_service = WeatherService()
        self.currency_service = CurrencyService()
        self.planes = bot.planes
        super().__init__()

    async def cog_load(self) -> None:
        logger.info("CoreCog loading: creating aiohttp ClientSession")
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def cog_unload(self) -> None:
        logger.info("CoreCog unloading: closing aiohttp ClientSession")
        if self.session and not self.session.closed:
            await self.session.close()

    @bridge.bridge_command(name='weather', description="Get the current weather in a city")
    async def weather(
        self,
        ctx: discord.ApplicationContext,
        city: str = Option(str, "Name of the city (e.g. London, Tokyo)")
    ):
        logger.info(f"weather command invoked with city={city}")

        if not self.session or self.session.closed:
            await ctx.respond("HTTP session is not ready. Try again later.", ephemeral=True)
            logger.error("weather command failed: session not ready")
            return

        await ctx.defer()
        try:
            weather_data = await self.weather_service.get_weather(city, self.session)
            if not weather_data:
                await ctx.followup.send(
                    f"❌ Could not find weather for `{city}`.",
                    ephemeral=True
                )
                return

            embed = self.weather_service.create_weather_embed(weather_data)
            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Weather command error: {e}", exc_info=True)
            try:
                await ctx.followup.send(
                    "An error occurred while fetching weather data.",
                    ephemeral=True
                )
            except Exception:
                logger.error("Failed to send followup message after weather error")

    @bridge.bridge_command(name="currency", description="Convert currency using exchangerate.host")
    async def currency(
        self,
        ctx: discord.ApplicationContext,
        amount: str = Option(float, "Amount to convert"),
        from_currency: str = Option(str, "Currency to convert from"),
        to_currency: str = Option(str, "Currency to convert to")
    ):
        logger.info(f"currency command invoked: {amount} {from_currency} -> {to_currency}")

        if not self.session or self.session.closed:
            await ctx.respond("HTTP session is not ready. Try again later.", ephemeral=True)
            logger.error("currency command failed: session not ready")
            return

        await ctx.defer()
        try:
            result = await self.currency_service.convert_currency(
                amount,
                from_currency,
                to_currency,
                self.session
            )

            if result is None:
                await ctx.followup.send(
                    "❌ Currency conversion failed.",
                    ephemeral=True
                )
                return

            await ctx.followup.send(
                f"💱 {amount} {from_currency.upper()} = {result:.2f} {to_currency.upper()}"
            )

        except Exception as e:
            logger.error(f"Currency conversion error: {e}", exc_info=True)
            try:
                await ctx.followup.send(
                    "❌ An error occurred during conversion.",
                    ephemeral=True
                )
            except Exception:
                logger.error("Failed to send followup message after currency error")

    @bridge.bridge_command(name="timezones", description="List supported timezones")
    async def timezones(self, ctx: discord.ApplicationContext):
        logger.info("timezones command invoked")

        try:
            if not SUPPORTED_TZ:
                await ctx.respond("No supported timezones configured.", ephemeral=True)
                logger.error("timezones command failed: SUPPORTED_TZ empty or None")
                return

            text = "\n".join([f"**{abbr}** → `{full}`" for abbr, full in SUPPORTED_TZ.items()])
            embed = discord.Embed(title="🕒 Supported Timezones", description=text, color=0x8B0000)
            await ctx.respond(embed=embed)

        except Exception as e:
            logger.error(f"timezones command error: {e}", exc_info=True)
            try:
                await ctx.respond("An error occurred while fetching timezones.", ephemeral=True)
            except Exception:
                logger.error("Failed to send error message after timezones command failure")

    @bridge.bridge_command(name="tzconvert", description="Convert time between timezones")
    async def tzconvert(
        self,
        ctx: discord.ApplicationContext,
        time: str = Option(str, "e.g. 14:00 or now"),
        from_tz: str = Option(str, "From timezone"),
        to_tz: str = Option(str, "To timezone")
    ):
        logger.info(f"tzconvert command invoked: {time} {from_tz} -> {to_tz}")

        await ctx.defer()

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

            await ctx.followup.send(
                f"🕒 `{input_dt.strftime('%Y-%m-%d %H:%M')}` in **{from_tz}** is "
                f"`{converted.strftime('%Y-%m-%d %H:%M')}` in **{to_tz}**"
            )

        except UnknownTimeZoneError:
            await ctx.followup.send(
                "❌ Invalid timezone specified.",
                ephemeral=True
            )
        except ValueError:
            await ctx.followup.send(
                "❌ Invalid time format. Use HH:MM or YYYY-MM-DD HH:MM",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Timezone conversion error: {e}", exc_info=True)
            await ctx.followup.send(
                "❌ An error occurred during conversion.",
                ephemeral=True
            )

    @bridge.bridge_command(name="credits", description="Credits for this bot")
    async def credits(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title="Bot Credits", description="Made by **SPOOPINATURAL**", color=0x8B0000)
        embed.set_thumbnail(url="https://i.imgur.com/BxmePJZ.png")
        embed.set_image(url="https://i.imgur.com/x6DzWEK.png")
        embed.set_footer(text="Thank you for using the bot!")

        embed.add_field(name="GitHub", value="[Github](https://github.com/SPOOPINATURAL)", inline=True)
        embed.add_field(name="Instagram", value="[Instagram](https://instagram.com/spoopi_natural)", inline=True)
        embed.add_field(name="Tumblr", value="[Tumblr](https://spoopi-natural.tumblr.com)", inline=True)
        embed.add_field(name="VGen", value="[VGen](https://vgen.co/SPOOPINATURAL)", inline=True)
        embed.add_field(name="Discord", value="spoopinatural", inline=True)

        await ctx.respond(embed=embed)

    @bridge.bridge_command(name="date", description="Get the current date and time")
    async def date(
        self,
        ctx: discord.ApplicationContext,
        tz: str = Option(str, "Timezone name or abbreviation (e.g., CST, PST, UTC)")
    ):
        if tz:
            tz_upper = tz.strip().upper()
            tz_name = SUPPORTED_TZ.get(tz_upper, tz)
        else:
            tz_name = "UTC"
            tz_upper = "UTC"

        try:
            zone = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            await ctx.respond("❌ Unknown timezone.", ephemeral=True)
            return

        now = datetime.now(zone)
        embed = discord.Embed(
            title="📅 Current Date & Time",
            description=f"{now.strftime('%A, %B %d, %Y – %I:%M %p')} ({tz_upper})",
            color=0x8B0000
        )
        await ctx.respond(embed=embed)

    @bridge.bridge_command(name="plane", description="Get a random WW1 plane")
    async def plane(self, ctx: discord.ApplicationContext):
        if not self.planes:
            await ctx.respond("No plane data loaded.")
            return

        plane = random.choice(self.planes)
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
        image_path_or_url = plane.get("image", "")
        files = []

        if image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://"):
            embed.set_image(url=image_path_or_url)
        else:
            image_path_or_url = image_path_or_url.replace("\\", "/")
            if os.path.exists(image_path_or_url):
                filename = os.path.basename(image_path_or_url)
                files.append(discord.File(image_path_or_url, filename=filename))
                embed.set_image(url=f"attachment://{filename}")
            await ctx.respond(embed=embed)

    @bridge.bridge_command(name="info", description="Command list")
    async def info(self, ctx: discord.ApplicationContext):
        guild_id = ctx.guild.id if ctx.guild else 0
        view = InfoPages(guild_id)
        try:
            response = await ctx.respond(embed=view.pages[0], view=view)
            view.message = await response.original_response()
        except Exception as e:
            logger.error(f"Info Pages error: {e}", exec_info=True)
            await ctx.respong("Info Pages Error", ephermeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(CoreCog(bot))
