# Telegram ChatGPT Bot

A Telegram bot powered by OpenAI's GPT-5-nano with conversation history and web search capabilities.

## Features

- **Chat with AI**: Send messages and get responses from GPT-5-nano
- **Conversation History**: Maintains context across messages per user
- **Web Search**: Use `/search` command to search the web
- **HTML Formatting**: Responses use Telegram HTML tags (`<b>`, `<i>`, `<code>`) for better readability
- **Message Splitting**: Long responses are automatically split into multiple messages (Telegram has a 4096 character limit)
- **Flight-Optimized**: Responses are optimized for in-flight use:
  - URLs and links are automatically removed
  - Source names are preserved (e.g., "nytimes", "reddit") without full URLs
  - No images or media links
- **Access Control**: Restrict bot access to specific users
- **Auto-Reload**: Development server automatically reloads on code changes
- **Commands**:
  - `/start` - Show available commands
  - `/newchat` - Clear conversation history and start fresh
  - `/search [query]` - Search the web for information

## Setup Instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a Telegram Bot Token:**
   - Open Telegram and search for `@BotFather`
   - Send `/newbot` command
   - Follow instructions to create your bot
   - Copy the token you receive

3. **Get an OpenAI API Key:**
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Create an API key in your account settings

4. **Find your Telegram User ID (optional, for access control):**
   - Message `@userinfobot` on Telegram
   - It will reply with your user ID

5. **Create `.env` file:**
   Edit `.env` and add:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-5-nano
   ALLOWED_USER_ID=your_telegram_user_id_here
   ```

   **Required:**
   - `TELEGRAM_BOT_TOKEN` - Your Telegram bot token from BotFather
   - `OPENAI_API_KEY` - Your OpenAI API key

   **Optional:**
   - `OPENAI_MODEL` - Model to use (defaults to `gpt-5-nano`)
   - `ALLOWED_USER_ID` - Restrict bot to specific user (leave unset to allow everyone)

6. **Start local development:**
   ```bash
   # Terminal 1: Start ngrok
   ngrok http 8000
   
   # Terminal 2: Run automated setup (detects ngrok URL and sets webhook automatically)
   python dev_webhook.py
   ```
   
   The script automatically:
   - Detects your ngrok URL
   - Sets the Telegram webhook
   - Starts the webhook server

7. **Test it:**
   - Open Telegram
   - Search for your bot (the name you gave it)
   - Send it a message or use `/start` to see commands

## Usage

- **Regular chat**: Just send a message and the bot will respond
- **Web search**: Use `/search weather in NYC` to search the web
- **Clear history**: Use `/newchat` to start a new conversation

## Development Workflow
### Development Loop
**1. Daily Development Workflow**

**Start local development:**
```bash
# Terminal 1: Start ngrok
ngrok http 8000

# Terminal 2: Run automated setup
python dev_webhook.py
```

The script automatically detects your ngrok URL and sets the webhook for you!

**Make code changes:**
- Edit code in `bot.py` or other files
- The server automatically reloads on file changes (no restart needed!)
- Test on Telegram immediately

**Deploy to production:**
```bash
# Stop local webhook (Ctrl+C in Terminal 2)
# Deploy
./deploy.sh
# Set webhook to Lambda URL (from deployment output)
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<LAMBDA_URL>/webhook"
```

**2. Quick Commands**

Check current webhook:
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Remove webhook:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

## Deployment to AWS Lambda

1. **Install Serverless Framework:**
   ```bash
   npm install -g serverless
   ```

2. **Configure AWS credentials:**
   ```bash
   aws configure
   ```

3. **Deploy:**
   ```bash
   ./deploy.sh
   ```
   
   The script automatically loads environment variables from `.env` file.

4. **Set webhook to Lambda URL:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<LAMBDA_URL>/webhook"
   ```