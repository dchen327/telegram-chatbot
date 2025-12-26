# Telegram ChatGPT Bot

A Telegram bot powered by OpenAI's GPT-5-nano with conversation history and web search capabilities.

## Features

- **Chat with AI**: Send messages and get responses from GPT-5-nano
- **Conversation History**: Maintains context across messages per user
- **Web Search**: Use `/search` command to search the web
- **HTML Formatting**: Responses use Telegram HTML tags for better readability
- **Access Control**: Restrict bot access to specific users
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

6. **Choose your development mode:**

   **Option A: Polling Mode (Simple, for quick testing)**
   ```bash
   python bot.py
   ```
   Or with auto-reload:
   ```bash
   python dev.py
   ```

   **Option B: Webhook Mode (Recommended, matches production)**
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

### How Webhooks Work

Telegram sends updates to **one webhook URL at a time**. This means:
- ✅ **No duplicates**: If webhook is set to ngrok → only local receives updates
- ✅ **No duplicates**: If webhook is set to Lambda → only Lambda receives updates
- ⚠️ **Duplicates possible**: If polling mode runs while webhook is set (polling actively fetches updates)

### Development Loop

**1. Initial Setup (First Time)**
```bash
# Deploy to Lambda
./deploy.sh
# Note the Lambda URL from output
```

**2. Daily Development Workflow**

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
- Restart `local_webhook.py` (Ctrl+C and run again)
- Test on Telegram immediately

**Deploy to production:**
```bash
# Stop local webhook (Ctrl+C in Terminal 2)
# Deploy
./deploy.sh
# Set webhook to Lambda URL (from deployment output)
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<LAMBDA_URL>/webhook"
```

**3. Quick Commands**

Check current webhook:
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Remove webhook (use polling mode):
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

### Alternative: Polling Mode for Quick Testing

For quick local testing without webhook setup:
```bash
# Remove webhook first
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
# Run with auto-reload
python dev.py
```

**Note:** Polling mode is simpler but doesn't match production behavior. Use webhook mode when testing production-like scenarios.

## Deployment to AWS Lambda

1. **Install Serverless Framework:**
   ```bash
   npm install -g serverless
   npm install --save-dev serverless-python-requirements
   ```

2. **Configure AWS credentials:**
   ```bash
   aws configure
   ```

3. **Set environment variables:**
   ```bash
   export TELEGRAM_BOT_TOKEN=your_token
   export OPENAI_API_KEY=your_key
   export OPENAI_MODEL=gpt-5-nano  # optional
   export ALLOWED_USER_ID=your_user_id  # optional
   ```

4. **Deploy:**
   ```bash
   ./deploy.sh
   ```

5. **Set webhook to Lambda URL:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<LAMBDA_URL>/webhook"
   ```

## Troubleshooting

- **"TELEGRAM_BOT_TOKEN not found"**: Make sure you created `.env` file with your token
- **"OPENAI_API_KEY not found"**: Add your OpenAI API key to `.env`
- **Bot not responding**: Check that the bot is running and you're messaging the correct bot
- **"Sorry, this bot is not available"**: Check your `ALLOWED_USER_ID` matches your Telegram user ID
- **Import errors**: Make sure you ran `pip install -r requirements.txt`
- **Duplicate responses**: Make sure only one bot instance is running (local OR Lambda, not both)
