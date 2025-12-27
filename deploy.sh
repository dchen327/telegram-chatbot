#!/bin/bash
# Deploy to AWS Lambda

if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi

# Load environment variables from .env
set -a
source .env
set +a

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN not found in .env file"
    exit 1
fi

# Deploy
echo "Deploying to AWS Lambda..."
DEPLOY_OUTPUT=$(serverless deploy 2>&1)
echo "$DEPLOY_OUTPUT"

# Extract webhook URL from deployment output
WEBHOOK_URL=$(echo "$DEPLOY_OUTPUT" | grep -oE 'https://[a-zA-Z0-9-]+\.execute-api\.[a-zA-Z0-9-]+\.amazonaws\.com/[^/]+' | head -1)

if [ -z "$WEBHOOK_URL" ]; then
    # Try alternative: get from serverless info
    WEBHOOK_URL=$(serverless info 2>/dev/null | grep -oE 'https://[a-zA-Z0-9-]+\.execute-api\.[a-zA-Z0-9-]+\.amazonaws\.com/[^/]+' | head -1)
fi

if [ -z "$WEBHOOK_URL" ]; then
    echo ""
    echo "⚠️  Could not automatically detect webhook URL"
    echo "Please set it manually:"
    echo "curl -X POST \"https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=<YOUR_LAMBDA_URL>/webhook\""
    exit 0
fi

WEBHOOK_URL="${WEBHOOK_URL}/webhook"

# Set webhook
echo ""
echo "Setting Telegram webhook..."
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=$WEBHOOK_URL")

if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo "✅ Webhook set to: $WEBHOOK_URL"
else
    echo "❌ Failed to set webhook"
    echo "Response: $RESPONSE"
    exit 1
fi

