# Discord Daily Name Changer Bot

This bot changes a specified user's nickname on a Discord server to a random male name every 24 hours.

## Setup Instructions

### 1. Create a Discord Bot Application and Get a Token

   a. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
   b. Click on "**New Application**" (top right).
   c. Give your application a name (e.g., "NameChangerBot") and click "**Create**".
   d. Navigate to the "**Bot**" tab on the left menu.
   e. Click "**Add Bot**" and confirm by clicking "**Yes, do it!**".
   f. Under the "TOKEN" section, click "**Copy**". **This is your bot token. Keep it secret!**
   g. **Enable Privileged Gateway Intents:**
      - Scroll down on the "Bot" page to the "Privileged Gateway Intents" section.
      - Enable "**Server Members Intent**". This is crucial for the bot to find users and change nicknames.

### 1.b. Create a Twitch Application (for Streamer Notifications)

   If you plan to use the Twitch streamer notification feature, you'll need to register an application on the Twitch Developer Portal to get a Client ID and Client Secret.

   a. Go to the [Twitch Developer Console](https://dev.twitch.tv/console/).
   b. Log in with your Twitch account.
   c. Click on "**Applications**" from the right side menu (or direct link: [https://dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps)).
   d. Click "**+ Register Your Application**".
   e. Fill in the details:
      - **Name:** Give your application a unique name (e.g., "MyDiscordTwitchNotifier").
      - **OAuth Redirect URLs:** For this bot's current features (using App Access Tokens for polling), this can be `http://localhost`. If you later implement user authentication flows or EventSub webhooks, you'll need to update this.
      - **Category:** Choose "Application Integration" or "Chat Bot".
   f. Click "**Create**".
   g. Once created, you'll see your application listed. Click "**Manage**" for the application you just created.
   h. You will find your "**Client ID**" displayed. Copy this value.
   i. Click the "**New Secret**" button to generate a "**Client Secret**". Copy this value immediately and store it securely. **You will not be able to see it again.**

### 2. Invite the Bot to Your Server

   a. Go back to the "**General Information**" tab (or stay on the "Bot" tab, then go to "OAuth2" -> "URL Generator").
   b. In the "OAuth2 URL Generator":
      - Under "SCOPES", select `bot`.
      - Under "BOT PERMISSIONS", select:
         - `Manage Nicknames` (to change nicknames)
         - `Send Messages` (optional, if you want the bot to confirm actions in a channel)
         - `Read Messages/View Channels` (usually enabled by default with `bot` scope, allows bot to see channels)
   c. Copy the generated URL at the bottom.
   d. Paste the URL into your web browser, select the server you want to add the bot to, and click "**Authorize**".

### 3. Prepare Your Python Environment

   a. Ensure you have Python 3.7 or higher installed.
   b. Open a terminal or command prompt.
   c. Navigate to the directory where you've saved `name_changer_bot.py`.
   d. Install the required Python libraries using the `requirements.txt` file:
      ```bash
      pip install -r requirements.txt
      ```
      This file lists all the necessary Python packages for the bot to run.

### 4. Configure the Bot (Using a `.env` File)

   The recommended way to configure the bot is by creating a `.env` file in the same directory as `name_changer_bot.py`. This file will store your sensitive credentials and settings. The script uses `python-dotenv` to automatically load these variables.

   **Create a `.env` file with the following content, replacing the placeholder values with your actual credentials:**

   ```env
   DISCORD_BOT_TOKEN=your_actual_discord_bot_token
   DISCORD_SERVER_ID=your_discord_server_id
   DISCORD_USER_ID=your_discord_user_id_for_name_change
   TWITCH_CLIENT_ID=your_twitch_app_client_id
   TWITCH_CLIENT_SECRET=your_twitch_app_client_secret
   ```

   **Important Security Note:**
   Ensure your `.env` file is **never** committed to version control (e.g., Git). If you are using Git, add `.env` to your `.gitignore` file (see Step 6).

   **How to get specific IDs:**
   *   `DISCORD_BOT_TOKEN`: See Step 1.a.
   *   `TWITCH_CLIENT_ID` & `TWITCH_CLIENT_SECRET`: See Step 1.b.
   *   `DISCORD_SERVER_ID` & `DISCORD_USER_ID`:
      - Enable Developer Mode in Discord: User Settings -> Advanced -> Developer Mode (toggle on).
      - To get Server ID: Right-click on your server icon -> Copy ID.
      - To get User ID (for name changing feature): Right-click on the target user's name -> Copy ID.

   **Alternative: Setting System Environment Variables:**
   If you prefer not to use a `.env` file, you can set these variables directly in your operating system's environment. The script will still pick them up. `python-dotenv` loads variables from `.env` if present, but system-set variables usually take precedence if they conflict.
   The following variables are needed:

   *   `DISCORD_BOT_TOKEN`
   *   `DISCORD_SERVER_ID`
   *   `DISCORD_USER_ID`
   *   `TWITCH_CLIENT_ID`
   *   `TWITCH_CLIENT_SECRET`

   Here's how you can set them if you choose this method:

   **For Linux/macOS (in terminal for the current session):**
   ```bash
   export DISCORD_BOT_TOKEN="your_actual_bot_token"
   export DISCORD_SERVER_ID="your_server_id"
   export DISCORD_USER_ID="your_user_id_for_name_change"
   export TWITCH_CLIENT_ID="your_twitch_client_id"
   export TWITCH_CLIENT_SECRET="your_twitch_client_secret"
   ```
   To make them permanent, add these lines to your shell's profile file (e.g., `~/.bashrc`, `~/.zshrc`).

   **For Windows (in Command Prompt for the current session):**
   ```cmd
   set DISCORD_BOT_TOKEN=your_actual_bot_token
   set DISCORD_SERVER_ID=your_server_id
   set DISCORD_USER_ID=your_user_id_for_name_change
   set TWITCH_CLIENT_ID=your_twitch_client_id
   set TWITCH_CLIENT_SECRET=your_twitch_client_secret
   ```
   **For Windows (in PowerShell for the current session):**
   ```powershell
   $env:DISCORD_BOT_TOKEN="your_actual_bot_token"
   $env:DISCORD_SERVER_ID="your_server_id"
   $env:DISCORD_USER_ID="your_user_id_for_name_change"
   $env:TWITCH_CLIENT_ID="your_twitch_client_id"
   $env:TWITCH_CLIENT_SECRET="your_twitch_client_secret"
   ```
   To set them permanently on Windows, search for "environment variables" in the Start menu to edit system environment variables.

   The script will print error messages and exit if these required variables are not found (either in `.env` or system environment).

### 5. Run the Bot

   a. Ensure you have configured the bot as described in Step 4 (ideally by creating a `.env` file).
   b. In your terminal or command prompt (still in the bot's directory), run the script:
      ```bash
      python name_changer_bot.py
      ```
   c. If everything is set up correctly, you should see messages like `Bot logged in as YourBotName` in the console, followed by task startup messages.
   d. The bot will then perform its configured tasks (changing nickname, polling Twitch).

### 6. Secure Your Credentials (`.gitignore`)

   If you are using Git for version control, it's crucial to prevent your `.env` file (which contains your secret tokens) from being committed. Create a file named `.gitignore` in the root of your project (if it doesn't already exist) and add the following line to it:

   ```
   .env
   ```
   This will tell Git to ignore the `.env` file.
   Also, ensure the `twitch_follows.json` file (which stores followed channels) is not accidentally committed if it contains server-specific data you don't want public. You might add:
   ```
   twitch_follows.json
   ```

### 7. Ensure Bot Permissions on Discord

   a. On your Discord server, go to **Server Settings -> Roles**.
   b. Find the role automatically created for your bot (it usually has the same name as the bot).
   c. **Crucially, ensure this bot's role is positioned higher in the role hierarchy than the role of the user whose nickname you want to change (for the name changing feature).** If the bot's role is lower, it won't have permission to change the nickname.
   d. Also, verify that the bot's role has the "Manage Nicknames" permission enabled. This should have been set during the bot invitation (Step 2b), but it's good to double-check.
   e. For Twitch notifications, ensure the bot has "Send Messages" and "Embed Links" permissions in the designated notification channels.

## Bot Commands
The bot responds to the following commands:

*   `!followtwitch <twitch_username> [#discord_channel (optional)]`
    *   Follows a Twitch streamer for live notifications.
    *   Requires "Manage Guild" permission.
    *   If `#discord_channel` is omitted, notifications go to the current channel.
*   `!unfollowtwitch <twitch_username>`
    *   Unfollows a Twitch streamer.
    *   Requires "Manage Guild" permission.
*   `!listtwitch`
    *   Lists all currently followed Twitch streamers and their notification channels.

## Customization

*   **Name Source (Daily Name Changer):** The bot fetches random male names dynamically from the `randomuser.me` API for the daily name change feature.
*   **Task Intervals:**
    *   Daily Name Change: Runs once every 24 hours (`@tasks.loop(hours=24)`).
    *   Twitch Status Polling: Runs every 2 minutes (`@tasks.loop(minutes=2)`).
    *   These can be adjusted in `name_changer_bot.py` if needed (be mindful of API rate limits).

## Troubleshooting

*   **"Server with ID ... not found"**: Double-check `SERVER_ID` in the script.
*   **"User with ID ... not found on server ..."**: Ensure the `USER_ID` is correct and the user is a member of the server.
*   **"Bot does not have permission..."**:
    *   Check the bot's role hierarchy (Step 6c).
    *   Ensure the "Manage Nicknames" permission is enabled for the bot's role (Step 6d).
    *   Ensure "Server Members Intent" is enabled in the Discord Developer Portal (Step 1g).
*   **Bot doesn't start / No login message**:
    *   Verify `BOT_TOKEN` is correct and doesn't have typos.
    *   Ensure `discord.py` is installed correctly.
