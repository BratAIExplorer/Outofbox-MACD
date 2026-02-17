# How to Setup Telegram Bot for Research Alerts

## 1. Get Your Bot Token (The Broker)
1.  Open Telegram app and search for **@BotFather** (it has a blue verified tick).
2.  Click **Start**.
3.  Send the command: `/newbot`
4.  **BotFather** will ask for a name. Enter something like: `Arun Research Bot`
5.  It will ask for a username (must end in 'bot'). Enter something like: `ArunEquityResearch_bot`
6.  **Success!** BotFather will give you a long string of characters called the **HTTP API Token** (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`).
    *   **Copy this Token**. We need it for the `.env` file.

## 2. Get Your Channel ID (The Destination)
1.  **Create a Public Channel** (if you haven't already).
2.  **Add your new bot** (e.g., `@ArunEquityResearch_bot`) as an **Administrator** to your channel.
    *   Go to Channel Info > Administrators > Add Admin > Search for your bot.
    *   *Note: This is required for the bot to post messages.*
3.  **Find the Channel ID**:
    *   **Method A (Easiest)**: Forward a message from your channel to the bot named **@userinfobot**. It will reply with the ID (usually starts with `-100`, e.g., `-1001234567890`).
    *   **Method B (Browser)**: Open your channel in Telegram Web. The URL will look like `web.telegram.org/z/#-1001234567890`. The ID is the number after the `#`.
    
## 3. Update Your `.env` File
Add these lines to your `.env` file inside `c:\Antigravity\OutoftheBox\.env`:

```env
# ... your existing API keys ...

TELEGRAM_BOT_TOKEN=your_token_from_step_1
TELEGRAM_CHANNEL_ID=your_channel_id_from_step_2
```
