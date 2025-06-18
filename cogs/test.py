import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        try:
            self.test_group = bot.create_group("test", "Test command group")
            logger.info("✅ Created /test command group")
        except Exception as e:
            logger.exception("❌ Failed to create /test command group")

        try:
            @self.test_group.command(name="hello", description="Say hello!")
            async def hello(ctx: discord.ApplicationContext):
                await ctx.respond(f"Hallo {ctx.user.mention} :)")
            logger.info("✅ Registered /test hello command")
        except Exception as e:
            logger.exception("❌ Failed to register /test hello command")

        try:
            bot.tree.add_command(self.test_group)
            logger.info("✅ Added /test group to command tree")
        except Exception as e:
            logger.exception("❌ Failed to add /test group to tree")

async def setup(bot):
    await bot.add_cog(TestCog(bot))