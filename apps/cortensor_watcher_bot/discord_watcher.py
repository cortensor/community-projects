import discord
import json
import asyncio
from datetime import datetime
from config import DISCORD_TOKEN, DISCORD_CHANNEL_ID, LATEST_DEVLOG_FILE

class DiscordWatcher(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.message_content = True  # Required to read message content
        super().__init__(intents=intents)
        self.last_message_id = None

    async def on_ready(self):
        print(f'✅ Logged in as {self.user} (Bot Mode Active)')
        print('🚀 Cortensor Watcher Bot is now running...')
        await self.start_monitoring()

    async def start_monitoring(self):
        """Check and confirm access to the target channel"""
        await self.wait_until_ready()
        channel = self.get_channel(DISCORD_CHANNEL_ID)

        if channel is None:
            print(f'❌ Channel with ID {DISCORD_CHANNEL_ID} not found.')
            return
        print(f'👀 Monitoring channel: #{channel.name} ({channel.id})')

    async def on_message(self, message: discord.Message):
        """Trigger when a new message appears in the channel"""
        # Ignore messages sent by the bot itself
        if message.author == self.user:
            return

        # Only process messages from the target channel
        if message.channel.id != DISCORD_CHANNEL_ID:
            return

        await self.process_new_message(message)

    async def process_new_message(self, message: discord.Message):
        """Process and store a new devlog message"""
        print(f'📨 New message detected: {message.id} from {message.author}')

        message_data = {
            'id': message.id,
            'content': message.content,
            'author': str(message.author),
            'timestamp': message.created_at.isoformat(),
            'channel_id': message.channel.id,
            'channel_name': message.channel.name,
            'processed': False
        }

        output_data = {
            'last_message_id': message.id,
            'last_updated': datetime.now().isoformat(),
            'message': message_data
        }

        # Write safely to JSON file
        try:
            with open(LATEST_DEVLOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f'💾 Message saved to {LATEST_DEVLOG_FILE}')
        except Exception as e:
            print(f'❌ Failed to save message: {e}')

    def run_bot(self):
        """Start the bot using the Discord Bot Token"""
        print('🚀 Starting Discord Watcher Bot...')
        super().run(DISCORD_TOKEN)

if __name__ == "__main__":
    watcher = DiscordWatcher()
    watcher.run_bot()
