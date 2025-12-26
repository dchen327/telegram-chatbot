# Architecture & Design Decisions

## Overview

This Telegram bot connects users to ChatGPT API, optimized for use during flights where messaging apps are available.

## Tech Stack Rationale

### Python + FastAPI
- **FastAPI**: Modern, fast web framework perfect for async operations
- **Python**: Great ecosystem for AI/ML integrations
- **Mangum**: Adapter to run FastAPI on AWS Lambda

### python-telegram-bot
- Official Python library for Telegram Bot API
- Well-maintained and feature-rich
- Supports both polling and webhook modes

### OpenAI API
- **Default Model: `gpt-4o-mini`**
  - Best balance of cost and quality
  - Fast responses
  - Good for general conversations
- **Alternatives**:
  - `gpt-4o`: Better quality, higher cost
  - `gpt-3.5-turbo`: Lower cost, slightly lower quality

### AWS Lambda Deployment
- **Why Lambda over Vercel?**
  - Better Python runtime support
  - More predictable cold start behavior
  - Easier integration with AWS services (DynamoDB, S3, etc.)
  - Free tier: 1M requests/month
- **Webhook vs Polling**:
  - Webhook: More efficient, required for production
  - Polling: Simpler for local development

## Architecture Flow

```
User → Telegram → Webhook → API Gateway → Lambda → Bot Handler
                                                      ↓
                                              OpenAI API
                                                      ↓
                                              Response → Telegram → User
```

## State Management

### Current: In-Memory Storage
- **Pros**: Simple, fast, no external dependencies
- **Cons**: Lost on cold starts, not shared across instances
- **Use Case**: MVP, single-user testing

### Future: DynamoDB
- **Pros**: Persistent, scalable, shared across instances
- **Cons**: Additional AWS service, slight latency
- **Implementation**: See commented code in `serverless.yml`

## Conversation History

- Stored per user (by Telegram user ID)
- Includes system prompt, user messages, and assistant responses
- Cleared with `/newchat` command
- Max tokens: 500 per response (for conciseness)

## Web Search Integration

### Current Implementation
- Uses **Tavily API** (free tier available)
- Keyword detection: "search", "look up", "find", "latest", etc.
- Function calling: OpenAI decides when to search

### How It Works
1. User message triggers keyword detection
2. OpenAI function calling framework invoked
3. If search needed, Tavily API called
4. Results added to conversation context
5. OpenAI generates final response with search results

### Alternatives
- OpenAI's built-in web search (if available)
- Google Custom Search API
- Bing Search API
- Serper API

## System Prompts

The bot is instructed to:
1. Be concise (mobile reading)
2. No images (won't load on flights)
3. Plain text only
4. Brief but informative

## Error Handling

- Try-catch around all API calls
- Graceful degradation if web search fails
- User-friendly error messages
- Logging for debugging

## Security Considerations

1. **API Keys**: Stored in environment variables, never in code
2. **Webhook Verification**: Telegram validates webhook requests
3. **Rate Limiting**: Consider adding if needed (not implemented yet)
4. **Input Validation**: Telegram handles most validation

## Cost Optimization

1. **Model Choice**: `gpt-4o-mini` is cost-effective
2. **Token Limits**: 500 max tokens per response
3. **Lambda**: Free tier covers most usage
4. **Tavily**: Free tier available

## Scalability Considerations

### Current Limitations
- In-memory storage doesn't scale across instances
- No rate limiting
- Single conversation per user

### Future Enhancements
- DynamoDB for persistent storage
- Redis for caching
- Rate limiting middleware
- Multiple conversation threads per user
- Queue system for high traffic

## Deployment Options

### Option 1: Serverless Framework (Recommended)
- Easy deployment
- Infrastructure as code
- Easy rollback

### Option 2: Manual Lambda
- More control
- Requires manual API Gateway setup
- More configuration

### Option 3: Local Development
- Polling mode
- Good for testing
- Not for production

## Monitoring & Debugging

- CloudWatch Logs: Automatic with Lambda
- Logging levels: INFO for normal, ERROR for issues
- Health check endpoint: `/health`

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `OPENAI_MODEL` | No | Model name (default: gpt-4o-mini) |
| `TAVILY_API_KEY` | No | For web search (optional) |
| `AWS_REGION` | No | AWS region (default: us-east-1) |
| `DYNAMODB_TABLE_NAME` | No | For future DynamoDB integration |

## Testing Strategy

1. **Local Testing**: Use polling mode
2. **Webhook Testing**: Use ngrok or similar
3. **Production**: Deploy to Lambda and test with real webhook

## Known Limitations

1. Conversation history lost on Lambda cold starts (with in-memory storage)
2. Web search requires Tavily API key
3. No support for images/voice (by design for flights)
4. Single conversation per user (no threads)

