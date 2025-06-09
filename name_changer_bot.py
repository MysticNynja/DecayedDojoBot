import discord
from discord.ext import tasks, commands
import asyncio
import aiohttp # Added
import random # Keep for now, might remove if no other random choice needed

# Configuration - Replace with your actual values
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'  # User will replace this
SERVER_ID = 548624354213363733
USER_ID = 133358760453210112

# MALE_NAMES list is now removed

intents = discord.Intents.default()
intents.members = True # Required to change nicknames
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


@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user.name}')
    change_nickname_task.start()

@tasks.loop(hours=24) # Run once a day
async def change_nickname_task():
    await bot.wait_until_ready() # Ensure bot is fully connected
    print("Attempting to change nickname using API...")
    try:
        guild = bot.get_guild(SERVER_ID)
        if not guild:
            print(f"Error: Server with ID {SERVER_ID} not found.")
            return

        member = guild.get_member(USER_ID)
        if not member:
            print(f"Error: User with ID {USER_ID} not found on server {guild.name}.")
            return

        new_name = await get_random_male_name()
        if not new_name:
            print("Failed to get a new name from API. Skipping nickname change for this cycle.")
            # Optionally, you could implement a fallback to a short static list here
            # or retry after a delay, but for now, we'll just skip.
            return

        await member.edit(nick=new_name)
        print(f"Successfully changed nickname for {member.display_name} to {new_name} on server {guild.name} using API.")

    except discord.Forbidden:
        print(f"Error: Bot does not have permission to change nickname for user {USER_ID} on server {SERVER_ID}.")
        print("Please ensure the bot has the 'Manage Nicknames' permission and its role is higher than the target user's role.")
    except Exception as e:
        print(f"An unexpected error occurred in change_nickname_task: {e}")

@change_nickname_task.before_loop
async def before_change_nickname_task():
    print("Change nickname task is waiting for the bot to be ready before the first run.")
    await bot.wait_until_ready()

# bot.run(BOT_TOKEN)
# print("Bot is ready to be run. Please replace 'YOUR_BOT_TOKEN_HERE' with your actual bot token and uncomment the bot.run() line.")
