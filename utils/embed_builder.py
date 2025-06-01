import discord

class EmbedBuilder:
    @staticmethod
    def error(message: str) -> discord.Embed:
        return discord.Embed(description=f"❌ {message}", color=0xff0000)

    @staticmethod
    def success(message: str, title: str = None) -> discord.Embed:
        embed = discord.Embed(description=f"✅ {message}", color=0x00ff00)
        if title:
            embed.title = title
        return embed

    @staticmethod
    def info(title: str, description: str, color: int = 0x3498db) -> discord.Embed:
        return discord.Embed(title=title, description=description, color=color)
