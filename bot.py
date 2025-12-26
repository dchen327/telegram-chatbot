"""
Step 2: OpenAI Integration
This bot connects users to ChatGPT API.
"""
import os
import re
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

openai_client = None


def convert_markdown_to_html(text: str) -> str:
    """Convert common markdown patterns to HTML for Telegram."""
    # Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Convert *italic* (not already in bold) to <i>italic</i>
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
    # Convert `code` to <code>code</code>
    text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
    return text


async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages by sending them to ChatGPT."""
    user_message = update.message.text
    user_name = update.effective_user.first_name

    logger.info(f"Received message from {user_name}: {user_message}")

    try:
        response = openai_client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            input=user_message,
            max_output_tokens=500
        )
        
        await update.message.reply_text(
            response.output_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        logger.info(f"Sent response to {user_name}")
    except Exception as e:
        logger.error(f"Error calling OpenAI: {e}")
        await update.message.reply_text("Sorry, I encountered an error. Please try again.")


def main():
    """Start the bot"""
    global openai_client
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables!")
        return

    openai_client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized")

    logger.info("Creating bot application...")
    application = Application.builder().token(token).build()

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, chat_message))

    logger.info("Starting bot in polling mode...")
    logger.info("Press Ctrl+C to stop")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
