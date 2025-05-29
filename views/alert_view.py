import discord

class AlertItemView(discord.ui.View):
    def __init__(self, cog, alert, alert_index, on_cancel, on_snooze):
        super().__init__(timeout=None)
        self.alert = alert
        self.cog = cog
        self.alert_index = alert_index
        self.on_cancel = on_cancel
        self.on_snooze = on_snooze

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.on_cancel(interaction, self.alert_index)

    @discord.ui.button(label="Snooze 10m", style=discord.ButtonStyle.secondary)
    async def snooze(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.on_snooze(interaction, self.alert_index)
