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

async def perform_nickname_change(guild_id: int, target_user_id: int, bot_instance: commands.Bot):
    """
    Attempts to change the nickname of a target user on a specific guild.

    Args:
        guild_id: The ID of the guild.
        target_user_id: The ID of the user whose nickname is to be changed.
        bot_instance: The bot instance, used to get guild and member.

    Returns:
        A tuple (bool, str): (success, message_or_new_name)
    """
    print(f"Attempting perform_nickname_change for user {target_user_id} on guild {guild_id}")
    try:
        guild = bot_instance.get_guild(guild_id)
        if not guild:
            error_msg = f"Error: Server with ID {guild_id} not found. Check DISCORD_SERVER_ID environment variable."
            print(error_msg)
            return False, error_msg

        member = guild.get_member(target_user_id)
        if not member:
            error_msg = f"Error: User with ID {target_user_id} not found on server {guild.name}. Check DISCORD_USER_ID environment variable."
            print(error_msg)
            return False, error_msg

        new_name = await get_random_male_name() # Assumes get_random_male_name() is defined
        if not new_name:
            error_msg = "Failed to get a new name from API."
            print(error_msg)
            return False, error_msg

        await member.edit(nick=new_name)
        success_msg = f"Successfully changed nickname for {member.display_name} to {new_name} on server {guild.name}."
        print(success_msg)
        return True, new_name # Or success_msg if more detail needed by caller

    except discord.Forbidden:
        error_msg = f"Error: Bot does not have permission to change nickname for user {target_user_id} on server {guild_id}. Ensure 'Manage Nicknames' permission and role hierarchy."
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred during nickname change: {e}"
        print(error_msg)
        return False, error_msg

@tasks.loop(time=dt_time(hour=6, minute=1, tzinfo=dt_timezone.utc))
async def change_nickname_task():
    await bot.wait_until_ready()
    print("Scheduled daily nickname change task running...")
    # SERVER_ID and USER_ID are global, loaded from .env
    success, message = await perform_nickname_change(SERVER_ID, USER_ID, bot)
    if success:
        print(f"Daily nickname change successful for user {USER_ID}: new name {message}")
    else:
        print(f"Daily nickname change failed for user {USER_ID}: {message}")


@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user.name}')
    if not change_nickname_task.is_running():
        change_nickname_task.start()
    print("Daily name changer task started.")

    # Sync slash commands
    try:
        # Sync global commands.
        # For development, you might sync to a specific guild for instant updates:
        # guild_id = os.getenv('DISCORD_TEST_GUILD_ID') # Example for specific guild sync
        # if guild_id:
        #    synced = await bot.tree.sync(guild=discord.Object(id=int(guild_id)))
        #    print(f"Synced {len(synced)} slash command(s) to guild {guild_id}.")
        # else:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s) globally.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

@bot.tree.command(name="changename", description="Manually changes the configured user's nickname.")
async def changename_slash_command(interaction: discord.Interaction):
    """Manually triggers a nickname change for the configured user on the configured server."""

    # Permission Check
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("You do not have the required 'Manage Nicknames' permission to use this command.", ephemeral=True)
        return

    if not interaction.guild: # Should not happen for guild commands, but good check
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # Defer the response as perform_nickname_change involves API calls and might take a moment
    await interaction.response.defer(ephemeral=False) # ephemeral=False so others can see the outcome message

    # SERVER_ID and USER_ID are global, loaded from .env
    success, result_message = await perform_nickname_change(SERVER_ID, USER_ID, bot)

    if success:
        # 'result_message' here is the new name
        await interaction.followup.send(f"Successfully changed nickname for user ID {USER_ID} to **{result_message}**.")
    else:
        # 'result_message' here is the error message
        await interaction.followup.send(f"Failed to change nickname for user ID {USER_ID}. Reason: {result_message}")

if __name__ == '__main__':
    print("Bot is attempting to start...")
    print("Ensure DISCORD_BOT_TOKEN, DISCORD_SERVER_ID, and DISCORD_USER_ID environment variables are correctly set in your .env file or system environment.")
    bot.run(BOT_TOKEN)
