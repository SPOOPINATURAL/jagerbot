import discord

class AlertModal(discord.ui.Modal, title="Set a New Alert"):
    def __init__(self, on_submit):
        super().__init__()
        self.on_submit_callback = on_submit
        self.event = discord.ui.TextInput(label="Event", placeholder="Meeting, homework, etc.", required=True)
        self.time = discord.ui.TextInput(label="Time", placeholder="e.g., 15:00, tomorrow at noon", required=True)
        self.recurring = discord.ui.TextInput(label="Recurring", placeholder="(Optional) e.g., 1h, 30m", required=False)
        self.add_item(self.event)
        self.add_item(self.time)
        self.add_item(self.recurring)

    async def on_submit(self, interaction: discord.Interaction):
        await self.on_submit_callback(
            interaction,
            self.event.value,
            self.time.value,
            self.recurring.value
        )
