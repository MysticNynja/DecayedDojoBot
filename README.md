# DecayeDojo Bot

Welcome to the **DecayeDojo Bot**! This bot primarily offers two features:
1.  **Daily Nickname Changer:** Automatically changes a specific user's nickname on your Discord server daily.
2.  **Twitch Live Notifications (Optional):** Monitors registered Twitch channels and sends notifications to a designated channel in your server when they go live or change games.

## Core Features

### 1. Daily Nickname Changer

This bot automatically changes a designated user's nickname on your Discord server daily at **06:01 UTC**.
- It fetches a random male first name from an external API (`randomuser.me`).
- **Configuration:** To use this feature, you **must** set the `DISCORD_SERVER_ID` and `DISCORD_USER_ID` environment variables (see Configuration section below). `DISCORD_SERVER_ID` is the ID of your server, and `DISCORD_USER_ID` is the ID of the user whose nickname will be changed.
- The bot also needs the "Manage Nicknames" permission and its role must be higher than the target user's role on the server for this feature to work.
- **Schedule Timezone:** The name change is scheduled for 06:01 UTC. Please note that this is a fixed UTC time and **will not automatically adjust for local Daylight Saving Time (DST)** changes. If your region observes DST, the local time the bot performs this action will shift by an hour during DST periods. You may need to manually adjust the `hour` in the `name_changer_bot.py` script if a consistent local time is critical year-round.

### 2. Twitch Live Notifications (Optional)

If configured by the bot owner (with Twitch API keys) and a server admin (with a notification channel), this bot can monitor registered Twitch channels.
- When a registered Twitch channel goes live, a notification is sent to the server's designated Twitch updates channel.
- Game changes during a live stream also trigger a notification.
- Server admins use `/twitchadmin set_channel` to define where these notifications appear.
- Server members can use `/twitch notify add <your_twitch_username>` to register their channel for monitoring on that server.
- **Setup Required:** This feature needs `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` to be set in the `.env` file by the bot owner (see Step 1.b and Configuration section). If these are not set, Twitch features will be disabled.

## Setup Instructions

### 1.a. Create a Discord Bot Application and Get a Token

   a. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
   b. Click on "**New Application**" (top right).
   c. Give your application a name (e.g., "DecayeDojoBot") and click "**Create**".
   d. Navigate to the "**Bot**" tab on the left menu.
   e. Click "**Add Bot**" and confirm by clicking "**Yes, do it!**".
   f. Under the "TOKEN" section, click "**Copy**". **This is your bot token. Keep it secret!**
   g. **Enable Privileged Gateway Intents:** On the "Bot" page in the Discord Developer Portal, scroll down to the "Privileged Gateway Intents" section. You need to enable the following intents:
      - Enable "**Server Members Intent**". This is crucial for the bot to find users (e.g., for the nickname changing feature) and to generally function correctly in servers.
      - Enable "**Message Content Intent**". This allows the bot to receive message content, which is important for processing commands.

