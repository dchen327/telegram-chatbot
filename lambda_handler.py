"""
AWS Lambda handler for Telegram bot webhook
"""
import json
import logging
from mangum import Mangum
from fastapi import FastAPI, Request, Response
from telegram import Update

# Import bot logic
from bot import create_application

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Store application instance (reused across invocations)
bot_application = None
_initialized = False


async def get_application():
    """Get or create and initialize bot application (reused for warm starts)"""
    global bot_application, _initialized
    if bot_application is None:
        bot_application = create_application()
    if not _initialized:
        await bot_application.initialize()
        _initialized = True
    return bot_application


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    await get_application()


@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook"""
    try:
        body = await request.json()
        application = await get_application()
        update = Update.de_json(body, application.bot)
        await application.process_update(update)
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
