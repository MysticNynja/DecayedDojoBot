
import discord
from discord.ext import tasks, commands
import aiohttp
import os
import sys
import time # For Twitch token expiry and embed timestamps
import json # For server_settings.json and stream_registrations.json
from dotenv import load_dotenv
from datetime import time as dt_time, timezone as dt_timezone # For specific time scheduling
import datetime  # <-- Add this import for datetime.datetime.now()
from discord import app_commands # For slash command groups and decorators

# Load environment variables from .env file at the very start
load_dotenv()

# --- Configuration from Environment Variables ---
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SERVER_ID_STR = os.getenv('DISCORD_SERVER_ID') # For name changer
USER_ID_STR = os.getenv('DISCORD_USER_ID')     # For name changer

# Validate core bot configuration
if not BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)
if not SERVER_ID_STR:
    print("Error: DISCORD_SERVER_ID (for name changer) environment variable not set.", file=sys.stderr)
    sys.exit(1) # Assuming name changer is a core feature that needs its config
if not USER_ID_STR:
    print("Error: DISCORD_USER_ID (for name changer) environment variable not set.", file=sys.stderr)
    sys.exit(1) # Assuming name changer is a core feature

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

# Twitch Configuration (Optional - features disabled if not set)
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
    print("Warning: TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET not set. Twitch features will be disabled.", file=sys.stderr)

# Debug Mode Configuration
DEBUG_MODE_ENABLED = os.getenv('BOT_DEBUG_MODE', 'False').lower() == 'true'
print(f"Bot Debug Mode Enabled: {DEBUG_MODE_ENABLED}")

# --- Global Variables for Twitch ---
twitch_access_token = None
twitch_token_expires_at = 0

# --- JSON Persistence ---
SERVER_SETTINGS_FILE = 'server_settings.json'
STREAM_REGISTRATIONS_FILE = 'stream_registrations.json'

guild_settings = {}
guild_stream_registrations = {}

def load_json_data(filepath, description):
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                print(f"Warning: Data in {filepath} ({description}) is not a dictionary. Resetting to empty.")
                return {}
            return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {filepath} ({description}): {e}. Returning empty dictionary.")
        return {}

def save_json_data(data, filepath, description):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving {filepath} ({description}): {e}")

guild_settings = load_json_data(SERVER_SETTINGS_FILE, "server settings")
guild_stream_registrations = load_json_data(STREAM_REGISTRATIONS_FILE, "stream registrations")

# --- Bot Intents and Initialization ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,  # Only respond to @mentions, no ! prefix
            help_command=None,  # Disable the default help command
            intents=intents
        )

    async def setup_hook(self):
        print("Running setup_hook...")
        
        # Add command groups to the tree
        self.tree.add_command(twitch_admin_group)
        self.tree.add_command(twitch_user_group)
        print("Added command groups to tree")
        
        # Sync commands
        try:
            await self.tree.sync()
            print("Commands synced globally")
        except Exception as e:
            print(f"Error syncing commands: {e}")
        
        # Start tasks
        if not change_nickname_task.is_running():
            change_nickname_task.start()
        
        if TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET:
            if not check_twitch_streams_task.is_running():
                check_twitch_streams_task.start()
            print("Daily name changer task and Twitch stream checker task started.")
        else:
            print("Daily name changer task started. Twitch stream checker is DISABLED.")

# Create bot instance after all command definitions
bot = CustomBot()

# --- Twitch API Helper Functions ---
async def get_twitch_app_access_token():
    global twitch_access_token, twitch_token_expires_at
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET: return None
    if twitch_access_token and twitch_token_expires_at > (time.time() + 60): return twitch_access_token

    print("Requesting new Twitch App Access Token...")
    # (Rest of the function as previously defined)
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
                    twitch_token_expires_at = time.time() + data['expires_in']
                    print("Successfully obtained new Twitch App Access Token.")
                    return twitch_access_token
                else:
                    print(f"Error: Could not parse token or expiry from Twitch response: {data}")
                    return None
        except Exception as e:
            print(f"Error requesting Twitch App Access Token: {e}")
            return None

