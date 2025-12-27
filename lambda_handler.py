"""
AWS Lambda handler for Telegram bot webhook
"""
import json
import logging
import sys
from mangum import Mangum
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "telegram-chatbot"}

try:
    from telegram import Update
    from bot import create_application
except Exception as e:
    logger.error(f"Failed to import bot module: {e}", exc_info=True)
    create_application = None
    Update = None

# Store application instance (reused across invocations)
bot_application = None
_initialized = False


async def get_application():
    """Get or create and initialize bot application (reused for warm starts)"""
    global bot_application, _initialized
    if create_application is None:
        raise RuntimeError("Bot module not available")
    if bot_application is None:
        bot_application = create_application()
    if not _initialized:
        await bot_application.initialize()
        _initialized = True
    return bot_application


# Note: FastAPI startup events don't work reliably in Lambda
# We initialize lazily on first request instead


@app.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook"""
    try:
        if create_application is None or Update is None:
            return JSONResponse(
                status_code=500,
                content={"error": "Bot module not available"}
            )
        
        body = await request.json()
        application = await get_application()
        update = Update.de_json(body, application.bot)
        await application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


_mangum_handler = Mangum(app, lifespan="off")


def _normalize_event(event):
    """Normalize API Gateway event to ensure required fields exist for Mangum"""
    # Make a copy to avoid modifying the original
    normalized = event.copy()
    
    # Ensure requestContext exists and has required fields for API Gateway v2
    if "requestContext" in normalized:
        request_context = normalized["requestContext"]
        if "http" in request_context:
            http_context = request_context["http"]
            # Add missing sourceIp if not present (Mangum requires this)
            if "sourceIp" not in http_context:
                http_context["sourceIp"] = "0.0.0.0"
            # Add missing protocol if not present
            if "protocol" not in http_context:
                http_context["protocol"] = "HTTP/1.1"
    else:
        # Create minimal requestContext for API Gateway v2
        normalized["requestContext"] = {
            "http": {
                "method": normalized.get("httpMethod", "GET"),
                "path": normalized.get("path", normalized.get("rawPath", "/")),
                "sourceIp": "0.0.0.0",
                "protocol": "HTTP/1.1"
            }
        }
    
    return normalized

def handler(event, context):
    """Main Lambda handler function"""
    try:
        normalized_event = _normalize_event(event)
        return _mangum_handler(normalized_event, context)
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
