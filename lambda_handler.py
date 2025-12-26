"""
AWS Lambda handler for Telegram bot webhook
"""
import json
import logging
from mangum import Mangum
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv

# Import bot logic
from bot import (
    handle_message,
    start_command,
    newchat_command,
    create_application
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Store application instance (reused across invocations)
bot_application = None


def get_application():
    """Get or create bot application (reused for warm starts)"""
    global bot_application
    if bot_application is None:
        bot_application = create_application()
    return bot_application


@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook"""
    try:
        body = await request.json()
        update = Update.de_json(body, get_application().bot)
        await get_application().process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return Response(status_code=500, content=json.dumps({"error": str(e)}))


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


# Create Mangum handler for Lambda
handler = Mangum(app, lifespan="off")

