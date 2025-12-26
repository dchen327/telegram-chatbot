"""
Step 3: Conversation History with Stateful Context
This bot maintains conversation history per user using Responses API with store:true.
"""
import os
import re
import logging
from typing import Dict
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

# Store conversation IDs per user (Telegram user ID -> OpenAI conversation ID)
user_conversations: Dict[int, str] = {}


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
    """Handle text messages by sending them to ChatGPT with stateful context."""
    user_message = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    logger.info(f"Received message from {user_name}: {user_message}")

    try:
        system_instruction = """Format your response using Telegram HTML tags. Available tags:
- <b>bold</b> or <strong>bold</strong>
- <i>italic</i> or <em>italic</em>
- <u>underline</u> or <ins>underline</ins>
- <s>strikethrough</s>, <strike>strikethrough</strike>, or <del>strikethrough</del>
- <span class="tg-spoiler">spoiler</span> or <tg-spoiler>spoiler</tg-spoiler>
- <code>inline code</code>
- <pre>code block</pre> or <pre><code class="language-name">code block</code></pre>
- <blockquote>quotation</blockquote>
- <a href="URL">link</a>
Tags can be nested. Do not use markdown formatting."""
        
        # Get or create conversation ID for this user
        conversation_id = user_conversations.get(user_id)
        
        # If no conversation exists, create one explicitly with system instructions
        if conversation_id is None:
            logger.info(f"Creating new conversation for user {user_id}")
            conversation = openai_client.conversations.create(
                items=[
                    {
                        "type": "message",
                        "role": "system",
                        "content": system_instruction
                    }
                ]
            )
            conversation_id = conversation.id
            user_conversations[user_id] = conversation_id
            logger.info(f"Created conversation_id {conversation_id} for user {user_id}")
        else:
            logger.info(f"Using existing conversation_id {conversation_id} for user {user_id}")
        
        api_params = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "input": user_message,
            "max_output_tokens": 500,
            "conversation": conversation_id
        }
        
        response = openai_client.responses.create(**api_params)
        
        response_text = response.output_text
        
        try:
            await update.message.reply_text(
                response_text,
                parse_mode=ParseMode.HTML
            )
        except Exception as parse_error:
            logger.warning(f"Failed to parse as HTML, sending as plain text: {parse_error}")
            await update.message.reply_text(response_text)
        
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
