import discord
import os
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv

load_dotenv()

TEST_GUILD_ID = 989558855023362110  # Change to your test server's ID

class JagerBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.is_dev = os.getenv("BOT_ENV", "prod").lower() == "dev"

    async def setup_hook(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"cogs.{filename[:-3]}")
                self.logger.info(f"✅ Loaded cog: {filename}")

        if self.is_dev:
            test_guild = discord.Object(id=TEST_GUILD_ID)
            self.tree.clear_commands(guild=test_guild)
            await self.tree.sync(guild=test_guild)
            self.logger.info("🧹 Cleared and re-synced commands in test guild")
        else:
            await self.tree.sync()
            self.logger.info("✅ Synced slash commands globally")

    async def on_ready(self):
        self.logger.info(f"Ready :) as {self.user}")
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Everything"
            )
        )

        # ✅ Fetch and log what Discord actually sees
        guild = discord.Object(id=TEST_GUILD_ID) if self.is_dev else None
        commands = await self.tree.fetch_commands(guild=guild)
        print("Fetched commands from Discord:")
        for cmd in commands:
            print(f"- {cmd.name}")


intents = discord.Intents.default()
intents.message_content = True  # Needed if you use on_message, etc.

bot = JagerBot(command_prefix=">", intents=intents)

# You must point to your token in a `.env` file like: DISCORD_TOKEN=your_token_here
bot.run(os.getenv("DISCORD_TOKEN"))