async def get_twitch_user_info(username: str):
    if not TWITCH_CLIENT_ID: return None
    token = await get_twitch_app_access_token()
    if not token: return None

    url = f"https://api.twitch.tv/helix/users?login={username.lower()}"
    headers = {'Client-ID': TWITCH_CLIENT_ID, 'Authorization': f'Bearer {token}'}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                if data.get('data'):
                    user_data = data['data'][0]
                    return {"id": user_data['id'], "login": user_data['login'], "display_name": user_data['display_name']}
                return None
        except Exception as e:
            print(f"Error fetching Twitch user info for {username}: {e}")
            return None

# Add this function near your other Twitch API helpers
async def get_twitch_user_profile(user_id: str, headers: dict):
    url = f"https://api.twitch.tv/helix/users?id={user_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data'):
                        return data['data'][0]
                return None
        except Exception as e:
            print(f"Error fetching user profile: {e}")
            return None

# Add this helper function near your other Twitch API functions
async def get_game_info(game_id: str, headers: dict):
    if not game_id: return None
    url = f"https://api.twitch.tv/helix/games?id={game_id}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data'):
                        return data['data'][0]
                return None
        except Exception as e:
            print(f"Error fetching game info: {e}")
            return None

# Add this helper function with your other Twitch API functions
async def get_stream_clips(broadcaster_id: str, started_at: str, headers: dict):
    """Get clips created during the stream"""
    url = f"https://api.twitch.tv/helix/clips?broadcaster_id={broadcaster_id}&started_at={started_at}&first=5"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                return []
        except Exception as e:
            print(f"Error fetching clips: {e}")
            return []

# --- Name Changer Feature ---
async def get_random_male_name():
    # (Function as previously defined)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://randomuser.me/api/?gender=male&inc=name') as response:
                response.raise_for_status() 
                data = await response.json()
                if data['results'] and data['results'][0]['name'] and data['results'][0]['name']['first']:
                    return data['results'][0]['name']['first']
                else:
                    print("Error: Could not parse name from randomuser.me API response or results are empty.")
                    return None
        except Exception as e:
            print(f"Error fetching name from randomuser.me API: {e}")
            return None


async def perform_nickname_change(guild_id: int, target_user_id: int, bot_instance: commands.Bot):
    # (Function as previously defined)
    print(f"Attempting perform_nickname_change for user {target_user_id} on guild {guild_id}")
    try:
        guild = bot_instance.get_guild(guild_id)
        if not guild:
            error_msg = f"Error: Server with ID {guild_id} not found. Check DISCORD_SERVER_ID."
            print(error_msg)
            return False, error_msg
        member = guild.get_member(target_user_id)
        if not member:
            error_msg = f"Error: User with ID {target_user_id} not found on server {guild.name}. Check DISCORD_USER_ID."
            print(error_msg)
            return False, error_msg
        new_name = await get_random_male_name()
        if not new_name:
            error_msg = "Failed to get a new name from API for nickname change."
            print(error_msg)
            return False, error_msg
        await member.edit(nick=new_name)
        success_msg = f"Successfully changed nickname for {member.display_name} to {new_name}."
        print(success_msg)
        return True, new_name
    except discord.Forbidden:
        error_msg = f"Permission Error: Bot lacks permission to change nickname for user {target_user_id} on server {guild_id}."
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during nickname change: {e}"
        print(error_msg)
        return False, error_msg

@tasks.loop(time=dt_time(hour=6, minute=1, tzinfo=dt_timezone.utc))
async def change_nickname_task():
    await bot.wait_until_ready()
    print("Scheduled daily nickname change task running...")
    success, message = await perform_nickname_change(SERVER_ID, USER_ID, bot)
    if success:
        print(f"Daily nickname change successful for user {USER_ID}: new name {message}")
    else:
        print(f"Daily nickname change failed for user {USER_ID}: {message}")

