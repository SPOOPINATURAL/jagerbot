import asyncio
import logging
from bot import JagerBot
import config
import os
import discord
from discord.ext import commands
from utils.setup import load_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_bot() -> JagerBot:
    import discord

    bot = JagerBot(
        command_prefix="$",
        help_command=None,
        intents=discord.Intents.all()
    )
    return bot
async def main():
    logger.info("main() is running")
    data = load_data()
    logger.info("Loaded data from JSON.")

    bot = create_bot()
    bot.planes = data.get("planes", [])
    bot.alerts = data.get("alerts", {})
    bot.user_scores = data.get("trivia_scores", {})
    
    @bot.event
    async def on_application_command_error(ctx, error):
        import traceback
        logger.error(f"Slash command error: {error}")
        logger.error(traceback.format_exc())
        await ctx.respond(f"Error: {error}", ephemeral=True)
    
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"Loaded extension: cogs.{filename[:-3]}")
            except Exception as e:
                logger.error(f"Failed to load extension cogs.{filename[:-3]}: {e}")

    @bot.event
    async def on_application_command_error(ctx, error):
        import traceback
        logger.error(f"Slash command error: {error}")
        logger.error(traceback.format_exc())
        await ctx.respond(f"Error: {error}", ephemeral=True)

    await bot.login(config.DISCORD_TOKEN)
    await bot.connect()

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands after connect.")
    except Exception as e:
        logger.error(f"Error syncing commands after connect: {e}")

    await bot.wait_until_close()
if __name__ == "__main__":
    asyncio.run(main())
