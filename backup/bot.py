"""
Telegram ChatGPT Bot
Handles Telegram messages and forwards them to OpenAI API
"""
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory conversation storage (per user)
# In production, consider using DynamoDB or another persistent store
conversations: Dict[int, List[Dict]] = {}

# System prompt for concise, mobile-friendly responses
SYSTEM_PROMPT = """You are a helpful AI assistant. Please follow these guidelines:
1. Be concise and to the point - responses will be read on mobile devices
2. Do NOT include images, markdown images, or image references in your responses
3. Use plain text formatting only
4. Keep responses brief but informative
5. If asked to search the web, use the provided search function"""


def get_conversation_history(user_id: int) -> List[Dict]:
    """Get conversation history for a user"""
    return conversations.get(user_id, [])


def add_to_conversation(user_id: int, role: str, content: str):
    """Add a message to conversation history"""
    if user_id not in conversations:
        conversations[user_id] = []
    conversations[user_id].append({"role": role, "content": content})


def clear_conversation(user_id: int):
    """Clear conversation history for a user"""
    conversations[user_id] = []


async def web_search(query: str) -> str:
    """
    Perform web search using Tavily API (or fallback to OpenAI's web search if available)
    Returns a formatted string with search results
    """
    try:
        # Try Tavily if API key is available
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=tavily_key)
            response = tavily.search(query=query, max_results=3)
            
            results = []
            for result in response.get("results", []):
                title = result.get("title", "No title")
                url = result.get("url", "")
                content = result.get("content", "")[:200]  # Limit content length
                results.append(f"Title: {title}\nURL: {url}\nContent: {content}...")
            
            return "\n\n".join(results) if results else "No search results found."
    except Exception as e:
        logger.error(f"Web search error: {e}")
    
    return f"Web search for '{query}' - (Search functionality may require API key setup)"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    if not user_message:
        await update.message.reply_text("Please send a text message.")
        return
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Get conversation history
        history = get_conversation_history(user_id)
        
        # Build messages for OpenAI
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add conversation history
        messages.extend(history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        add_to_conversation(user_id, "user", user_message)
        
        # Check if user wants web search (simple keyword detection)
        # You can enhance this with more sophisticated detection
        needs_search = any(keyword in user_message.lower() for keyword in [
            "search", "look up", "find", "latest", "current", "recent", "news"
        ])
        
        # Prepare tools for web search if needed
        tools = None
        tool_choice = None
        
        if needs_search:
            tools = [{
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }]
            tool_choice = {"type": "function", "function": {"name": "web_search"}}
        
        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),  # Default to gpt-4o-mini for cost efficiency
            messages=messages,
            tools=tools,
            tool_choice=tool_choice if needs_search else "auto",
            temperature=0.7,
            max_tokens=500  # Limit tokens for concise responses
        )
        
        message = response.choices[0].message
        
        # Handle tool calls (web search)
        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "web_search":
                    import json
                    args = json.loads(tool_call.function.arguments)
                    search_query = args.get("query", user_message)
                    search_results = await web_search(search_query)
                    
                    # Add search results to conversation and get final response
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": search_results
                    })
                    
                    # Get final response with search results
                    response = openai_client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500
                    )
                    message = response.choices[0].message
        
        assistant_response = message.content
        
        if not assistant_response:
            assistant_response = "I apologize, but I couldn't generate a response. Please try again."
        
        # Add assistant response to history
        add_to_conversation(user_id, "assistant", assistant_response)
        
        # Send response (Telegram has 4096 char limit, so we'll truncate if needed)
        if len(assistant_response) > 4096:
            # Split into chunks
            chunks = [assistant_response[i:i+4096] for i in range(0, len(assistant_response), 4096)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(assistant_response)
            
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error processing your message. Please try again."
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = """🤖 Hello! I'm your ChatGPT assistant for flights.

I can help you with:
• Answering questions
• Web searches (just ask naturally)
• General conversations

Commands:
/newchat - Start a fresh conversation

I'll keep responses concise for mobile reading!"""
    
    await update.message.reply_text(welcome_message)


async def newchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newchat command - clears conversation history"""
    user_id = update.effective_user.id
    clear_conversation(user_id)
    await update.message.reply_text("✨ Started a new conversation! Previous chat history cleared.")


def create_application() -> Application:
    """Create and configure the Telegram bot application"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
    
    application = Application.builder().token(token).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("newchat", newchat_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application


# For webhook deployment
async def webhook_handler(request):
    """Handle webhook requests from Telegram"""
    application = create_application()
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"statusCode": 200, "body": "OK"}


# For polling (local development)
if __name__ == "__main__":
    app = create_application()
    logger.info("Starting bot in polling mode...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

