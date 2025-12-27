"""
AWS Lambda handler for Telegram bot webhook
"""
import json
import logging
import os
import sys
import traceback
from mangum import Mangum
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# Configure logging for Lambda - use INFO level and format for CloudWatch
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
logger.info("Lambda handler module loaded")

# Create FastAPI app early
try:
    app = FastAPI()
    logger.info("FastAPI app created")
except Exception as e:
    logger.error(f"Failed to create FastAPI app: {e}", exc_info=True)
    raise

# Health endpoint - completely independent, no bot imports needed
@app.get("/health")
def health():
    """Health check endpoint - simple health check that doesn't require bot initialization"""
    logger.info("Health endpoint called")
    try:
        return {"status": "ok", "service": "telegram-chatbot"}
    except Exception as e:
        logger.error(f"Health endpoint error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "traceback": traceback.format_exc()}
        )

# Import bot logic (lazy import to catch errors)
try:
    from telegram import Update
    from bot import create_application
    logger.info("Successfully imported bot module")
except Exception as e:
    logger.error(f"Failed to import bot module: {e}", exc_info=True)
    # Don't raise - let health endpoint work even if bot import fails
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
        
        # Parse JSON body
        try:
            body = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse request body as JSON: {e}")
            # Try to get raw body for debugging
            try:
                raw_body = await request.body()
                logger.error(f"Raw body (first 500 chars): {raw_body[:500]}")
            except:
                pass
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid JSON in request body"}
            )
        
        # Log received data for debugging
        if isinstance(body, dict):
            logger.info(f"Received webhook update_id: {body.get('update_id', 'missing')}, keys: {list(body.keys())}")
        else:
            logger.error(f"Body is not a dict, type: {type(body)}, value: {body}")
            return JSONResponse(
                status_code=400,
                content={"error": "Body must be a JSON object"}
            )
        
        # Validate that body has update_id (required by Update)
        if "update_id" not in body:
            logger.error(f"Missing update_id in body. Body keys: {list(body.keys())}, body: {str(body)[:500]}")
            return JSONResponse(
                status_code=400,
                content={"error": "Missing update_id in webhook payload"}
            )
        
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


# Create Mangum handler for Lambda
# Wrap in try/except to catch initialization errors
_mangum_handler = None
try:
    _mangum_handler = Mangum(app, lifespan="off")
    logger.info("Mangum handler created successfully")
except Exception as e:
    logger.error(f"Failed to create Mangum handler: {e}", exc_info=True)
    logger.error(f"Traceback: {traceback.format_exc()}")

# Create a minimal error handler that handles health endpoint
def _error_handler(event, context):
    """Fallback handler when Mangum initialization fails"""
    logger.error(f"Error handler invoked with event: {json.dumps(event)}")
    try:
        # Check if this is a health check request
        path = event.get("path", "") or event.get("rawPath", "")
        method = event.get("httpMethod", "") or event.get("requestContext", {}).get("http", {}).get("method", "")
        
        if path.endswith("/health") and method.upper() == "GET":
            logger.info("Health endpoint accessed via error handler")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"status": "ok", "service": "telegram-chatbot", "handler": "error_handler"})
            }
        
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Handler initialization failed",
                "message": "Mangum handler could not be created"
            })
        }
    except Exception as handler_error:
        logger.error(f"Error in error_handler: {handler_error}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": f"Critical handler error: {str(handler_error)}"
            })
        }

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

# Main handler function - wraps Mangum handler with logging and error handling
def handler(event, context):
    """Main Lambda handler function"""
    # Force flush logs immediately to ensure they appear in CloudWatch
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    try:
        logger.info(f"Lambda invoked - path: {event.get('path', event.get('rawPath', 'unknown'))}, method: {event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'unknown'))}")
        sys.stdout.flush()
    except Exception as log_err:
        # Even if logging fails, try to continue
        print(f"Failed to log invocation: {log_err}")
        sys.stdout.flush()
    
    # Use error handler if Mangum failed to initialize
    if _mangum_handler is None:
        try:
            logger.warning("Using error handler because Mangum handler is not available")
            sys.stdout.flush()
        except:
            print("Mangum handler not available, using error handler")
            sys.stdout.flush()
        return _error_handler(event, context)
    
    try:
        # Normalize event to ensure required fields exist
        normalized_event = _normalize_event(event)
        
        # Call Mangum handler (it's synchronous and handles async internally)
        result = _mangum_handler(normalized_event, context)
        try:
            logger.info(f"Handler returned status: {result.get('statusCode', 'unknown')}")
            sys.stdout.flush()
        except:
            pass
        return result
    except Exception as e:
        # Ensure error is logged and flushed
        try:
            logger.error(f"Unhandled exception in handler: {e}", exc_info=True)
            logger.error(f"Traceback: {traceback.format_exc()}")
            sys.stdout.flush()
            sys.stderr.flush()
        except:
            print(f"CRITICAL ERROR: {e}")
            traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
        
        # Try to return a proper error response
        try:
            path = event.get("path", "") or event.get("rawPath", "")
            if path.endswith("/health") or "/health" in path:
                # Even if there's an error, try to return health check response
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"status": "ok", "service": "telegram-chatbot", "note": "error_in_handler"})
                }
        except:
            pass
        
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": f"Unhandled exception: {str(e)}",
                "type": type(e).__name__
            })
        }
