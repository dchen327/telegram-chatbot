"""
Local webhook server for development.
Run this instead of bot.py when testing webhook mode locally.
Use ngrok or similar to expose it: ngrok http 8000
Then set webhook: curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<ngrok-url>/webhook"
"""
import uvicorn
from lambda_handler import app

if __name__ == "__main__":
    print("🚀 Starting local webhook server on http://localhost:8000")
    print("📝 Use ngrok to expose: ngrok http 8000")
    print("🔗 Then set webhook to your ngrok URL")
    uvicorn.run(app, host="0.0.0.0", port=8000)