### 1.b. Create a Twitch Application (OPTIONAL - for future Twitch features)

   If you plan to use future Twitch-related features (like stream notifications, which are not yet re-implemented in this version but the groundwork is being laid), you'll need to register an application on the Twitch Developer Portal. If you only want the nickname changer, you can skip this step and omit `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` from your `.env` file.

   a. Go to the [Twitch Developer Console](https://dev.twitch.tv/console/).
   b. Log in with your Twitch account.
   c. Click on "**Applications**" from the right side menu (or direct link: [https://dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps)).
   d. Click "**+ Register Your Application**".
   e. Fill in the details:
      - **Name:** Give your application a unique name (e.g., "DecayeDojoBot-Notifier").
      - **OAuth Redirect URLs:** For current app access token usage (and potential future webhook usage), `http://localhost` is a common placeholder.
      - **Category:** Choose "Application Integration" or "Chat Bot".
   f. Click "**Create**".
   g. Once created, you'll see your application listed. Click "**Manage**" for the application you just created.
   h. You will find your "**Client ID**" displayed. Copy this value for `TWITCH_CLIENT_ID`.
   i. Click the "**New Secret**" button to generate a "**Client Secret**". Copy this value immediately for `TWITCH_CLIENT_SECRET` and store it securely. **You will not be able to see it again.**

### 2. Python Environment Setup (Using a Virtual Environment - Recommended)

Using a Python virtual environment is highly recommended as it keeps project dependencies isolated and avoids conflicts with other Python projects or your global Python installation.

**a. Navigate to Your Project Directory:**
   Open your terminal or command prompt and navigate to the bot's project folder (e.g., where `name_changer_bot.py` is located).
   ```bash
   cd path/to/your/DecayedDojoBot
   ```
   *(Replace `path/to/your/DecayedDojoBot` with the actual path to the project directory)*

**b. Create the Virtual Environment:**
   Python 3 comes with the `venv` module. It's common to name the virtual environment folder `.venv`.
   ```bash
   python -m venv .venv
   ```
   *(If `python` on your system points to an older Python version, you might need `python3 -m venv .venv` or `py -m venv .venv` if you're on Windows and have the Python Launcher installed.)*
   This command creates a `.venv` folder in your project directory.

**c. Activate the Virtual Environment:**
   *   **Windows (Command Prompt):**
       ```cmd
       .\.venv\Scripts\activate
       ```
   *   **Windows (PowerShell):**
       ```powershell
       .\.venv\Scripts\Activate.ps1
       ```
       *(If you get an error about script execution being disabled in PowerShell, you might need to run `Set-ExecutionPolicy Unrestricted -Scope Process` first for that session, then try activating again.)*
   *   **macOS and Linux (bash/zsh):**
       ```bash
       source .venv/bin/activate
       ```
   Your terminal prompt should now change, often showing `(.venv)` at the beginning, indicating the virtual environment is active.

**d. Install Dependencies:**
   With the virtual environment active, install the required Python packages using the `requirements.txt` file:
   ```bash
   pip install -r requirements.txt
   ```
   This installs dependencies specifically into your virtual environment.

**e. (For VS Code Users) Configure the Python Interpreter:**
   If you use Visual Studio Code:
   1. Open your project folder in VS Code.
   2. Open the Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P` on Mac).
   3. Type "**Python: Select Interpreter**" and press Enter.
   4. VS Code should automatically detect and list the interpreter from your `.venv` folder (e.g., `Python X.Y.Z ('.venv': venv)`). Select this interpreter.
   5. If not listed, choose "Enter interpreter path..." and navigate to:
      - Windows: `.venv\Scripts\python.exe`
      - macOS/Linux: `.venv/bin/python`
   This ensures VS Code uses the virtual environment for running, debugging, and linting.

**f. Running the Bot:**
   Whenever you want to run the bot, ensure your virtual environment is activated in your terminal first, then run:
   ```bash
   python name_changer_bot.py
   ```

**g. Deactivating the Virtual Environment:**
   When you're done working in that terminal session, you can deactivate the virtual environment by typing:
   ```bash
   deactivate
   ```

**h. Ignoring the Virtual Environment Folder (Git):**
   The `.gitignore` file in this project is already configured to ignore the `.venv/` directory, so you don't accidentally commit the entire virtual environment to version control.

**Note on Helper Scripts:**
For a quicker initial setup of the virtual environment and dependency installation, you can also use the provided helper scripts (`setup_venv.bat` for Windows, `setup_venv.sh` for macOS/Linux). You will still need to activate the environment manually as described above to run the bot.

### 3. Invite the Bot to Your Server

   a. Go back to the "**General Information**" tab in the Discord Developer Portal (or stay on the "Bot" tab, then go to "OAuth2" -> "URL Generator").
   b. In the "OAuth2 URL Generator":
      - Under "SCOPES", select `bot`.
      - Under "BOT PERMISSIONS", select:
         - `Manage Nicknames` (required for the daily nickname changer)
         - `Send Messages` (if you want the bot to send any kind of messages/confirmations - good to have)
         - `Read Messages/View Channels` (usually enabled by default with `bot` scope)
   c. Copy the generated URL at the bottom.
   d. Paste the URL into your web browser, select the server you want to add the bot to, and click "**Authorize**".

### 4. Configure the Bot (Using a `.env` File)

   The recommended way to configure the bot is by creating a `.env` file in the same directory as `name_changer_bot.py`. This file will store your sensitive credentials and settings. The script uses `python-dotenv` to automatically load these variables.

   **Create a `.env` file with the following content, replacing the placeholder values with your actual credentials:**

   ```env
   # --- Discord Bot General ---
   DISCORD_BOT_TOKEN=your_actual_discord_bot_token

   # --- Daily Nickname Changer Feature ---
   # ID of the Discord server where nickname changes occur
   DISCORD_SERVER_ID=your_discord_server_id
   # ID of the user whose nickname will be changed daily
   DISCORD_USER_ID=the_user_id_whose_nickname_will_be_changed

   # --- Twitch Live Notifications Feature (OPTIONAL) ---
   # To enable Twitch features, get these from Step 1.b.
   # If these are not set, Twitch features will be disabled.
   TWITCH_CLIENT_ID=your_twitch_app_client_id_here
   TWITCH_CLIENT_SECRET=your_twitch_app_client_secret_here
   ```

   **Important Security Note:**
   Ensure your `.env` file is **never** committed to version control (e.g., Git). If you are using Git, add `.env` to your `.gitignore` file (see Step 5).

   **How to get specific IDs:**
   *   `DISCORD_BOT_TOKEN`: See Step 1.a.
   *   `DISCORD_SERVER_ID` & `DISCORD_USER_ID`: (Required for Nickname Changer). For instructions on enabling Developer Mode and copying IDs, see Step 1.a.
   *   `TWITCH_CLIENT_ID` & `TWITCH_CLIENT_SECRET`: See Step 1.b. (Optional, for Twitch features).
      - Enable Developer Mode in Discord: User Settings -> App Settings -> Advanced -> Developer Mode (toggle on). (This line is slightly generic, the specific ID copying is for Discord IDs)
      - To get Discord Server ID: Right-click on your server icon -> Copy ID.
      - To get Discord User ID (for name changing feature): Right-click on the target user's name -> Copy ID.

   **Alternative: Setting System Environment Variables:**
   If you prefer not to use a `.env` file, you can set these variables directly in your operating system's environment. The script will still pick them up. `python-dotenv` loads variables from `.env` if present, but system-set variables usually take precedence if they conflict.
   The following variables are needed:

   *   `DISCORD_BOT_TOKEN` (Required)
   *   `DISCORD_SERVER_ID` (Required for Nickname Changer)
   *   `DISCORD_USER_ID` (Required for Nickname Changer)
   *   `TWITCH_CLIENT_ID` (Optional, for Twitch Live Notifications feature)
   *   `TWITCH_CLIENT_SECRET` (Optional, for Twitch Live Notifications feature)

   Here's how you can set them if you choose this method:

   **For Linux/macOS (in terminal for the current session):**
   ```bash
   export DISCORD_BOT_TOKEN="your_actual_bot_token"
   export DISCORD_SERVER_ID="your_server_id"
   export DISCORD_USER_ID="your_user_id_for_name_change"
   # Optionally, for Twitch features:
   # export TWITCH_CLIENT_ID="your_twitch_client_id"
   # export TWITCH_CLIENT_SECRET="your_twitch_client_secret"
   ```
   To make them permanent, add these lines to your shell's profile file (e.g., `~/.bashrc`, `~/.zshrc`).

   **For Windows (in Command Prompt for the current session):**
   ```cmd
   set DISCORD_BOT_TOKEN=your_actual_bot_token
   set DISCORD_SERVER_ID=your_server_id
   set DISCORD_USER_ID=your_user_id_for_name_change
   REM Optionally, for Twitch features:
   REM set TWITCH_CLIENT_ID=your_twitch_client_id
   REM set TWITCH_CLIENT_SECRET=your_twitch_client_secret
   ```
   **For Windows (in PowerShell for the current session):**
   ```powershell
   $env:DISCORD_BOT_TOKEN="your_actual_bot_token"
   $env:DISCORD_SERVER_ID="your_server_id"
   $env:DISCORD_USER_ID="your_user_id_for_name_change"
   # Optionally, for Twitch features:
   # $env:TWITCH_CLIENT_ID="your_twitch_client_id"
   # $env:TWITCH_CLIENT_SECRET="your_twitch_client_secret"
   ```
   To set them permanently on Windows, search for "environment variables" in the Start menu to edit system environment variables.

   The script will print error messages and exit if required Discord variables are not found. Twitch variables are optional; if missing, Twitch-related functionality will be disabled.

### 5. Run the Bot

   a. Ensure you have configured the bot as described in Step 4 (ideally by creating a `.env` file) and that your virtual environment (from Step 2) is active.
   b. In your terminal or command prompt (still in the bot's directory), run the script:
      ```bash
      python name_changer_bot.py
      ```
   c. If everything is set up correctly, you should see messages like `Bot logged in as YourBotName` in the console, followed by the daily name changer task starting.
   d. The bot will then perform its daily nickname change at the scheduled UTC time.

### 6. Secure Your Credentials (`.gitignore`)

   If you are using Git for version control, it's crucial to prevent your `.env` file (which contains your secret tokens) from being committed. The `.gitignore` file in this project is already configured to ignore `.env` and `*.env` files.

### 7. Ensure Bot Permissions on Discord

   a. On your Discord server, go to **Server Settings -> Roles**.
   b. Find the role automatically created for your bot (it usually has the same name as the bot).
   c. **Crucially, ensure this bot's role is positioned higher in the role hierarchy than the role of the user whose nickname you want to change.** If the bot's role is lower, it won't have permission to change the nickname.
   d. Also, verify that the bot's role has the "Manage Nicknames" permission enabled. This should have been set during the bot invitation (Step 3), but it's good to double-check.

## Bot Commands

### Nickname Management

*   **`/changename`**
    *   **Description:** Manually triggers a nickname change for the user specified by `DISCORD_USER_ID` on the server specified by `DISCORD_SERVER_ID` in your `.env` configuration.
    *   **Usage:** Type `/` in any channel the bot can see, and Discord will show a list of available slash commands. Select `changename` from the list and press Enter.
    *   **Permissions:** To use this command, you must have the "Manage Nicknames" permission in the server. The bot will inform you if you lack this permission.
    *   **Note:** This is in addition to the automatic daily nickname change. Slash commands may take up to an hour to appear in all servers after the bot is updated or restarted, unless synced to a specific development guild.

### Twitch Notifications

#### Admin Commands
*   **`/twitchadmin set_channel channel:<#channel>`**
    *   **Description:** Sets or updates the specific Discord channel where Twitch live notifications will be sent for this server. Only one notification channel can be set per server.
    *   **Usage:** `/twitchadmin set_channel channel:#your-twitch-updates`
    *   **Permissions Required:** Manage Server (or Administrator).

#### User Commands
*   **`/twitch notify add twitch_username:<username>`**
    *   **Description:** Registers a Twitch username to send live notifications to this server's configured Twitch updates channel.
    *   **Usage:** `/twitch notify add twitch_username:your_twitch_login_name`
    *   **Note:** Uses the Twitch login name (the one in the URL), not necessarily the display name. Requires an admin to have first set a notification channel using `/twitchadmin set_channel`.

*   **`/twitch notify remove twitch_username:<username>`**
    *   **Description:** Unregisters a Twitch username from live notifications on this server.
    *   **Usage:** `/twitch notify remove twitch_username:your_twitch_login_name`

*   **`/twitch notify list`**
    *   **Description:** Lists all Twitch channels currently registered for live notifications on this server.
    *   **Usage:** `/twitch notify list`

## Customization

*   **Name Source (Daily Nickname Changer):** The bot fetches random male names dynamically from the `randomuser.me` API for the daily name change feature.
*   **Task Intervals:**
    *   Daily Name Change: Runs daily at 06:01 UTC (see feature description above). This can be adjusted in `name_changer_bot.py` by modifying the `@tasks.loop(time=...)` decorator for the `change_nickname_task` function.
    *   Twitch Status Polling: Runs approximately every 1 minute (`@tasks.loop(minutes=1)`). This can also be adjusted in the script if needed (be mindful of API rate limits for Twitch).

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