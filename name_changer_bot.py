import discord
from discord.ext import tasks, commands
import asyncio
import aiohttp
import os
import sys
import time
import json
from dotenv import load_dotenv # New import

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

# Twitch Configuration from environment variables
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

# Validate Twitch configuration
if not TWITCH_CLIENT_ID:
    print("Error: TWITCH_CLIENT_ID environment variable not set.", file=sys.stderr)
    sys.exit(1)
if not TWITCH_CLIENT_SECRET:
    print("Error: TWITCH_CLIENT_SECRET environment variable not set.", file=sys.stderr)
    sys.exit(1)

# Twitch App Access Token storage
twitch_access_token = None
twitch_token_expires_at = 0 # Stores Unix timestamp of expiry

TWITCH_FOLLOWS_FILE = 'twitch_follows.json'

# --- Twitch Follows Persistence Functions ---
def load_twitch_follows():
    """Loads followed Twitch channels from the JSON file."""
    if not os.path.exists(TWITCH_FOLLOWS_FILE):
        return {} # { "channel_login": { "last_status": "offline", "discord_channel_id": 123 } }
    try:
        with open(TWITCH_FOLLOWS_FILE, 'r') as f:
            data = json.load(f)
            # Basic validation for expected structure (dict of dicts)
            if not isinstance(data, dict) or not all(isinstance(v, dict) for v in data.values()):
                print(f"Warning: Data in {TWITCH_FOLLOWS_FILE} is not in the expected format. Resetting to empty.")
                return {}
            return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {TWITCH_FOLLOWS_FILE}: {e}. Returning empty list.")
        return {}

