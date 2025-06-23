#!/usr/bin/env python3
"""Test script to verify configuration is working correctly."""

try:
    from config import config
    print("✅ Config import successful!")
    
    print(f"📧 Gemini API Key: {'SET' if config.GEMINI_API_KEY else 'NOT SET'}")
    print(f"🤖 Default Model: {config.GEMINI_DEFAULT_MODEL}")
    print(f"🌡️  Flask Environment: {config.FLASK_ENV}")
    print(f"🐞 Debug Mode: {config.FLASK_DEBUG}")
    print(f"🚪 Port: {config.PORT}")
    
    if config.GEMINI_API_KEY and config.GEMINI_API_KEY != 'your_actual_gemini_api_key_here':
        print("✅ Configuration looks good!")
    else:
        print("❌ Please set your GEMINI_API_KEY in the .env file")
        
except Exception as e:
    print(f"❌ Configuration error: {e}")
    print("\n💡 Make sure you have:")
    print("   1. Created a .env file in the project root")
    print("   2. Added your GEMINI_API_KEY to the .env file")
    print("   3. Installed python-dotenv: pip install python-dotenv") 