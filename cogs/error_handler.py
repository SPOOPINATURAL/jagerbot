import os
import psutil
import aiohttp
from discord.ext import commands
from discord import Interaction
from discord.app_commands import AppCommandError, CommandOnCooldown, MissingPermissions, BotMissingPermissions, CommandNotFound, TransformerError
from discord.errors import NotFound

class ErrorHandlerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.error(self.on_app_command_error)
        super().__init__()

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def cog_unload(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Command not recognized. Use `/info` to see available cogs.")
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

    async def on_app_command_error(self, interaction: Interaction, error: AppCommandError):
        try:
            if isinstance(error, CommandOnCooldown):
                msg = f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f} seconds."
            elif isinstance(error, MissingPermissions):
                msg = "🚫 You don't have permission to use this command."
            elif isinstance(error, BotMissingPermissions):
                msg = "⚠️ I’m missing the required permissions to do that."
            elif isinstance(error, CommandNotFound):
                msg = "❌ Slash command not found."
            elif isinstance(error, TransformerError):
                msg = "❌ Invalid input. Please check your command options."
            else:
                print(f"Unhandled slash command error: {error}")
                msg = "❌ An unexpected error occurred."

            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)

        except NotFound:
            pass

    def check_for_multiple_instances(self):
        current_pid = os.getpid()
        count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'python' in proc.info['name'].lower() and 'your_bot_script_name.py' in ' '.join(proc.info['cmdline']):
                count += 1
        if count > 1:
            print("Warning: Multiple instances of bot detected!")
            return True
        return False

    if check_for_multiple_instances():
        exit(1)

async def setup(bot):
    await bot.add_cog(ErrorHandlerCog(bot))