# --- Twitch Notification Task ---
@tasks.loop(minutes=1)
async def check_twitch_streams_task():
    await bot.wait_until_ready()
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET: 
        print("Twitch features disabled - missing credentials")
        return
    if not guild_stream_registrations: 
        print("No stream registrations found")
        return

    token = await get_twitch_app_access_token()
    if not token:
        print("Twitch Poll: Failed to get token.")
        return

    print("--- Starting Twitch stream check ---")
    headers = {'Client-ID': TWITCH_CLIENT_ID, 'Authorization': f'Bearer {token}'}
    
    for guild_id_str, streams in list(guild_stream_registrations.items()):
        # Get notification channel for this guild
        notification_channel_id = guild_settings.get(guild_id_str, {}).get('twitch_notification_channel_id')
        if not notification_channel_id:
            print(f"No notification channel set for guild {guild_id_str}")
            continue
            
        discord_channel = bot.get_channel(notification_channel_id)
        if not discord_channel:
            print(f"Could not find channel {notification_channel_id} for guild {guild_id_str}")
            continue
        if not isinstance(discord_channel, discord.TextChannel):
            print(f"Channel {notification_channel_id} for guild {guild_id_str} is not a TextChannel (type: {type(discord_channel)}), skipping.")
            continue

        for twitch_user_id, details in list(streams.items()):
            login_name = details.get('login_name', 'unknown')
            print(f"Checking stream status for {login_name} (ID: {twitch_user_id})")
            
            url = f"https://api.twitch.tv/helix/streams?user_id={twitch_user_id}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as resp:
                        print(f"API response status for {login_name}: {resp.status}")
                        if resp.status == 200:
                            api_resp = await resp.json()
                            print(f"API response for {login_name}: {api_resp}")
                            
                            is_live_now = bool(api_resp.get('data'))
                            was_live = details.get('last_live_status', False)
                            
                            # Stream just went live
                            if is_live_now:
                                stream_data = api_resp['data'][0]
                                current_viewers = stream_data.get('viewer_count', 0)
                                current_game_id = stream_data.get('game_id')
                                current_game_name = stream_data.get('game_name', 'No Game')
                                
                                # Update stats for existing stream
                                if was_live and details.get('last_message_id'):
                                    try:
                                        message = await discord_channel.fetch_message(details['last_message_id'])
                                        if message:
                                            updated_embed = message.embeds[0]
                                            
                                            # Update stream title if changed
                                            current_title = stream_data.get('title', 'No Title')
                                            description_lines = (updated_embed.description or "").split('\n')
                                            if not description_lines[0].endswith(current_title):
                                                description_lines[0] = f"**{current_title}**"
                                                updated_embed.description = '\n'.join(description_lines)
                                            
                                            # If game changed, update game info and image
                                            if current_game_id != details.get('last_game_id'):
                                                game_info = await get_game_info(current_game_id, headers)
                                                
                                                # Update title and game name in description
                                                updated_embed.title = f"{details.get('display_name', login_name)} is playing {current_game_name}!"
                                                description_lines = (updated_embed.description or "").split('\n')
                                                for i, line in enumerate(description_lines):
                                                    if "🎮 Playing:" in line:
                                                        description_lines[i] = f"🎮 Playing: **{current_game_name}**"
                                                updated_embed.description = '\n'.join(description_lines)
                                                
                                                # Update game box art
                                                if game_info and game_info.get('box_art_url'):
                                                    box_art_url = game_info['box_art_url'].replace('{width}', '285').replace('{height}', '380')
                                                    updated_embed.set_image(url=box_art_url)
                                                
                                                details['last_game_id'] = current_game_id
                                                details['last_game_name'] = current_game_name
                                            
                                            # Update viewer count
                                            description_lines = (updated_embed.description or "").split('\n')
                                            for i, line in enumerate(description_lines):
                                                if "👥 Current Viewers:" in line:
                                                    description_lines[i] = f"👥 Current Viewers: **{current_viewers}**"
                                            updated_embed.description = '\n'.join(description_lines)
                                            
                                            # Update the message with all changes
                                            if DEBUG_MODE_ENABLED:
                                                edited_message_content = "[DEBUG] Stream Updated" # Or use message.content to preserve original if it was debug
                                            else:
                                                edited_message_content = "@everyone"
                                            await message.edit(content=edited_message_content, embed=updated_embed)
                                            
                                            # Update stats
                                            if current_viewers > details.get('peak_viewers', 0):
                                                details['peak_viewers'] = current_viewers
                                            details['total_viewers'] = details.get('total_viewers', 0) + current_viewers
                                            details['viewer_count_samples'] = details.get('viewer_count_samples', 0) + 1
                                            details['avg_viewers'] = round(details['total_viewers'] / details['viewer_count_samples'])
                                            save_json_data(guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")
                                    except Exception as e:
                                        print(f"Error updating live message for {login_name}: {e}")
                                
                                # Stream just went live
                                elif not was_live:
                                    # Get both profile and game info
                                    user_profile = await get_twitch_user_profile(twitch_user_id, headers)
                                    game_info = await get_game_info(current_game_id, headers)
                                    
                                    # Store stream start time and thumbnail URL
                                    details['stream_start_time'] = datetime.datetime.now(datetime.timezone.utc).timestamp()
                                    details['stream_start_timestamp'] = datetime.datetime.now(datetime.timezone.utc).timestamp()
                                    details['last_thumbnail_url'] = stream_data.get('thumbnail_url')  # Store thumbnail URL
                                    if DEBUG_MODE_ENABLED:
                                        print(f"DEBUG: Stream {login_name} just went live. Initial timestamps set: stream_start_time={details['stream_start_time']}, stream_start_timestamp={details['stream_start_timestamp']}")
                                    
                                    # Create the new embed
                                    embed_title = f"{details.get('display_name', login_name)} is playing {current_game_name} on Twitch!"
                                    embed_url = f"https://www.twitch.tv/{login_name}"
                                    embed_description = (
                                        f"{stream_data.get('title', 'No Title')}\n"
                                        f"🎮 Playing: {current_game_name}\n"
                                        f"👥 Current Viewers: {current_viewers}"
                                    )
                                    
                                    stream_embed = discord.Embed(
                                        title=embed_title,
                                        url=embed_url,
                                        description=embed_description,
                                        color=0x00b0f4, # Hex value for #00b0f4
                                        timestamp=datetime.datetime.now(datetime.timezone.utc)
                                    )

                                    # Author (Streamer Info)
                                    author_icon_url = None
                                    if user_profile and user_profile.get('profile_image_url'):
                                        author_icon_url = user_profile['profile_image_url']
                                    stream_embed.set_author(
                                        name=details.get('display_name', login_name),
                                        url=embed_url,
                                        icon_url=author_icon_url
                                    )

                                    # Thumbnail (Game Box Art)
                                    if game_info and game_info.get('box_art_url'):
                                        box_art_url = game_info['box_art_url'].replace('{width}', '285').replace('{height}', '380')
                                        stream_embed.set_thumbnail(url=box_art_url)
                                    
                                    # Image (Stream Preview)
                                    if stream_data.get('thumbnail_url'):
                                        base_url = stream_data['thumbnail_url'].replace('{width}', '400').replace('{height}', '225')
                                        # Add cache-busting query parameter
                                        final_stream_preview_url = f"{base_url}?t={int(time.time())}"
                                        stream_embed.set_image(url=final_stream_preview_url)

                                    # Footer
                                    stream_embed.set_footer(
                                        text="decayeddojo.com",
                                        icon_url="https://cdn-icons-png.flaticon.com/128/4494/4494567.png"
                                    )

                                    try:
                                        # Create View and Button
                                        view = discord.ui.View()
                                        button = discord.ui.Button(
                                            label="Watch Stream",
                                            style=discord.ButtonStyle.link,
                                            url=embed_url # embed_url is f"https://www.twitch.tv/{login_name}"
                                        )
                                        view.add_item(button)

                                        custom_message = details.get('custom_live_message')
                                        if custom_message: # Check if not None and not empty
                                            text_to_use = custom_message
                                        else:
                                            text_to_use = stream_data.get('title', 'Live on Twitch!')

                                        if DEBUG_MODE_ENABLED:
                                            message_content = f"[DEBUG] {text_to_use}" # No @everyone ping in debug mode
                                        else:
                                            message_content = f"{text_to_use} @everyone" # Normal behavior with @everyone

                                        message = await discord_channel.send(content=message_content, embed=stream_embed, view=view)
                                        details['last_message_id'] = message.id
                                        print(f"Sent live notification for {login_name}")
                                    except Exception as e:
                                        print(f"Error sending notification: {e}")
                                
                                # Update stream status
                                details['last_live_status'] = True
                                details['last_stream_id'] = stream_data.get('id')
                                details['last_game_name'] = current_game_name
                                details['last_game_id'] = current_game_id
                                # Timestamps are set only in the 'elif not was_live:' block now
                                # The debug print for initial timestamp setting is now at the beginning of this block.
                                save_json_data(guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")
                            

                            elif not is_live_now and was_live:
                                # Stream went offline
                                print(f"Stream went offline: {login_name}")
                                
                                # Calculate stream duration if we have the start time
                                duration_text = ""
                                start_ts_for_duration = details.get('stream_start_timestamp')
                                current_ts_for_duration = time.time() # This is a local epoch time
                                if DEBUG_MODE_ENABLED:
                                    print(f"DEBUG: Calculating duration for {login_name}. Start_Timestamp (UTC epoch): {start_ts_for_duration}, Current_Time (local epoch): {current_ts_for_duration}")
                                if start_ts_for_duration is not None:
                                    # It's important that both timestamps are of the same nature (both UTC epoch or both local epoch)
                                    # Since start_ts_for_duration is now UTC epoch, current_ts_for_duration should also be UTC epoch for direct subtraction.
                                    current_utc_ts_for_duration = datetime.datetime.now(datetime.timezone.utc).timestamp()
                                    if DEBUG_MODE_ENABLED:
                                        print(f"DEBUG: Using Current_Time (UTC epoch) for calculation: {current_utc_ts_for_duration}")
                                    duration = current_utc_ts_for_duration - start_ts_for_duration
                                    if DEBUG_MODE_ENABLED:
                                        print(f"DEBUG: Raw duration value: {duration}")
                                    hours = int(duration // 3600)
                                    minutes = int((duration % 3600) // 60)
                                    duration_text = f"Stream Duration: **{hours}h {minutes}m**"
                                else:
                                    if DEBUG_MODE_ENABLED:
                                        print(f"DEBUG: Start_Timestamp is None for {login_name}, duration_text will be empty.")
                                
                                # Get user profile for thumbnail
                                user_profile = await get_twitch_user_profile(twitch_user_id, headers)
                                
                                # Create the new embed for offline message
                                embed_title = f"{details.get('display_name', login_name)} has finished streaming."
                                embed_url = f"https://www.twitch.tv/{login_name}"
                                embed_description = (
                                    "Stream Summary\n"
                                    f"{duration_text}\n"
                                    f"Peak Viewers: **{details.get('peak_viewers', 0)}**\n"
                                    f"Average Viewers: **{details.get('avg_viewers', 0)}**\n"
                                    f"Last Game: **{details.get('last_game_name', 'N/A')}**\n\n"
                                    "Thanks for watching! 👋"
                                )

                                offline_embed = discord.Embed(
                                    title=embed_title,
                                    description=embed_description,
                                    color=0x808080,  # Hex value for dark grey
                                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                                )

                                # Author (Streamer Info)
                                author_icon_url = None
                                if user_profile and user_profile.get('profile_image_url'):
                                    author_icon_url = user_profile['profile_image_url']
                                offline_embed.set_author(
                                    name=details.get('display_name', login_name),
                                    url=embed_url,
                                    icon_url=author_icon_url
                                )

                                # Thumbnail (Last Game Box Art)
                                game_info = None # Ensure game_info is defined before conditional assignment
                                if details.get('last_game_id'):
                                    game_info = await get_game_info(details['last_game_id'], headers)
                                if game_info and game_info.get('box_art_url'):
                                    box_art_url = game_info['box_art_url'].replace('{width}', '285').replace('{height}', '380')
                                    offline_embed.set_thumbnail(url=box_art_url)
                                else: # Fallback if no game box art (e.g. game_id was null, or API failed)
                                    offline_embed.set_thumbnail(url=None) # Or a default placeholder

                                # Ensure no main image is set for offline embed
                                offline_embed.set_image(url=None)

                                # Footer
                                offline_embed.set_footer(
                                    text="decayeddojo.com",
                                    icon_url="https://cdn-icons-png.flaticon.com/128/4494/4494567.png"
                                )
                                
                                try:
                                    await discord_channel.send(embed=offline_embed)
                                    print(f"Sent offline notification for {login_name}")
                                except Exception as e:
                                    print(f"Error sending offline notification: {e}")
                                
                                # Update status and clear stream data
                                details['last_live_status'] = False
                                details['stream_start_time'] = None
                                details['last_stream_id'] = None
                                details['last_message_id'] = None
                                details['peak_viewers'] = 0
                                details['avg_viewers'] = 0
                                save_json_data(guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")
                                
                                # Check for clips if clips channel is configured
                                clips_channel_id = guild_settings.get(guild_id_str, {}).get('twitch_clips_channel_id')
                                if clips_channel_id:
                                    clips_channel = bot.get_channel(clips_channel_id)
                                    if clips_channel and isinstance(clips_channel, discord.TextChannel):
                                        # Format the start time for Twitch API
                                        raw_start_time_value = details.get('stream_start_time') # Get value, might be None
                                        # Ensure numeric_start_time is 0 if raw_start_time_value is None, otherwise use raw_start_time_value
                                        numeric_start_time_for_clips = raw_start_time_value if raw_start_time_value is not None else 0

                                        # Use timezone aware UTC for fromtimestamp
                                        start_time_iso = datetime.datetime.fromtimestamp(numeric_start_time_for_clips, datetime.timezone.utc).isoformat() + 'Z'
                                        
                                        # Get clips created during the stream
                                        clips = await get_stream_clips(twitch_user_id, start_time_iso, headers)
                                        
                                        if clips:
                                            clips_embed = discord.Embed(
                                                title=f"📎 Clips from {details.get('display_name', login_name)}'s stream",
                                                description="Here are the clips created during the stream:",
                                                color=discord.Color.purple()
                                            )
                                            
                                            for clip in clips:
                                                clips_embed.add_field(
                                                    name=f"👀 {clip.get('title', 'Untitled Clip')}",
                                                    value=f"Created by: {clip.get('creator_name', 'Unknown')}\n"
                                                          f"Views: {clip.get('view_count', 0)}\n"
                                                          f"[Watch Clip]({clip.get('url')})",
                                                    inline=False
                                                )
                                            
                                            try:
                                                await clips_channel.send(embed=clips_embed)
                                                print(f"Sent clips summary for {login_name}")
                                            except Exception as e:
                                                print(f"Error sending clips: {e}")
                                
            except Exception as e:
                print(f"Error checking {login_name}: {e}")

# --- Event: Bot Ready ---
@bot.event
async def on_ready():
    # User attribute check as per your feedback
    if bot.user is not None:
        print(f'Bot logged in as {bot.user.name}')
    else:
        print('Bot user object is None at on_ready. This is unexpected.')
        return # Cannot proceed without bot.user

    # Diagnostic prints for commands are here (before sync)
    print("--- Diagnosing commands in bot.tree before sync ---")
    all_commands_on_tree = bot.tree.get_commands() 
    print(f"Total top-level items found in bot.tree: {len(all_commands_on_tree)}")
    for cmd_or_group in all_commands_on_tree:
        print(f"  Item: {cmd_or_group.name}, Type: {type(cmd_or_group)}")
        if isinstance(cmd_or_group, app_commands.Group):
            # For app_commands.Group, sub-commands are in its 'commands' attribute (a list)
            group_sub_commands = cmd_or_group.commands
            print(f"    Sub-commands in group '{cmd_or_group.name}': {[c.name for c in group_sub_commands]}")
    print("--- End diagnostic prints ---")

    # Sync slash commands
    try:
        guild_id_env = os.getenv('DISCORD_TEST_GUILD_ID')
        if guild_id_env:
            try:
                guild_obj = discord.Object(id=int(guild_id_env))
                print(f"Attempting to sync to specific guild: {guild_id_env}")
                synced = await bot.tree.sync(guild=guild_obj)
                print(f"Synced {len(synced)} slash command(s) to guild {guild_id_env}.")
            except ValueError:
                print(f"Error: DISCORD_TEST_GUILD_ID ('{guild_id_env}') is not a valid integer. Falling back to global sync.")
                synced = await bot.tree.sync()
                print(f"Synced {len(synced)} slash command(s) globally (due to invalid test guild ID).")
        else:
            print("Attempting to sync commands globally...")
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} slash command(s) globally.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

# --- Slash Command Definitions ---

# Changename (direct on tree)
@bot.tree.command(name="changename", description="Manually changes the configured user's nickname.")
async def changename_slash_command(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    
    # Check invoker's permissions
    # interaction.user is a Member if in guild, User if in DM. Guild check done above.
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("You do not have 'Manage Nicknames' permission.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True) # Defer as ephemeral, followup will also be.
    success, result_message = await perform_nickname_change(SERVER_ID, USER_ID, bot)
    if success:
        await interaction.followup.send(f"Successfully changed nickname for user ID {USER_ID} to **{result_message}**.")
    else:
        await interaction.followup.send(f"Failed to change nickname for user ID {USER_ID}. Reason: {result_message}")

# Twitch Admin Group
twitch_admin_group = app_commands.Group(name="twitchadmin", description="Admin commands for Twitch feature configuration.")

@twitch_admin_group.command(name="set_channel", description="Sets the channel for Twitch live notifications on this server.")
@app_commands.describe(notification_channel="The channel where Twitch live notifications will be sent.")
@app_commands.checks.has_permissions(manage_guild=True) # discord.py handles this check for app commands
async def set_twitch_notification_channel(interaction: discord.Interaction, notification_channel: discord.TextChannel):
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        await interaction.response.send_message("Twitch features are not configured (missing bot credentials).", ephemeral=True)
        return
    if not interaction.guild_id:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    guild_id_str = str(interaction.guild_id)
    if guild_id_str not in guild_settings: guild_settings[guild_id_str] = {}
    guild_settings[guild_id_str]['twitch_notification_channel_id'] = notification_channel.id
    save_json_data(guild_settings, SERVER_SETTINGS_FILE, "server settings")
    await interaction.response.send_message(f"Twitch live notifications set to {notification_channel.mention}.", ephemeral=True)

@set_twitch_notification_channel.error # Error handler for this specific command
async def set_twitch_notification_channel_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need 'Manage Server' permissions to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {str(error)[:1800]}", ephemeral=True) # Keep error msg short
        print(f"Error in /twitchadmin set_channel: {error}")


# --- Twitch Clips Channel Setup ---
@twitch_admin_group.command(name="set_clips_channel", description="Sets the channel for Twitch clips on this server.")
@app_commands.describe(clips_channel="The channel where Twitch clips will be sent.")
@app_commands.checks.has_permissions(manage_guild=True)
async def set_twitch_clips_channel(interaction: discord.Interaction, clips_channel: discord.TextChannel):
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        await interaction.response.send_message("Twitch features are not configured (missing bot credentials).", ephemeral=True)
        return
    if not interaction.guild_id:
        await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
        return

    guild_id_str = str(interaction.guild_id)
    if guild_id_str not in guild_settings: 
        guild_settings[guild_id_str] = {}
    
    guild_settings[guild_id_str]['twitch_clips_channel_id'] = clips_channel.id
    save_json_data(guild_settings, SERVER_SETTINGS_FILE, "server settings")
    await interaction.response.send_message(f"Twitch clips will be sent to {clips_channel.mention}.", ephemeral=True)

# Twitch User Group
twitch_user_group = app_commands.Group(name="twitch", description="Manage Twitch stream notifications for Twitch channels.")

@twitch_user_group.command(name="notifyadd", description="Register a Twitch channel for live notifications on this server.")
@app_commands.describe(twitch_username="Your Twitch username (login name).")
async def twitch_notify_add(interaction: discord.Interaction, twitch_username: str):
    if not interaction.guild_id: 
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        await interaction.response.send_message("Twitch features are not configured on this bot.", ephemeral=True)
        return

    guild_id_str = str(interaction.guild_id)
    if guild_id_str not in guild_settings or 'twitch_notification_channel_id' not in guild_settings[guild_id_str]:
        await interaction.response.send_message("Admin has not set a Twitch notification channel. Use `/twitchadmin set_channel`.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    twitch_info = await get_twitch_user_info(twitch_username)
    if not twitch_info:
        await interaction.followup.send(f"Twitch user `{twitch_username}` not found.")
        return

    tid, tlogin, tdisplay = twitch_info['id'], twitch_info['login'], twitch_info['display_name']
    if guild_id_str not in guild_stream_registrations: guild_stream_registrations[guild_id_str] = {}
    if tid in guild_stream_registrations[guild_id_str]:
        await interaction.followup.send(f"`{tdisplay}` (`{tlogin}`) is already registered here.")
        return

    guild_stream_registrations[guild_id_str][tid] = {
        "display_name": tdisplay, "login_name": tlogin,
        "last_live_status": False, "last_stream_id": None, "last_game_name": None,
        "registered_by": interaction.user.id
    }
    save_json_data(guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")
    await interaction.followup.send(f"`{tdisplay}` (`{tlogin}`) registered for notifications!")

@twitch_user_group.command(name="notifyremove", description="Unregister a Twitch channel from notifications on this server.")
@app_commands.describe(twitch_username="Your Twitch username (login name) to unregister.")
async def twitch_notify_remove(interaction: discord.Interaction, twitch_username: str):
    if not interaction.guild_id:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        await interaction.response.send_message("Twitch features are not configured on this bot.", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    gid_str = str(interaction.guild_id)
    uname_lower = twitch_username.lower()
    
    if gid_str not in guild_stream_registrations:
        await interaction.followup.send(f"`{twitch_username}` not found in registrations for this server.")
        return

    found_id = None
    removed_display = uname_lower
    for tid, details in guild_stream_registrations[gid_str].items():
        if details.get('login_name','').lower() == uname_lower:
            found_id = tid
            removed_display = details.get('display_name', uname_lower)
            break
            
    if found_id:
        del guild_stream_registrations[gid_str][found_id]
        if not guild_stream_registrations[gid_str]: del guild_stream_registrations[gid_str] # Clean up empty guild entry
        save_json_data(guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")
        await interaction.followup.send(f"`{removed_display}` unregistered from notifications.")
    else:
        await interaction.followup.send(f"`{twitch_username}` not found in registrations for this server.")

@twitch_user_group.command(name="notifylist", description="Lists Twitch channels registered for notifications on this server.")
async def twitch_notify_list(interaction: discord.Interaction):
    if not interaction.guild_id:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        await interaction.response.send_message("Twitch features are not configured on this bot.", ephemeral=True)
        return

    gid_str = str(interaction.guild_id)
    if gid_str not in guild_stream_registrations or not guild_stream_registrations[gid_str]:
        await interaction.response.send_message("No Twitch channels registered for notifications on this server.", ephemeral=True)
        return

    guild_name = interaction.guild.name if interaction.guild else "this server"
    embed = discord.Embed(title=f"Twitch Notifications for {guild_name}", color=discord.Color.purple())
    lines = [f"- **{d.get('display_name', 'N/A')}** (`{d.get('login_name', 'id:'+tid)}`) - Status: {'Live' if d.get('last_live_status') else 'Offline'}" 
             for tid, d in guild_stream_registrations[gid_str].items()]
    embed.description = "\n".join(lines) if lines else "No channels registered."
    await interaction.response.send_message(embed=embed, ephemeral=True)

@twitch_user_group.command(name="setlivenotification", description="Sets or updates your custom go-live notification message for the bot.")
@app_commands.describe(
    twitch_username="Your Twitch username (login name).",
    message="Your custom go-live message (max 140 characters)."
)
async def twitch_set_live_notification(interaction: discord.Interaction, twitch_username: str, message: str):
    if not interaction.guild_id:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        await interaction.response.send_message("Twitch features are not configured on this bot.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    guild_id_str = str(interaction.guild_id)
    twitch_username_input = twitch_username.lower()

    if guild_id_str not in guild_stream_registrations:
        await interaction.followup.send(f"`{twitch_username}` not found in registrations for this server. Use `/twitch notifyadd` first.")
        return

    found_twitch_user_id = None
    user_details = None
    for tid, details_val in guild_stream_registrations[guild_id_str].items():
        if details_val.get('login_name','').lower() == twitch_username_input:
            found_twitch_user_id = tid
            user_details = details_val
            break

    if not found_twitch_user_id or not user_details:
        await interaction.followup.send(f"`{twitch_username}` not found in registrations for this server. Use `/twitch notifyadd` first.")
        return

    if len(message) > 140:
        await interaction.followup.send("Your message is too long (max 140 characters).")
        return

    guild_stream_registrations[guild_id_str][found_twitch_user_id]['custom_live_message'] = message
    save_json_data(guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")

    display_name = user_details.get('display_name', twitch_username)
    await interaction.followup.send(f"Custom live notification message updated for `{display_name}`.")


# Add this at the very bottom of the file
if __name__ == "__main__":
    print("Starting bot...")
    bot.run(BOT_TOKEN)