def save_twitch_follows(data):
    """Saves followed Twitch channels to the JSON file."""
    try:
        with open(TWITCH_FOLLOWS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving {TWITCH_FOLLOWS_FILE}: {e}")

# Load followed Twitch channels at startup
followed_twitch_channels = load_twitch_follows()
# Example: followed_twitch_channels = {"asmongold": {"last_status": "offline", "discord_channel_id": 123456789012345678}}
# save_twitch_follows(followed_twitch_channels) # For initial file creation if needed, or after modification

intents = discord.Intents.default()
intents.members = True # Required to change nicknames
bot = commands.Bot(command_prefix="!", intents=intents)

async def get_twitch_app_access_token():
    """
    Obtains a new Twitch App Access Token if the current one is invalid or expired.
    Uses TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET from environment variables.
    Returns the access token string or None if an error occurs.
    """
    global twitch_access_token, twitch_token_expires_at

    # Check if current token is still valid (with a small buffer, e.g., 60 seconds)
    if twitch_access_token and twitch_token_expires_at > (time.time() + 60):
        # print("Reusing existing Twitch token.")
        return twitch_access_token

    print("Requesting new Twitch App Access Token...")
    token_url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(token_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                if 'access_token' in data and 'expires_in' in data:
                    twitch_access_token = data['access_token']
                    # Calculate expiry time (expires_in is in seconds)
                    twitch_token_expires_at = time.time() + data['expires_in']
                    print("Successfully obtained new Twitch App Access Token.")
                    return twitch_access_token
                else:
                    print(f"Error: Could not parse token or expiry from Twitch response: {data}")
                    return None
        except aiohttp.ClientError as e:
            print(f"Error requesting Twitch App Access Token: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while requesting Twitch App Access Token: {e}")
            return None

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
    await bot.wait_until_ready()

    if not followed_twitch_channels:
        return

    # print(f"Running Twitch status check for {len(followed_twitch_channels)} channel(s)...")
    token = await get_twitch_app_access_token()
    if not token:
        print("Failed to get Twitch token for polling task. Skipping this run.")
        return

    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }

    needs_save_to_file = False

    for twitch_login, details in followed_twitch_channels.items():
        user_id = details.get("user_id")
        if not user_id:
            continue

        stream_url = f"https://api.twitch.tv/helix/streams?user_id={user_id}"
        current_stream_data = None
        is_currently_live = False

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(stream_url, headers=headers) as response:
                    if response.status == 429:
                        print(f"Rate limited by Twitch API when checking {twitch_login}. Will retry later.")
                        await asyncio.sleep(60)
                        continue

                    response.raise_for_status()
                    api_data = await response.json()

                    if api_data['data']:
                        current_stream_data = api_data['data'][0]
                        is_currently_live = True

            except aiohttp.ClientResponseError as e:
                print(f"Twitch API HTTP Error for {twitch_login} ({user_id}): {e.status} - {e.message}")
                continue
            except aiohttp.ClientError as e:
                print(f"Twitch API ClientError for {twitch_login} ({user_id}): {e}")
                continue
            except json.JSONDecodeError as e:
                print(f"Error decoding Twitch API JSON response for {twitch_login} ({user_id}): {e}")
                continue
            except Exception as e:
                print(f"An unexpected error occurred while checking Twitch status for {twitch_login} ({user_id}): {e}")
                continue

        last_live_status = details.get('last_live_status', False)
        discord_channel_id = details.get('discord_channel_id')
        streamer_display_name = details.get('display_name', twitch_login)

        notification_channel = bot.get_channel(discord_channel_id) if discord_channel_id else None
        if not notification_channel:
            if is_currently_live != last_live_status:
                 details['last_live_status'] = is_currently_live
                 needs_save_to_file = True
            if is_currently_live and current_stream_data:
                details['last_stream_id'] = current_stream_data.get('id')
                details['last_game_name'] = current_stream_data.get('game_name')
                needs_save_to_file = True
            elif not is_currently_live:
                details['last_stream_id'] = None
                details['last_game_name'] = None
                needs_save_to_file = True
            continue

        if is_currently_live:
            stream_id = current_stream_data.get('id')
            game_name = current_stream_data.get('game_name', 'N/A')
            stream_title = current_stream_data.get('title', 'No title')
            thumbnail_url = current_stream_data.get('thumbnail_url', '').replace('{width}', '640').replace('{height}', '360')

            if not last_live_status:
                print(f"{streamer_display_name} went LIVE!")
                embed = discord.Embed(
                    title=f":red_circle: LIVE: {streamer_display_name} is now streaming!",
                    description=f"**{stream_title}**\nPlaying: **{game_name}**",
                    url=f"https://twitch.tv/{twitch_login}",
                    color=discord.Color.purple()
                )
                if thumbnail_url:
                    embed.set_image(url=f"{thumbnail_url}?t={int(time.time())}")
                embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else discord.Embed.Empty)
                embed.add_field(name="Watch Now", value=f"[twitch.tv/{twitch_login}](https://twitch.tv/{twitch_login})")
                embed.set_footer(text=f"Twitch Notification | {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
                try:
                    await notification_channel.send(embed=embed)
                except discord.Forbidden:
                    print(f"Missing permissions to send message in {notification_channel.name} ({notification_channel.id}) for {twitch_login}")
                except Exception as e:
                    print(f"Error sending live notification for {twitch_login}: {e}")

                details['last_live_status'] = True
                details['last_stream_id'] = stream_id
                details['last_game_name'] = game_name
                needs_save_to_file = True

            elif stream_id != details.get('last_stream_id'):
                print(f"{streamer_display_name} has a new stream ID. Still live. Game: {game_name}")
                if game_name != details.get('last_game_name'):
                    embed = discord.Embed(
                        title=f":video_game: Game Change: {streamer_display_name}",
                        description=f"Now playing: **{game_name}**\nTitle: *{stream_title}*",
                        url=f"https://twitch.tv/{twitch_login}",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text=f"Twitch Notification | {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
                    try:
                        await notification_channel.send(embed=embed)
                    except Exception as e:
                        print(f"Error sending game change notification for {twitch_login}: {e}")

                details['last_stream_id'] = stream_id
                details['last_game_name'] = game_name
                needs_save_to_file = True

            elif game_name != details.get('last_game_name'):
                print(f"{streamer_display_name} changed game to {game_name}")
                embed = discord.Embed(
                    title=f":video_game: Game Change: {streamer_display_name}",
                    description=f"Now playing: **{game_name}**\nTitle: *{stream_title}*",
                    url=f"https://twitch.tv/{twitch_login}",
                    color=discord.Color.blue()
                )
                embed.set_footer(text=f"Twitch Notification | {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
                try:
                    await notification_channel.send(embed=embed)
                except Exception as e:
                    print(f"Error sending game change notification for {twitch_login}: {e}")

                details['last_game_name'] = game_name
                needs_save_to_file = True

            if details.get('last_stream_id') != stream_id:
                details['last_stream_id'] = stream_id
                needs_save_to_file = True

        else:
            if last_live_status:
                print(f"{streamer_display_name} went OFFLINE.")
                details['last_live_status'] = False
                details['last_stream_id'] = None
                details['last_game_name'] = None
                needs_save_to_file = True

        await asyncio.sleep(1)

    if needs_save_to_file:
        save_twitch_follows(followed_twitch_channels)

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user.name}')
    if not change_nickname_task.is_running():
        change_nickname_task.start()
    if not check_twitch_live_status_task.is_running(): # Add this for the new task
        check_twitch_live_status_task.start()
    print("Daily name changer task and Twitch live status checker task started.")

@tasks.loop(hours=24) # Run once a day
async def change_nickname_task():
    await bot.wait_until_ready() # Ensure bot is fully connected
    print("Attempting to change nickname using API...")
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

@change_nickname_task.before_loop
async def before_change_nickname_task():
    print("Change nickname task is waiting for the bot to be ready before the first run.")
    await bot.wait_until_ready()

# --- Twitch User Info Helper ---
async def get_twitch_user_info(username: str):
    """Fetches user ID and display name for a given Twitch username."""
    token = await get_twitch_app_access_token()
    if not token:
        print("Failed to get Twitch token for get_twitch_user_info.")
        return None

    url = f"https://api.twitch.tv/helix/users?login={username.lower()}"
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                if data['data']:
                    user_data = data['data'][0]
                    return {
                        "id": user_data['id'],
                        "login": user_data['login'], # Store the canonical login name
                        "display_name": user_data['display_name']
                    }
                else:
                    return None # User not found
        except aiohttp.ClientError as e:
            print(f"Error fetching Twitch user info for {username}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in get_twitch_user_info for {username}: {e}")
            return None

# --- Discord Commands for Twitch Follows ---
@bot.command(name='followtwitch')
@commands.has_permissions(manage_guild=True)
async def follow_twitch(ctx, twitch_username: str, notification_channel: discord.TextChannel = None):
    """Follows a Twitch streamer to get live notifications.
    Usage: !followtwitch <twitch_username> [#discord_channel]
    If #discord_channel is not provided, notifications will be sent to the current channel.
    """
    if not notification_channel:
        notification_channel = ctx.channel

    twitch_user = await get_twitch_user_info(twitch_username)

    if not twitch_user:
        await ctx.send(f"Could not find Twitch user: {twitch_username}")
        return

    key_username = twitch_user['login']

    followed_twitch_channels[key_username] = {
        "user_id": twitch_user['id'],
        "display_name": twitch_user['display_name'],
        "discord_channel_id": notification_channel.id,
        "last_live_status": False, # Initialize as offline
        "last_stream_id": None,
        "last_game_name": None
    }
    save_twitch_follows(followed_twitch_channels)
    await ctx.send(f"Now following {twitch_user['display_name']} ({key_username}). Notifications will be sent to {notification_channel.mention}.")

@follow_twitch.error
async def follow_twitch_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `!followtwitch <twitch_username> [#discord_channel (optional)]`")
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send(f"Error: Could not find the Discord channel specified: {error.argument}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Error: Invalid argument provided. {error}")
    else:
        await ctx.send(f"An error occurred: {error}")
        print(f"Error in follow_twitch command: {error}")


@bot.command(name='unfollowtwitch')
@commands.has_permissions(manage_guild=True)
async def unfollow_twitch(ctx, twitch_username: str):
    """Unfollows a Twitch streamer."""
    key_username = twitch_username.lower() # Normalize for lookup

    # Try to find by display name if direct key_username fails, then get login name
    found_key = None
    if key_username in followed_twitch_channels:
        found_key = key_username
    else:
        for k, v in followed_twitch_channels.items():
            if v.get('display_name', '').lower() == key_username:
                found_key = k
                break

    if found_key:
        display_name_to_show = followed_twitch_channels[found_key].get('display_name', found_key)
        del followed_twitch_channels[found_key]
        save_twitch_follows(followed_twitch_channels)
        await ctx.send(f"No longer following {display_name_to_show} ({found_key}).")
    else:
        await ctx.send(f"{twitch_username} is not currently being followed.")

@unfollow_twitch.error
async def unfollow_twitch_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `!unfollowtwitch <twitch_username>`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    else:
        await ctx.send(f"An error occurred: {error}")
        print(f"Error in unfollow_twitch command: {error}")


@bot.command(name='listtwitch')
async def list_twitch(ctx):
    """Lists all followed Twitch streamers and their notification channels."""
    if not followed_twitch_channels:
        await ctx.send("Not following any Twitch channels yet. Use `!followtwitch <username> [#channel]` to add one.")
        return

    embed = discord.Embed(title="Followed Twitch Channels", color=discord.Color.purple()) # Twitch color
    description_lines = []
    for username, details in followed_twitch_channels.items():
        channel_mention = f"<#{details['discord_channel_id']}>" if 'discord_channel_id' in details else "Unknown channel"
        display_name = details.get('display_name', username)
        # twitch_id = details.get('user_id', 'N/A') # user_id might be too much for a simple list
        last_status = "Live" if details.get('last_live_status', False) else "Offline"

        description_lines.append(f"**{display_name}** (`{username}`)\n  Notifying: {channel_mention}\n  Status: {last_status}\n")

    if not description_lines: # Should be caught by the initial check, but as a safeguard
        await ctx.send("No channels are currently being followed.")
        return

    # Discord embed field values have a limit, and total embed description also.
    # For simplicity, we'll join into description. If many channels, pagination would be needed.
    full_description = "\n".join(description_lines)
    if len(full_description) > 4096: # Max embed description length
        full_description = full_description[:4090] + "\n..."
        embed.set_footer(text="List truncated due to length.")

    embed.description = full_description
    await ctx.send(embed=embed)

if __name__ == '__main__':
    print("Bot is attempting to start...")
    print("Ensure DISCORD_BOT_TOKEN, DISCORD_SERVER_ID, DISCORD_USER_ID, TWITCH_CLIENT_ID, and TWITCH_CLIENT_SECRET environment variables are correctly set in your .env file or system environment.")
    bot.run(BOT_TOKEN)
