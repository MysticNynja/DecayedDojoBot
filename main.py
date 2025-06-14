
import discord
from discord.ext import commands
import os
import sys
from dotenv import load_dotenv
from discord import app_commands # For CommandTree

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
    int(SERVER_ID_STR) # Validate that it's an integer
except ValueError:
    print("Error: DISCORD_SERVER_ID environment variable is not a valid integer.", file=sys.stderr)
    sys.exit(1)

try:
    int(USER_ID_STR) # Validate that it's an integer
except ValueError:
    print("Error: DISCORD_USER_ID environment variable is not a valid integer.", file=sys.stderr)
    sys.exit(1)

# Twitch Configuration (Optional - features disabled if not set)
# These are loaded here for initial validation, cogs also access them via os.getenv
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
    print("Warning: TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET not set. Twitch features will be disabled in cogs.", file=sys.stderr)

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
        # setup_hook is called before on_ready.
        # Cog loading and other async setup can happen here or in on_ready.
        # For this project, load_extensions is called in on_ready.
        pass

    async def load_extensions(self):
        print("Loading extensions...")
        extensions = [
            "cogs.name_changer.name_changer_cog",
            "cogs.twitch_notifications.twitch_notifications_cog"
        ]
        for extension in extensions:
            try:
                await self.load_extension(extension)
                print(f"Loaded {extension} successfully.")
            except Exception as e:
                print(f"Failed to load extension {extension}: {e}", file=sys.stderr)

# Create bot instance after all command definitions
bot = CustomBot()

# Features below are moved to cogs
# --- Twitch API Helper Functions ---
# --- Name Changer Feature ---
# --- Twitch Notification Task ---

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
    # It's better to call load_extensions before diagnosing the tree,
    # so commands from cogs are included in the diagnostic.
    await bot.load_extensions() # Changed from self.load_extensions to bot.load_extensions

    all_commands_on_tree = bot.tree.get_commands()
    print(f"Total top-level items found in bot.tree: {len(all_commands_on_tree)}")
    for cmd_or_group in all_commands_on_tree:
        print(f"  Item: {cmd_or_group.name}, Type: {type(cmd_or_group)}")
        if isinstance(cmd_or_group, app_commands.Group):
            group_sub_commands = cmd_or_group.commands
            print(f"    Sub-commands in group '{cmd_or_group.name}': {[c.name for c in group_sub_commands]}")
    print("--- End diagnostic prints ---")

    # Sync slash commands
    try:
        # Extensions are now loaded above.
        guild_id_env = os.getenv('DISCORD_TEST_GUILD_ID')
        if guild_id_env:
            try:
                guild_obj = discord.Object(id=int(guild_id_env))
                print(f"Attempting to sync to specific guild: {guild_id_env}")
                bot.tree.copy_global_to(guild=guild_obj)
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
# All slash commands now live in their respective cogs.

# Add this at the very bottom of the file
if __name__ == "__main__":
    print("Starting bot...")
    # Ensure the bot instance has the load_extensions method if it's called in on_ready or setup_hook
    # For CustomBot, it's part of its methods.
    bot.run(BOT_TOKEN)
