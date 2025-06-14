import discord
from discord.ext import tasks, commands
import aiohttp
import os
from datetime import time as dt_time, timezone as dt_timezone

# Environment variables should be loaded in the main bot file,
# but we need to access them here.
# Consider passing them via the cog's constructor if they are needed at init time,
# or accessing them via bot.config if you store config on the bot object.
SERVER_ID_STR = os.getenv('DISCORD_SERVER_ID')
USER_ID_STR = os.getenv('DISCORD_USER_ID')

# It's good practice to validate these, but perhaps do it once in main.py
# and make them available to cogs, or handle potential None values gracefully.
SERVER_ID = int(SERVER_ID_STR) if SERVER_ID_STR else None
USER_ID = int(USER_ID_STR) if USER_ID_STR else None

class NameChangerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Ensure SERVER_ID and USER_ID are available and valid
        # This warning is still relevant at cog initialization time.
        if SERVER_ID is None or USER_ID is None:
            print("Warning: NameChangerCog loaded but SERVER_ID or USER_ID is not set. Nickname changes will fail if task is started.")

    async def initialize_tasks(self):
        # Start the task only if it's not already running.
        if not self.change_nickname_task.is_running():
            self.change_nickname_task.start()
            print("NameChangerCog: change_nickname_task started.")
        else:
            print("NameChangerCog: change_nickname_task was already running.")

    async def get_random_male_name(self):
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

    async def perform_nickname_change(self, guild_id: int, target_user_id: int):
        print(f"Attempting perform_nickname_change for user {target_user_id} on guild {guild_id}")
        if not guild_id or not target_user_id:
            error_msg = "Error: Guild ID or Target User ID is None in perform_nickname_change."
            print(error_msg)
            return False, error_msg
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                error_msg = f"Error: Server with ID {guild_id} not found. Check DISCORD_SERVER_ID."
                print(error_msg)
                return False, error_msg
            member = guild.get_member(target_user_id)
            if not member:
                error_msg = f"Error: User with ID {target_user_id} not found on server {guild.name}. Check DISCORD_USER_ID."
                print(error_msg)
                return False, error_msg
            new_name = await self.get_random_male_name()
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
    async def change_nickname_task(self):
        await self.bot.wait_until_ready()
        # Ensure SERVER_ID and USER_ID are valid before running the task
        if SERVER_ID is None or USER_ID is None:
            print("Daily nickname change task skipped: SERVER_ID or USER_ID not configured.")
            return

        print("Scheduled daily nickname change task running from cog...")
        success, message = await self.perform_nickname_change(SERVER_ID, USER_ID)
        if success:
            print(f"Daily nickname change successful for user {USER_ID} (via cog): new name {message}")
        else:
            print(f"Daily nickname change failed for user {USER_ID} (via cog): {message}")

    @commands.hybrid_command(name="changename", description="Manually changes the configured user's nickname.")
    @commands.has_permissions(manage_nicknames=True) # For hybrid commands, this is a good way
    async def changename_slash_command(self, ctx: commands.Context):
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        # For hybrid commands, ctx.author is the invoker.
        # Permission check is handled by decorator, but an explicit check can be added if needed.
        # if not ctx.author.guild_permissions.manage_nicknames:
        #     await ctx.send("You do not have 'Manage Nicknames' permission.", ephemeral=True)
        #     return

        # Ensure SERVER_ID and USER_ID are valid
        if SERVER_ID is None or USER_ID is None:
            await ctx.send("Nickname change feature is not configured (missing SERVER_ID or USER_ID).", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        success, result_message = await self.perform_nickname_change(SERVER_ID, USER_ID)
        if success:
            await ctx.send(f"Successfully changed nickname for user ID {USER_ID} to **{result_message}**.", ephemeral=True)
        else:
            await ctx.send(f"Failed to change nickname for user ID {USER_ID}. Reason: {result_message}", ephemeral=True)

    @changename_slash_command.error
    async def changename_slash_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have 'Manage Nicknames' permission to use this command.", ephemeral=True)
        else:
            await ctx.send(f"An error occurred: {error}", ephemeral=True)
            print(f"Error in changename_slash_command: {error}")

    async def cog_unload(self):
        self.change_nickname_task.cancel()

async def setup(bot: commands.Bot):
    # It's good practice to ensure necessary config is present before adding the cog
    if not os.getenv('DISCORD_SERVER_ID') or not os.getenv('DISCORD_USER_ID'):
        print("Error: Name Changer Cog not loaded. DISCORD_SERVER_ID or DISCORD_USER_ID not set in .env.")
    else:
        cog = NameChangerCog(bot)
        await bot.add_cog(cog)
        await cog.initialize_tasks() # Initialize tasks after adding the cog
        print("NameChangerCog added and tasks initialized.")
