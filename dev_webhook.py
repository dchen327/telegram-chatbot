"""
Automated local webhook development script.
Handles ngrok, webhook setup, and server startup automatically.
"""
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env file!")
    sys.exit(1)

NGROK_PORT = 8000


def get_ngrok_url():
    """Get the ngrok public URL from the local API."""
    try:
        with httpx.Client(timeout=2) as client:
            response = client.get("http://127.0.0.1:4040/api/tunnels")
            data = response.json()
            if data.get("tunnels"):
                return data["tunnels"][0]["public_url"]
    except Exception:
        pass
    return None


def set_webhook(url):
    """Set Telegram webhook to the given URL."""
    webhook_url = f"{url}/webhook"
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    
    try:
        with httpx.Client(timeout=5) as client:
            response = client.post(api_url)
            result = response.json()
            if result.get("ok"):
                print(f"✅ Webhook set to: {webhook_url}")
                return True
            else:
                print(f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}")
                return False
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False


def main():
    print("🚀 Starting local webhook development environment...")
    print("")
    
    # Check if ngrok is running
    print("1️⃣ Checking ngrok...")
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print("   ⚠️  ngrok not detected. Please start ngrok in another terminal:")
        print(f"      ngrok http {NGROK_PORT}")
        print("")
        print("   Then run this script again.")
        sys.exit(1)
    
    print(f"   ✅ Found ngrok: {ngrok_url}")
    print("")
    
    # Set webhook
    print("2️⃣ Setting Telegram webhook...")
    if not set_webhook(ngrok_url):
        sys.exit(1)
    print("")
    
    # Start server
    print("3️⃣ Starting webhook server...")
    print(f"   Server will run on http://localhost:{NGROK_PORT}")
    print("   Press Ctrl+C to stop")
    print("")
    
    # Import and run uvicorn
    import uvicorn
    
    try:
        uvicorn.run(
            "lambda_handler:app",
            host="0.0.0.0",
            port=NGROK_PORT,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        # Optionally remove webhook
        print("\n💡 To remove webhook, run:")
        print(f"   curl -X POST \"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook\"")


if __name__ == "__main__":
    main()

