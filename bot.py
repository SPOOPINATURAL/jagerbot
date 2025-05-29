import discord
import os
from discord.ext import commands
import logging

class JagerBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    async def setup_hook(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        await self.tree.sync()
        self.logger.info("✅ Synced slash commands")

    async def on_ready(self):
        self.logger.info(f"Ready :) as {self.user}")
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.watching, name="Everything")
        )
        commands = [command.name for command in self.tree.get_commands()]
        self.logger.info(f"Registered slash commands: {commands}")