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
   d. Install the required Python libraries if you haven't already:
      ```bash
      pip install discord.py aiohttp
      ```

### 4. Configure the Bot (`name_changer_bot.py`)

   a. Open the `name_changer_bot.py` file in a text editor.
   b. **Replace `'YOUR_BOT_TOKEN_HERE'` with the bot token you copied in Step 1f.**
      ```python
      BOT_TOKEN = 'YOUR_ACTUAL_BOT_TOKEN'
      ```
   c. **Verify Server and User IDs:**
      The `SERVER_ID` and `USER_ID` are currently hardcoded in the script. If you need to change them, update these lines:
      ```python
      SERVER_ID = 548624354213363733 # Replace with your Server ID if different
      USER_ID = 133358760453210112   # Replace with the target User ID if different
      ```
      To get these IDs:
      - Enable Developer Mode in Discord: User Settings -> Advanced -> Developer Mode (toggle on).
      - To get Server ID: Right-click on your server icon -> Copy ID.
      - To get User ID: Right-click on the target user's name -> Copy ID.

### 5. Run the Bot

   a. Save the changes to `name_changer_bot.py`.
   b. In your terminal or command prompt (still in the bot's directory), run the script:
      ```bash
      python name_changer_bot.py
      ```
   c. If everything is set up correctly, you should see a message like `Bot logged in as YourBotName` in the console.
   d. The bot will then attempt to change the nickname for the specified user and will try again every 24 hours.

### 6. Ensure Bot Permissions on Discord

   a. On your Discord server, go to **Server Settings -> Roles**.
   b. Find the role automatically created for your bot (it usually has the same name as the bot).
   c. **Crucially, ensure this bot's role is positioned higher in the role hierarchy than the role of the user whose nickname you want to change.** If the bot's role is lower, it won't have permission to change the nickname.
   d. Also, verify that the bot's role has the "Manage Nicknames" permission enabled. This should have been set during the bot invitation (Step 2b), but it's good to double-check.

## Customization

*   **Name Source:** The bot now fetches random male names dynamically from the `randomuser.me` API. The internal `MALE_NAMES` list has been removed.
*   **Task Interval:** The task interval is set to 24 hours (`@tasks.loop(hours=24)`). You can change this if needed (e.g., `minutes=1` for testing, but be mindful of Discord API rate limits).

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
