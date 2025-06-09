import discord
from discord.ext import tasks, commands
import asyncio
import aiohttp
import os
import sys
from dotenv import load_dotenv # New import
from datetime import time as dt_time, timezone as dt_timezone # For specific time scheduling

# Load environment variables from .env file at the very start
load_dotenv()

# Configuration from environment variables
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SERVER_ID_STR = os.getenv('DISCORD_SERVER_ID')
USER_ID_STR = os.getenv('DISCORD_USER_ID')

# Validate configuration
if not BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)
if not SERVER_ID_STR:
    print("Error: DISCORD_SERVER_ID environment variable not set.", file=sys.stderr)
    sys.exit(1)
if not USER_ID_STR:
    print("Error: DISCORD_USER_ID environment variable not set.", file=sys.stderr)
    sys.exit(1)

try:
    SERVER_ID = int(SERVER_ID_STR)
except ValueError:
    print("Error: DISCORD_SERVER_ID environment variable is not a valid integer.", file=sys.stderr)
    sys.exit(1)

try:
    USER_ID = int(USER_ID_STR)
except ValueError:
    print("Error: DISCORD_USER_ID environment variable is not a valid integer.", file=sys.stderr)
    sys.exit(1)

intents = discord.Intents.default()
intents.members = True # Required to change nicknames
intents.message_content = True # Enable message content intent
bot = commands.Bot(command_prefix="!", intents=intents)

async def get_random_male_name():
    """Fetches a random male first name from the randomuser.me API."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://randomuser.me/api/?gender=male&inc=name') as response:
                response.raise_for_status() # Raise an exception for HTTP errors
                data = await response.json()
                if data['results'] and data['results'][0]['name'] and data['results'][0]['name']['first']:
                    return data['results'][0]['name']['first']
                else:
                    print("Error: Could not parse name from API response or results are empty.")
                    return None # Or a default fallback name
        except aiohttp.ClientError as e:
            print(f"Error fetching name from API: {e}")
            return None # Or a default fallback name
        except Exception as e:
            print(f"An unexpected error occurred while fetching name: {e}")
            return None


@tasks.loop(minutes=2) # Adjust interval as needed
async def check_twitch_live_status_task():
    await bot.wait_until_ready() # Ensure bot is fully connected
    print("Attempting daily nickname change (scheduled)...")
@tasks.loop(time=dt_time(hour=6, minute=1, tzinfo=dt_timezone.utc))
async def change_nickname_task():
    await bot.wait_until_ready() # Ensure bot is fully connected
    print("Attempting daily nickname change (scheduled)...")
    try:
        guild = bot.get_guild(SERVER_ID)
        if not guild:
            print(f"Error: Server with ID {SERVER_ID} not found. Check DISCORD_SERVER_ID environment variable.")
            return

        member = guild.get_member(USER_ID)
        if not member:
            print(f"Error: User with ID {USER_ID} not found on server {guild.name}. Check DISCORD_USER_ID environment variable.")
            return

        new_name = await get_random_male_name()
        if not new_name:
            print("Failed to get a new name from API. Skipping nickname change for this cycle.")
            return

        await member.edit(nick=new_name)
        print(f"Successfully changed nickname for {member.display_name} to {new_name} on server {guild.name} using API.")

    except discord.Forbidden:
        print(f"Error: Bot does not have permission to change nickname for user {USER_ID} on server {SERVER_ID}.")
        print("Please ensure the bot has the 'Manage Nicknames' permission and its role is higher than the target user's role.")
    except Exception as e:
        print(f"An unexpected error occurred in change_nickname_task: {e}")


@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user.name}')
    if not change_nickname_task.is_running():
        change_nickname_task.start()
    # Removed Twitch task startup
    print("Daily name changer task started.")


if __name__ == '__main__':
    print("Bot is attempting to start...")
    print("Ensure DISCORD_BOT_TOKEN, DISCORD_SERVER_ID, and DISCORD_USER_ID environment variables are correctly set in your .env file or system environment.")
    bot.run(BOT_TOKEN)
