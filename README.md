# Telegram ChatGPT Bot - Step by Step Build

We're building this bot incrementally! See `BUILD_PLAN.md` for the full roadmap.

## Current Step: Step 1 - Basic Echo Bot

### What We're Building
A simple bot that echoes back whatever you send to it. This helps us verify:
- Telegram bot setup is working
- .env file is configured correctly
- We can send/receive messages

### Setup Instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a Telegram Bot Token:**
   - Open Telegram and search for `@BotFather`
   - Send `/newbot` command
   - Follow instructions to create your bot
   - Copy the token you receive

3. **Create `.env` file:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and paste your bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_actual_token_here
   ```

4. **Run the bot:**
   ```bash
   python bot.py
   ```

5. **Test it:**
   - Open Telegram
   - Search for your bot (the name you gave it)
   - Send it a message
   - It should echo back what you said!

### Troubleshooting

- **"TELEGRAM_BOT_TOKEN not found"**: Make sure you created `.env` file with your token
- **Bot not responding**: Check that the bot is running and you're messaging the correct bot
- **Import errors**: Make sure you ran `pip install -r requirements.txt`

### Next Steps

Once this works, we'll move to Step 2: Adding OpenAI integration!
