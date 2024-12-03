import discord
from discord.ext import commands
from discord import app_commands
from transformers import pipeline
import re

# Define intents including message content and voice states
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Hugging Face AI Detection using a better model
model_name = "roberta-large-openai-detector"  # Advanced Hugging Face model
classifier = pipeline("zero-shot-classification", model=model_name)
categories = ["AI", "Human"]

conversation_map = {}

# Function to strip emojis from text
def strip_emojis(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & pictographs
        "\U0001F680-\U0001F6FF"  # Transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # Flags
        "\U00002500-\U00002BEF"  # Chinese char
        "\U00002702-\U000027B0"
        "\U00002700-\U000027BF"
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002600-\U000026FF"  # Miscellaneous Symbols
        "\U00002B50-\U00002BFF"  # Stars
        "\U0001F680-\U0001F6FF"  # Transport and map symbols
        "\u200d"  # Zero-width joiner
        "\u2640-\u2642"  # Gender symbols
        "\u2600-\u2B55"  # Miscellaneous symbols
        "\u23cf"  # Eject symbol
        "\u23e9"  # fast forward
        "\u231a"  # watch
        "\ufe0f"  # Dingbats
        "\u3030"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r"", text)

@bot.event
async def on_ready():
    activity = discord.Streaming(name="I Silence AI", url="https://stellarium-web.org")
    await bot.change_presence(status=discord.Status.idle, activity=activity)
    print(f"Bot is ready. Logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print("Slash commands synced successfully!")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_message(message):
    # Ignore messages from bots
    if message.author.bot:
        return

    # Handle DM replies
    if isinstance(message.channel, discord.DMChannel) and message.author.id in conversation_map:
        original_sender_id = conversation_map[message.author.id]
        original_sender = await bot.fetch_user(original_sender_id)
        if original_sender:
            if message.content:
                await original_sender.send(f"{message.author.name} replied: {message.content}")
            if message.attachments:
                attachment_urls = "\n".join(att.url for att in message.attachments)
                await original_sender.send(
                    f"{message.author.name} sent an attachment: \n{attachment_urls}"
                )
        return

    # Strip emojis and standardize text
    text_without_emojis = strip_emojis(message.content).lower()

    # Skip very short messages or pure numbers
    if len(text_without_emojis) < 10 or text_without_emojis.isdigit():
        await bot.process_commands(message)
        return

    try:
        # Classify the message using Hugging Face's model
        result = classifier(text_without_emojis, candidate_labels=categories)

        # Adjust threshold for more accurate detection
        if result['labels'][0] == 'AI' and result['scores'][0] > 0.55:  # Higher threshold
            try:
                # Delete the message if it's AI-generated
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, Your Message has now been... TERMINATED! https://tenor.com/view/tyrminator-tyr-bot-redeye-gif-22046800"
                )
            except discord.DiscordException as e:
                print(f"Error deleting message: {e}")
    except Exception as e:
        print(f"Error during AI detection: {e}")

    # Process other commands
    await bot.process_commands(message)

@bot.tree.command(name="send", description="Send a message using the bot")
@app_commands.describe(channel="The channel to send the message in", message="The message to send")
async def send_message(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.response.send_message(
            "I don't have permission to send messages in that channel.", ephemeral=True
        )
        return
    try:
        await channel.send(message)
        await interaction.response.send_message(f"Message sent to {channel.mention}.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to send the message: {e}", ephemeral=True)

@bot.tree.command(name="dmsend", description="Send a DM to a user using the bot")
@app_commands.describe(user="The user to send the DM to", message="The message to send in the DM")
async def dm_send(interaction: discord.Interaction, user: discord.User, message: str):
    try:
        await user.send(message)
        conversation_map[user.id] = interaction.user.id
        await interaction.response.send_message(f"DM sent to {user.name}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("They might DMs disabled.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to send the DM: {e}", ephemeral=True)

bot.run("Bot-Token")
