import asyncio
import logging
from bot import JagerBot
import config
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
    async with bot:
        try:
            logger.info("Starting bot...")
            await bot.start(config.DISCORD_TOKEN)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            await bot.close()
            logger.info("Bot closed cleanly.")
if __name__ == "__main__":
    asyncio.run(main())
