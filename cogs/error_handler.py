import discord
from discord.ext import commands
from discord import app_commands

class ErrorHandlerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.error(self.on_app_command_error)

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

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
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

async def setup(bot):
    await bot.add_cog(ErrorHandlerCog(bot))
