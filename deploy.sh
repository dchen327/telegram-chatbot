#!/bin/bash
# Quick deployment script for AWS Lambda

echo "🚀 Deploying Telegram ChatGPT Bot to AWS Lambda..."

# Check if serverless is installed
if ! command -v serverless &> /dev/null; then
    echo "❌ Serverless Framework not found. Installing..."
    npm install -g serverless
    npm install --save-dev serverless-python-requirements
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Make sure to set environment variables in Lambda console."
fi

# Deploy
echo "📦 Deploying..."
serverless deploy

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Get your API Gateway URL from the output above"
echo "2. Set webhook: curl -X POST \"https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_API_GATEWAY_URL>/webhook\""
echo "3. Test your bot on Telegram!"

