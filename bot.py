import os
import logging
from typing import Dict
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Only load .env file in local development (not in Lambda)
# Lambda uses environment variables from serverless.yml
if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
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

# Allowed user ID (set via ALLOWED_USER_ID env var)
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")
if ALLOWED_USER_ID:
    ALLOWED_USER_ID = int(ALLOWED_USER_ID)


def is_user_allowed(user_id: int) -> bool:
    """Check if user is allowed to use the bot."""
    if ALLOWED_USER_ID is None:
        return True  # If not set, allow everyone (for development)
    return user_id == ALLOWED_USER_ID

SYSTEM_INSTRUCTION = """You are a helpful AI assistant for Telegram.

ABSOLUTE RULES (NEVER BREAK THESE):
1. NEVER include URLs, links, or images. Not even from search results. Not even in parentheses. No exceptions.
2. NEVER use markdown syntax. No **, no *, no `, no #, no ##, no [text](url), no ![image](url).
3. Always summarize information in your own words. Do not copy raw output from search results.
4. NEVER ask for clarification or confirmation. Proceed immediately with the requested action and provide results.

FORMAT RULES:
- Use ONLY HTML tags for formatting: <b>bold</b>, <i>italic</i>, <code>code</code>
- For headers, use <b>Header Text</b> on its own line
- For lists, use plain dashes: - item

CORRECT list formatting:
1. <b>Vegetables</b>:
   - Daikon radish for sweetness.
   - Bok choy for crunch.

WRONG (never do this):
1. **Vegetables**:
   - Daikon radish ([source](https://example.com))

Be concise but thorough. Provide complete, helpful answers."""


def get_or_create_conversation(user_id: int) -> str:
    """Get existing conversation ID or create a new one for the user."""
    conversation_id = user_conversations.get(user_id)
    
    if conversation_id is None:
        logger.info(f"Creating new conversation for user {user_id}")
        conversation = openai_client.conversations.create(
            items=[
                {
                    "type": "message",
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION
                }
            ]
        )
        conversation_id = conversation.id
        user_conversations[user_id] = conversation_id
        logger.info(f"Created conversation_id {conversation_id} for user {user_id}")
    
    return conversation_id


async def send_to_openai(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                         message: str, use_web_search: bool = False):
    """Send message to OpenAI and reply with the response."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try:
        conversation_id = get_or_create_conversation(user_id)
        
        api_params = {
            "model": os.getenv("OPENAI_MODEL", "gpt-5-nano"),
            "input": message,
            "max_output_tokens": 5000,
            "conversation": conversation_id,
            "reasoning": {"effort": "low"}
        }
        
        if use_web_search:
            api_params["tools"] = [{"type": "web_search"}]
        
        response = openai_client.responses.create(**api_params)
        response_text = response.output_text
        if not response_text:
            logger.warning(f"Empty response. Full response: {response}")
        
        try:
            await update.message.reply_text(response_text, parse_mode=ParseMode.HTML)
        except Exception as parse_error:
            logger.warning(f"Failed to parse as HTML, sending as plain text: {parse_error}")
            await update.message.reply_text(response_text)
        
        logger.info(f"Sent response to {user_name}")
    except Exception as e:
        logger.error(f"Error calling OpenAI: {e}")
        await update.message.reply_text("Sorry, I encountered an error. Please try again.")


async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages by sending them to ChatGPT."""
    user_id = update.effective_user.id
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        await update.message.reply_text("Sorry, this bot is not available.")
        return
    
    user_message = update.message.text
    logger.info(f"Received message from {update.effective_user.first_name}: {user_message}")
    await send_to_openai(update, context, user_message)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        await update.message.reply_text("Sorry, this bot is not available.")
        return
    
    await update.message.reply_text(
        "Hello! I'm your AI assistant. Send me a message and I'll respond.\n\n"
        "<b>Commands:</b>\n"
        "/newchat - Start a new conversation\n"
        "/search [query] - Search the web",
        parse_mode=ParseMode.HTML
    )


async def newchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newchat command - clears conversation history."""
    user_id = update.effective_user.id
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        await update.message.reply_text("Sorry, this bot is not available.")
        return
    if user_id in user_conversations:
        del user_conversations[user_id]
        await update.message.reply_text("Conversation cleared! Starting fresh.")
        logger.info(f"Cleared conversation for user {user_id}")
    else:
        await update.message.reply_text("No conversation to clear. Send me a message to start!")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command - performs web search."""
    user_id = update.effective_user.id
    if not is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        await update.message.reply_text("Sorry, this bot is not available.")
        return
    
    query = " ".join(context.args) if context.args else None
    
    if not query:
        await update.message.reply_text("Usage: /search [your query]\nExample: /search weather in NYC")
        return
    
    logger.info(f"Search request from {update.effective_user.first_name}: {query}")
    # Add instructions: proceed immediately without asking for confirmation
    search_prompt = f"{query}\n\n(Do NOT ask for clarification or confirmation. Proceed immediately with the search and provide results. Do NOT include any URLs or links in your response.)"
    await send_to_openai(update, context, search_prompt, use_web_search=True)


def create_application():
    """Create and configure the bot application."""
    global openai_client
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables!")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables!")

    openai_client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized")
    
    if ALLOWED_USER_ID:
        logger.info(f"Access restricted to user ID: {ALLOWED_USER_ID}")
    else:
        logger.warning("ALLOWED_USER_ID not set - bot is open to everyone!")

    logger.info("Creating bot application...")
    application = Application.builder().token(token).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("newchat", newchat_command))
    application.add_handler(CommandHandler("search", search_command))
    
    # Message handler (for non-command messages)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, chat_message))

    return application
