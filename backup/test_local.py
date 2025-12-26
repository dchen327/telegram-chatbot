"""
Simple test script for local development
Tests the bot in polling mode
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_vars():
    """Check if required environment variables are set"""
    required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY"]
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("Please create a .env file with these variables.")
        return False
    
    print("✅ All required environment variables are set")
    return True

def test_imports():
    """Test if all required packages are installed"""
    try:
        import telegram
        import openai
        import fastapi
        import mangum
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Run: pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    print("🧪 Testing Telegram ChatGPT Bot Setup\n")
    
    print("1. Checking environment variables...")
    env_ok = test_env_vars()
    
    print("\n2. Checking package imports...")
    imports_ok = test_imports()
    
    if env_ok and imports_ok:
        print("\n✅ All checks passed! You can run the bot with:")
        print("   python bot.py")
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")

