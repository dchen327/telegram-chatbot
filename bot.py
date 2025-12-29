import os
import sys
import logging
import re
from functools import wraps
from typing import Dict, List
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.constants import ChatAction, ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Only load .env file in local development (not in Lambda)
# Lambda uses environment variables from serverless.yml
if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
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


def require_auth(func):
    """Decorator to check user authorization before executing handler."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_user_allowed(update.effective_user.id):
            await update.message.reply_text("Sorry, this bot is not available.")
            return
        await func(update, context)
    return wrapper


def split_message(text: str, max_length: int = 4096) -> List[str]:
    """Split a long message into chunks that fit within Telegram's limit."""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        # If line itself is too long, split by words
        if len(line) > max_length:
            # Save current chunk if exists
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # Split long line by words
            for word in line.split(' '):
                if len(current_chunk) + len(word) + 1 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = word
                else:
                    current_chunk = f"{current_chunk} {word}".strip()
        else:
            # Check if adding this line would exceed limit
            separator = '\n' if current_chunk else ''
            if len(current_chunk) + len(separator) + len(line) > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk = f"{current_chunk}{separator}{line}".strip()
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def clean_response(text: str) -> str:
    """Minimal processing - remove markdown links and URLs, keep source names."""
    # Remove markdown links [text](url) - keep just the text (source name)
    markdown_links = re.findall(r'\[([^\]]+)\]\([^\)]+\)', text)
    if markdown_links:
        logger.info(f"Removed {len(markdown_links)} markdown link(s): {markdown_links}")
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Remove raw URLs (http://, https://, www.) - but preserve HTML tags
    urls = re.findall(r'https?://[^\s<\)]+|www\.[^\s<\)]+', text)
    if urls:
        logger.info(f"Removed {len(urls)} URL(s): {urls[:3]}{'...' if len(urls) > 3 else ''}")
    text = re.sub(r'https?://[^\s<\)]+', '', text)
    text = re.sub(r'www\.[^\s<\)]+', '', text)
    
    return text.strip()

SYSTEM_INSTRUCTION = """You are a helpful AI assistant for Telegram.

ABSOLUTE RULES (NEVER BREAK THESE):
1. NEVER include URLs, links, or images. You may mention source names (e.g., "nytimes", "reddit", "wikipedia") but NEVER include the actual URL or link.
2. NEVER use markdown syntax. No **, no *, no `, no #, no ##, no [text](url), no ![image](url). No markdown at all.
3. Always summarize information in your own words. Do not copy raw output from search results.
4. NEVER ask for clarification or confirmation. Proceed immediately with the requested action and provide results.

FORMAT RULES:
- Use ONLY HTML tags for formatting: <b>bold</b>, <i>italic</i>, <code>code</code>
- For headers, use <b>Header Text</b> on its own line
- For lists, use plain dashes: - item
- Always close tags properly: <b>text</b> not <b>text
- Use plain newlines for line breaks (no HTML tags for breaks)

CORRECT list formatting:
1. <b>Vegetables</b>:
   - Daikon radish for sweetness.
   - Bok choy for crunch.

WRONG (never do this):
1. **Vegetables**:
   - Daikon radish ([source](https://example.com))

CORRECT source attribution:
- According to nytimes, the recipe calls for...
- As reported by reddit users...

WRONG source attribution:
- According to [nytimes](https://nytimes.com/article), the recipe...
- Source: https://example.com

Be concise but thorough. Provide complete, helpful answers."""


def get_or_create_conversation(user_id: int) -> str:
    """Get existing conversation ID or create a new one for the user."""
    conversation_id = user_conversations.get(user_id)
    
    if conversation_id is None:
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
    
    return conversation_id


async def send_to_openai(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                         message: str, use_web_search: bool = False):
    """Send message to OpenAI and reply with the response."""
    user_id = update.effective_user.id
    
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
        
        # Clean URLs and markdown from response
        response_text = clean_response(response_text)
        
        # Split message if too long (Telegram limit is 4096 characters)
        chunks = split_message(response_text)
        
        # Send each chunk
        for chunk in chunks:
            # Try HTML first, fall back to plain text if it fails
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.warning(f"HTML parsing failed, falling back to plain text: {e}")
                # Strip all HTML tags for plain text fallback
                plain_text = re.sub(r'<[^>]+>', '', chunk)
                await update.message.reply_text(plain_text)
    except Exception as e:
        logger.error(f"Error calling OpenAI: {e}")
        await update.message.reply_text("Sorry, I encountered an error. Please try again.")


@require_auth
async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages by sending them to ChatGPT."""
    await send_to_openai(update, context, update.message.text)


@require_auth
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "Hello! I'm your AI assistant. Send me a message and I'll respond.\n\n"
        "<b>Commands:</b>\n"
        "/newchat - Start a new conversation\n"
        "/search [query] - Search the web",
        parse_mode=ParseMode.HTML
    )


@require_auth
async def newchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newchat command - clears conversation history."""
    user_id = update.effective_user.id
    if user_id in user_conversations:
        del user_conversations[user_id]
        await update.message.reply_text("Conversation cleared! Starting fresh.")
    else:
        await update.message.reply_text("No conversation to clear. Send me a message to start!")


@require_auth
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command - performs web search."""
    query = " ".join(context.args) if context.args else None
    
    if not query:
        await update.message.reply_text("Usage: /search [your query]\nExample: /search weather in NYC")
        return
    
    search_prompt = f"{query}\n\nIMPORTANT: Use HTML formatting (<b>, <i>, <code>) for structure. You may mention source names (e.g., 'nytimes', 'reddit') but NEVER include URLs, links, or markdown syntax. Rewrite all information in your own words using HTML tags for formatting."
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
    application = Application.builder().token(token).build()

    # Set bot commands (shows up when user types "/")
    async def post_init(app: Application) -> None:
        await app.bot.set_my_commands([
            BotCommand("start", "Show welcome message and commands"),
            BotCommand("newchat", "Start a new conversation"),
            BotCommand("search", "Search the web for information")
        ])
    
    application.post_init = post_init

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("newchat", newchat_command))
    application.add_handler(CommandHandler("search", search_command))
    
    # Message handler (for non-command messages)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, chat_message))

    return application
