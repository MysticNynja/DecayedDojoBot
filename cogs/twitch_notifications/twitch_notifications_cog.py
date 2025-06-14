import discord
from discord.ext import tasks, commands
from discord import app_commands
import aiohttp
import os
# import sys # Unused
import time
import json
from datetime import datetime # dt_time and dt_timezone are unused

# Configuration from Environment Variables - ensure these are loaded in main.py
# and accessible if needed, or pass them to the cog
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

# --- JSON Persistence ---
SERVER_SETTINGS_FILE = 'server_settings.json'
STREAM_REGISTRATIONS_FILE = 'stream_registrations.json'

def _load_json_data(filepath, description):
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

def _save_json_data(data, filepath, description):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving {filepath} ({description}): {e}")


class TwitchNotificationsCog(commands.Cog):
    # Define command groups as class attributes
    twitch_admin_group = app_commands.Group(name="twitchadmin", description="Admin commands for Twitch feature configuration.")
    twitch_user_group = app_commands.Group(name="twitch", description="Manage Twitch stream notifications for Twitch channels.")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.twitch_access_token = None
        self.twitch_token_expires_at = 0

        self.guild_settings = _load_json_data(SERVER_SETTINGS_FILE, "server settings")
        self.guild_stream_registrations = _load_json_data(STREAM_REGISTRATIONS_FILE, "stream registrations")

        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            print("TwitchNotificationsCog: Warning - Twitch features will be DISABLED (missing client ID or secret). Task will not start.")

    async def initialize_tasks(self):
        if TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET:
            if not self.check_twitch_streams_task.is_running():
                self.check_twitch_streams_task.start()
                print("TwitchNotificationsCog: Twitch stream checker task started via initialize_tasks.")
            else:
                print("TwitchNotificationsCog: Twitch stream checker task was already running when initialize_tasks was called.")
        else:
            print("TwitchNotificationsCog: initialize_tasks skipped starting task, Twitch features are DISABLED (missing client ID or secret).")

    async def cog_unload(self): # Changed to async def
        self.check_twitch_streams_task.cancel()
        print("TwitchNotificationsCog: Unloaded, Twitch stream checker task cancelled.")

    # --- Twitch API Helper Functions ---
    async def get_twitch_app_access_token(self):
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            return None
        if self.twitch_access_token and self.twitch_token_expires_at > (time.time() + 60):
            return self.twitch_access_token

        print("TwitchNotificationsCog: Requesting new Twitch App Access Token...")
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
                        self.twitch_access_token = data['access_token']
                        self.twitch_token_expires_at = time.time() + data['expires_in']
                        print("TwitchNotificationsCog: Successfully obtained new Twitch App Access Token.")
                        return self.twitch_access_token
                    else:
                        print(f"TwitchNotificationsCog Error: Could not parse token or expiry from Twitch response: {data}")
                        return None
            except Exception as e:
                print(f"TwitchNotificationsCog Error requesting Twitch App Access Token: {e}")
                return None

    async def get_twitch_user_info(self, username: str):
        if not TWITCH_CLIENT_ID:
            return None
        token = await self.get_twitch_app_access_token()
        if not token:
            return None

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
                print(f"TwitchNotificationsCog Error fetching Twitch user info for {username}: {e}")
                return None

    async def get_twitch_user_profile(self, user_id: str, headers: dict):
        url = f"https://api.twitch.tv/helix/users?id={user_id}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data'):
                            return data['data'][0]
                    # Return None if response status is not 200 or data is not found
                    return None
            except Exception as e:
                print(f"TwitchNotificationsCog Error fetching user profile: {e}")
                return None

    async def get_game_info(self, game_id: str, headers: dict):
        if not game_id:
            return None
        url = f"https://api.twitch.tv/helix/games?id={game_id}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data'):
                            return data['data'][0]
                    # Return None if response status is not 200 or data is not found
                    return None
            except Exception as e:
                print(f"TwitchNotificationsCog Error fetching game info: {e}")
                return None

    async def get_stream_clips(self, broadcaster_id: str, started_at: str, headers: dict):
        url = f"https://api.twitch.tv/helix/clips?broadcaster_id={broadcaster_id}&started_at={started_at}&first=5"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Return empty list if 'data' is not in response
                        return data.get('data', [])
                    # Return empty list if status is not 200
                    return []
            except Exception as e:
                print(f"TwitchNotificationsCog Error fetching clips: {e}")
                return []

    # --- Twitch Notification Task ---
    @tasks.loop(minutes=1)
    async def check_twitch_streams_task(self):
        await self.bot.wait_until_ready()
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            # This check might be redundant if task is not started, but good for safety
            print("TwitchNotificationsCog: Twitch features disabled - missing credentials in task.")
            return
        if not self.guild_stream_registrations:
            # print("TwitchNotificationsCog: No stream registrations found in task.") # Can be noisy
            return

        token = await self.get_twitch_app_access_token()
        if not token:
            print("TwitchNotificationsCog Poll: Failed to get token.")
            return

        # print("TwitchNotificationsCog: --- Starting Twitch stream check ---") # Can be noisy
        headers = {'Client-ID': TWITCH_CLIENT_ID, 'Authorization': f'Bearer {token}'}

        for guild_id_str, streams in list(self.guild_stream_registrations.items()):
            notification_channel_id = self.guild_settings.get(guild_id_str, {}).get('twitch_notification_channel_id')
            if not notification_channel_id:
                # print(f"TwitchNotificationsCog: No notification channel set for guild {guild_id_str}")
                continue

            discord_channel = self.bot.get_channel(notification_channel_id)
            if not discord_channel:
                print(f"TwitchNotificationsCog: Could not find channel {notification_channel_id} for guild {guild_id_str}")
                continue
            if not isinstance(discord_channel, discord.TextChannel):
                print(f"TwitchNotificationsCog: Channel {notification_channel_id} for guild {guild_id_str} is not a TextChannel, skipping.")
                continue

            for twitch_user_id, details in list(streams.items()):
                login_name = details.get('login_name', 'unknown')
                # print(f"TwitchNotificationsCog: Checking stream status for {login_name} (ID: {twitch_user_id})")

                url = f"https://api.twitch.tv/helix/streams?user_id={twitch_user_id}"
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers) as resp:
                            # print(f"TwitchNotificationsCog: API response status for {login_name}: {resp.status}")
                            if resp.status == 200:
                                api_resp = await resp.json()
                                # print(f"TwitchNotificationsCog: API response for {login_name}: {api_resp}")

                                is_live_now = bool(api_resp.get('data'))
                                was_live = details.get('last_live_status', False)

                                if is_live_now:
                                    stream_data = api_resp['data'][0]
                                    current_viewers = stream_data.get('viewer_count', 0)
                                    current_game_id = stream_data.get('game_id')
                                    current_game_name = stream_data.get('game_name', 'No Game')

                                    if was_live and details.get('last_message_id'):
                                        try:
                                            message = await discord_channel.fetch_message(details['last_message_id'])
                                            if message:
                                                updated_embed = message.embeds[0]
                                                current_title = stream_data.get('title', 'No Title')
                                                description_lines = (updated_embed.description or "").split('\n')
                                                if not description_lines[0].endswith(current_title):
                                                    description_lines[0] = f"**{current_title}**"

                                                if current_game_id != details.get('last_game_id'):
                                                    game_info = await self.get_game_info(current_game_id, headers)
                                                    updated_embed.title = f"{details.get('display_name', login_name)} is playing {current_game_name}!"
                                                    for i, line in enumerate(description_lines):
                                                        if "🎮 Playing:" in line: description_lines[i] = f"🎮 Playing: **{current_game_name}**"
                                                    if game_info and game_info.get('box_art_url'):
                                                        box_art_url = game_info['box_art_url'].replace('{width}', '285').replace('{height}', '380')
                                                        updated_embed.set_image(url=box_art_url)
                                                    details['last_game_id'] = current_game_id
                                                    details['last_game_name'] = current_game_name

                                                for i, line in enumerate(description_lines):
                                                    if "👥 Current Viewers:" in line: description_lines[i] = f"👥 Current Viewers: **{current_viewers}**"
                                                updated_embed.description = '\n'.join(description_lines)
                                                await message.edit(content="@everyone", embed=updated_embed)

                                                if current_viewers > details.get('peak_viewers', 0): details['peak_viewers'] = current_viewers
                                                details['total_viewers'] = details.get('total_viewers', 0) + current_viewers
                                                details['viewer_count_samples'] = details.get('viewer_count_samples', 0) + 1
                                                details['avg_viewers'] = round(details['total_viewers'] / details['viewer_count_samples'])
                                                _save_json_data(self.guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")
                                        except Exception as e:
                                            print(f"TwitchNotificationsCog Error updating live message for {login_name}: {e}")

                                    elif not was_live:
                                        user_profile = await self.get_twitch_user_profile(twitch_user_id, headers)
                                        game_info = await self.get_game_info(current_game_id, headers)
                                        details['stream_start_timestamp'] = datetime.now().timestamp()
                                        details['last_thumbnail_url'] = stream_data.get('thumbnail_url')

                                        stream_embed = discord.Embed(
                                            title=f"{details.get('display_name', login_name)} is now live on Twitch!",
                                            description=f"**{stream_data.get('title', 'No Title')}**\n\n"
                                                      f"🎮 Playing: **{current_game_name}**\n"
                                                      f"👥 Current Viewers: **{current_viewers}**",
                                            url=f"https://twitch.tv/{login_name}", color=discord.Color.purple()
                                        )
                                        if game_info and game_info.get('box_art_url'):
                                            box_art_url = game_info['box_art_url'].replace('{width}', '285').replace('{height}', '380')
                                            stream_embed.set_image(url=box_art_url)
                                        if user_profile and user_profile.get('profile_image_url'):
                                            stream_embed.set_thumbnail(url=user_profile['profile_image_url'])

                                        try:
                                            message = await discord_channel.send(content="@everyone", embed=stream_embed)
                                            details['last_message_id'] = message.id
                                            print(f"TwitchNotificationsCog: Sent live notification for {login_name}")
                                        except Exception as e:
                                            print(f"TwitchNotificationsCog Error sending notification: {e}")

                                    details['last_live_status'] = True
                                    details['last_stream_id'] = stream_data.get('id')
                                    details['last_game_name'] = current_game_name
                                    details['last_game_id'] = current_game_id
                                    # details['stream_start_time'] = time.time() # Already have stream_start_timestamp
                                    _save_json_data(self.guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")

                                elif not is_live_now and was_live:
                                    print(f"TwitchNotificationsCog: Stream went offline: {login_name}")
                                    duration_text = ""
                                    if details.get('stream_start_timestamp'):
                                        duration = time.time() - details.get('stream_start_timestamp')
                                        hours, minutes = int(duration // 3600), int((duration % 3600) // 60)
                                        duration_text = f"Stream Duration: **{hours}h {minutes}m**"

                                    embed = discord.Embed(
                                        title=f"📺 {details.get('display_name', login_name)} has ended their stream",
                                        description=f"**Stream Summary**\n\n{duration_text}\n"
                                                   f"Peak Viewers: **{details.get('peak_viewers', 0)}**\n"
                                                   f"Average Viewers: **{details.get('avg_viewers', 0)}**\n"
                                                   f"Last Game: **{details.get('last_game_name', 'N/A')}**\n\n"
                                                   f"Thanks for watching! 👋", color=discord.Color.dark_grey()
                                    )
                                    user_profile = await self.get_twitch_user_profile(twitch_user_id, headers)
                                    if user_profile and user_profile.get('profile_image_url'):
                                        embed.set_thumbnail(url=user_profile['profile_image_url'])

                                    if details.get('last_game_id'):
                                        game_info = await self.get_game_info(details['last_game_id'], headers)
                                        if game_info and game_info.get('box_art_url'):
                                            game_embed = discord.Embed(color=discord.Color.dark_grey())
                                            box_art_url = game_info['box_art_url'].replace('{width}', '285').replace('{height}', '380')
                                            game_embed.set_image(url=box_art_url)
                                            await discord_channel.send(embed=game_embed)

                                    if details.get('last_thumbnail_url'):
                                        thumb_url = details['last_thumbnail_url'].replace('{width}', '1280').replace('{height}', '720')
                                        stream_preview_embed = discord.Embed(color=discord.Color.dark_grey())
                                        stream_preview_embed.set_image(url=f"{thumb_url}?t={int(time.time())}")
                                        await discord_channel.send(embed=stream_preview_embed)

                                    embed.set_footer(text="Stream Ended")
                                    embed.timestamp = datetime.now()

                                    try:
                                        await discord_channel.send(embed=embed)
                                        print(f"TwitchNotificationsCog: Sent offline notification for {login_name}")
                                    except Exception as e:
                                        print(f"TwitchNotificationsCog Error sending offline notification: {e}")

                                    details.update({
                                        'last_live_status': False, 'stream_start_timestamp': None,
                                        'last_stream_id': None, 'last_message_id': None,
                                        'peak_viewers': 0, 'avg_viewers': 0,
                                        'total_viewers': 0, 'viewer_count_samples': 0
                                    })  # Reset more stats
                                    _save_json_data(self.guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")

                                    clips_channel_id = self.guild_settings.get(guild_id_str, {}).get('twitch_clips_channel_id')
                                    if clips_channel_id:
                                        clips_channel = self.bot.get_channel(clips_channel_id)
                                        if clips_channel and isinstance(clips_channel, discord.TextChannel):
                                            stream_start_ts = details.get('stream_start_timestamp')
                                            start_time_iso = None
                                            if stream_start_ts:
                                                start_time_iso = datetime.fromtimestamp(stream_start_ts).isoformat() + 'Z'

                                            if start_time_iso: # Only fetch clips if we have a valid start time
                                                clips = await self.get_stream_clips(twitch_user_id, start_time_iso, headers)
                                                if clips:
                                                    clips_embed = discord.Embed(title=f"📎 Clips from {details.get('display_name', login_name)}'s stream",
                                                                                description="Here are the clips created during the stream:",
                                                                                color=discord.Color.purple())
                                                    for clip in clips:
                                                        clips_embed.add_field(name=f"👀 {clip.get('title', 'Untitled Clip')}",
                                                                            value=f"Created by: {clip.get('creator_name', 'Unknown')}\nViews: {clip.get('view_count', 0)}\n[Watch Clip]({clip.get('url')})",
                                                                            inline=False)
                                                    try:
                                                        await clips_channel.send(embed=clips_embed)
                                                        print(f"TwitchNotificationsCog: Sent clips summary for {login_name}")
                                                    except Exception as e:
                                                        print(f"TwitchNotificationsCog Error sending clips: {e}")
                except Exception as e:
                    print(f"TwitchNotificationsCog Error checking {login_name}: {e}")

    @check_twitch_streams_task.before_loop
    async def before_check_twitch_streams_task(self):
        await self.bot.wait_until_ready()
        print("TwitchNotificationsCog: `check_twitch_streams_task` waiting for bot readiness.")

    # --- Admin Commands ---
    @twitch_admin_group.command(name="set_channel", description="Sets the channel for Twitch live notifications.")
    @app_commands.describe(notification_channel="The channel for live notifications.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_twitch_notification_channel(self, interaction: discord.Interaction, notification_channel: discord.TextChannel):
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            await interaction.response.send_message("Twitch features are not configured (missing bot credentials).", ephemeral=True)
            return
        if not interaction.guild_id: # Trailing space was here, removed.
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return

        guild_id_str = str(interaction.guild_id)
        if guild_id_str not in self.guild_settings: self.guild_settings[guild_id_str] = {}
        self.guild_settings[guild_id_str]['twitch_notification_channel_id'] = notification_channel.id
        _save_json_data(self.guild_settings, SERVER_SETTINGS_FILE, "server settings")
        await interaction.response.send_message(f"Twitch live notifications set to {notification_channel.mention}.", ephemeral=True)

    @set_twitch_notification_channel.error
    async def set_twitch_notification_channel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You need 'Manage Server' permissions.", ephemeral=True)
        else:
            await interaction.response.send_message(f"An error occurred: {str(error)[:1800]}", ephemeral=True)
            print(f"TwitchNotificationsCog Error in /twitchadmin set_channel: {error}")

    @twitch_admin_group.command(name="set_clips_channel", description="Sets the channel for Twitch clips.")
    @app_commands.describe(clips_channel="The channel for Twitch clips.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_twitch_clips_channel(self, interaction: discord.Interaction, clips_channel: discord.TextChannel):
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            await interaction.response.send_message("Twitch features are not configured.", ephemeral=True)
            return
        if not interaction.guild_id: # Trailing space was here, removed.
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return

        guild_id_str = str(interaction.guild_id)
        if guild_id_str not in self.guild_settings: self.guild_settings[guild_id_str] = {}
        self.guild_settings[guild_id_str]['twitch_clips_channel_id'] = clips_channel.id
        _save_json_data(self.guild_settings, SERVER_SETTINGS_FILE, "server settings")
        await interaction.response.send_message(f"Twitch clips will be sent to {clips_channel.mention}.", ephemeral=True)

    # --- User Commands ---
    @twitch_user_group.command(name="notifyadd", description="Register a Twitch channel for live notifications.")
    @app_commands.describe(twitch_username="Your Twitch username.")
    async def twitch_notify_add(self, interaction: discord.Interaction, twitch_username: str):
        if not interaction.guild_id: # Trailing space was here, removed.
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            await interaction.response.send_message("Twitch features are not configured on this bot.", ephemeral=True)
            return

        guild_id_str = str(interaction.guild_id)
        if guild_id_str not in self.guild_settings or 'twitch_notification_channel_id' not in self.guild_settings[guild_id_str]:
            await interaction.response.send_message("Admin has not set a Twitch notification channel. Use `/twitchadmin set_channel`.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        twitch_info = await self.get_twitch_user_info(twitch_username)
        if not twitch_info:
            await interaction.followup.send(f"Twitch user `{twitch_username}` not found.")
            return

        tid, tlogin, tdisplay = twitch_info['id'], twitch_info['login'], twitch_info['display_name']
        if guild_id_str not in self.guild_stream_registrations: self.guild_stream_registrations[guild_id_str] = {}
        if tid in self.guild_stream_registrations[guild_id_str]:
            await interaction.followup.send(f"`{tdisplay}` (`{tlogin}`) is already registered here.")
            return

        self.guild_stream_registrations[guild_id_str][tid] = {
            "display_name": tdisplay, "login_name": tlogin,
            "last_live_status": False, "last_stream_id": None, "last_game_name": None,
            "last_game_id": None, "stream_start_timestamp": None, "last_thumbnail_url": None, # Initialize new fields
            "peak_viewers": 0, "avg_viewers": 0, "total_viewers": 0, "viewer_count_samples": 0, # Initialize stats
            "registered_by": interaction.user.id
        }
        _save_json_data(self.guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")
        await interaction.followup.send(f"`{tdisplay}` (`{tlogin}`) registered for notifications!")

    @twitch_user_group.command(name="notifyremove", description="Unregister a Twitch channel from notifications.")
    @app_commands.describe(twitch_username="Twitch username to unregister.")
    async def twitch_notify_remove(self, interaction: discord.Interaction, twitch_username: str):
        if not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            await interaction.response.send_message("Twitch features are not configured on this bot.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        gid_str = str(interaction.guild_id)
        uname_lower = twitch_username.lower()

        if gid_str not in self.guild_stream_registrations:
            await interaction.followup.send(f"`{twitch_username}` not found in registrations for this server.")
            return

        found_id = None
        removed_display = uname_lower
        for tid, details in self.guild_stream_registrations[gid_str].items():
            if details.get('login_name','').lower() == uname_lower:
                found_id = tid
                removed_display = details.get('display_name', uname_lower)
                break

        if found_id:
            del self.guild_stream_registrations[gid_str][found_id]
            if not self.guild_stream_registrations[gid_str]: del self.guild_stream_registrations[gid_str]
            _save_json_data(self.guild_stream_registrations, STREAM_REGISTRATIONS_FILE, "stream registrations")
            await interaction.followup.send(f"`{removed_display}` unregistered from notifications.")
        else:
            await interaction.followup.send(f"`{twitch_username}` not found in registrations for this server.")

    @twitch_user_group.command(name="notifylist", description="Lists Twitch channels registered for notifications.")
    async def twitch_notify_list(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
            await interaction.response.send_message("Twitch features are not configured on this bot.", ephemeral=True)
            return

        gid_str = str(interaction.guild_id)
        if gid_str not in self.guild_stream_registrations or not self.guild_stream_registrations[gid_str]:
            await interaction.response.send_message("No Twitch channels registered for notifications on this server.", ephemeral=True)
            return

        guild_name = interaction.guild.name if interaction.guild else "this server"
        embed = discord.Embed(title=f"Twitch Notifications for {guild_name}", color=discord.Color.purple())
        lines = [f"- **{d.get('display_name', 'N/A')}** (`{d.get('login_name', 'id:'+tid)}`) - Status: {'Live' if d.get('last_live_status') else 'Offline'}"
                 for tid, d in self.guild_stream_registrations[gid_str].items()]
        embed.description = "\n".join(lines) if lines else "No channels registered."
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        print("Error: Twitch Notifications Cog not loaded. TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET not set in .env.")
    else:
        # Add the command groups to the bot's tree before adding the cog
        # This ensures they are registered correctly.
        # Note: For discord.py 2.x, groups are typically part of the cog and added via bot.add_cog.
        # If groups are defined as class variables in the cog, they are automatically registered with the cog.
        # The bot.tree.add_command calls for groups are usually done in main.py for standalone groups,
        # or handled by the cog system.

        # For cogs, app command groups defined as class variables are automatically picked up.
        # If they were standalone, you'd add them like:
        # bot.tree.add_command(TwitchNotificationsCog.twitch_admin_group)
        # bot.tree.add_command(TwitchNotificationsCog.twitch_user_group)

        cog = TwitchNotificationsCog(bot)
        await bot.add_cog(cog)
        await cog.initialize_tasks() # Initialize tasks after adding the cog
        print("TwitchNotificationsCog added and tasks initialized.")
