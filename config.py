"""
Application configuration module.

Loads environment variables and provides access to configuration settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_DEFAULT_MODEL = os.getenv('GEMINI_DEFAULT_MODEL', 'gemini-1.5-flash') # Default to flash if not set

# You can list available models here if needed, for validation or selection UI
AVAILABLE_GEMINI_MODELS = [
    "gemini-1.5-pro-latest",
    "gemini-1.5-flash-latest",
    "gemini-pro", # General purpose
    # Older models, might be deprecated or have different pricing/capabilities
    "gemini-1.0-pro", 
    # Specific models if you plan to use them, e.g. for vision
    # "gemini-pro-vision" 
]

# Validate that the default model is in the available list (optional, but good practice)
if GEMINI_DEFAULT_MODEL not in AVAILABLE_GEMINI_MODELS:
    # This is a simple warning. You might want to raise an error or fall back to a known good model.
    print(f"Warning: GEMINI_DEFAULT_MODEL '{GEMINI_DEFAULT_MODEL}' is not in the list of explicitly available models. Ensure it's a valid model name.")

# Wikidata Configuration
WIKIDATA_USER_AGENT = os.getenv('WIKIDATA_USER_AGENT', 'PythonWikidataLexicalGraph/1.0 (your-email@example.com)')

# Cache Configuration (Example - assuming basic in-memory or file-based from cache_helper)
# CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple') # e.g., 'simple', 'redis'
# CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))

if __name__ == '__main__':
    # For testing or displaying current config
    print("Current Configuration:")
    print(f"  Gemini API Key Loaded: {bool(GEMINI_API_KEY and GEMINI_API_KEY != 'your_gemini_api_key_here')}")
    print(f"  Gemini Default Model: {GEMINI_DEFAULT_MODEL}")
    print(f"  Available Gemini Models: {AVAILABLE_GEMINI_MODELS}")
    print(f"  Wikidata User Agent: {WIKIDATA_USER_AGENT}") 