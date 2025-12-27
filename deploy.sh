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

# Deploy
serverless deploy

