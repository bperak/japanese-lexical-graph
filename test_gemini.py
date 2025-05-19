#!/usr/bin/env python
"""
Test script for Gemini API integration.
This script validates the Gemini API configuration and tests different functionalities.
"""

import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv
import gemini_helper


model_name = "gemini-2.0-flash" 
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api_key():
    """Test if the Gemini API key is valid and configuration works."""
    print("\n=== Testing API Key Configuration ===")
    if gemini_helper.HAS_VALID_API_KEY:
        print("✅ API key is configured")
    else:
        print("❌ API key is not configured or invalid")
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("   No API key found in environment variables")
        elif api_key == 'your_gemini_api_key_here':
            print("   API key is set to default placeholder value")
        else:
            masked_key = api_key[:4] + "..." + api_key[-4:]
            print(f"   API key found but might be invalid: {masked_key}")

def test_model_config():
    """Test if the model configuration is valid."""
    print("\n=== Testing Model Configuration ===")
    model_name = gemini_helper.DEFAULT_MODEL
    print(f"Current model name: {model_name}")
    
    try:
        # Try to initialize the model
        model = genai.GenerativeModel(model_name)
        print(f"✅ Successfully initialized model: {model_name}")
    except Exception as e:
        print(f"❌ Failed to initialize model: {model_name}")
        print(f"   Error: {str(e)}")
        
        # Try alternative models
        alternatives = ['gemini-2.0-flash-lite', 'gemini-2.0-flash']
        for alt_model in alternatives:
            try:
                model = genai.GenerativeModel(alt_model)
                print(f"✅ Alternative model works: {alt_model}")
            except Exception as alt_e:
                print(f"❌ Alternative model failed: {alt_model}")
                print(f"   Error: {str(alt_e)}")

def test_generate_explanation():
    """Test generating explanations for different terms."""
    print("\n=== Testing Generate Explanation ===")
    
    test_terms = ["母親", "吊り橋", "鉄橋", "本"]
    
    for term in test_terms:
        print(f"\nTesting term: {term}")
        try:
            result = gemini_helper.generate_explanation(term)
            if "error" in result:
                print(f"❌ Error for term '{term}': {result['error']}")
            else:
                print(f"✅ Successfully generated explanation for '{term}'")
                print(f"   Overview: {result['overview'][:100]}...")
        except Exception as e:
            print(f"❌ Exception for term '{term}': {str(e)}")

def test_analyze_relationship():
    """Test analyzing relationships between terms."""
    print("\n=== Testing Analyze Relationship ===")
    
    test_pairs = [
        ("母親", "父親"),
        ("吊り橋", "鉄橋"),
        ("本", "書籍")
    ]
    
    for term1, term2 in test_pairs:
        print(f"\nTesting relationship: '{term1}' and '{term2}'")
        try:
            result = gemini_helper.analyze_relationship(term1, term2)
            if "error" in result:
                print(f"❌ Error for relationship '{term1}'-'{term2}': {result['error']}")
            else:
                print(f"✅ Successfully analyzed relationship between '{term1}' and '{term2}'")
                print(f"   Relationship: {result['relationship'][:100]}...")
                print(f"   Similarity score: {result['similarity_score']}")
        except Exception as e:
            print(f"❌ Exception for relationship '{term1}'-'{term2}': {str(e)}")

def test_direct_gemini_query():
    """Test a direct query to the Gemini API."""
    print("\n=== Testing Direct Gemini Query ===")
    
    if not gemini_helper.HAS_VALID_API_KEY:
        print("❌ Skipping test: API key not configured")
        return
    
    try:
        # Try a simple query first
        print("Testing simple query...")
        model = genai.GenerativeModel("gemini-2.0-flash")  # Use known working model
        response = model.generate_content("Hello, what's your name?")
        print(f"✅ Simple query successful: {response.text[:100]}...")
        
        # Try a JSON query
        print("\nTesting JSON query...")
        prompt = """
        Return a JSON object with information about Tokyo.
        
        Format:
        {
            "city": "name",
            "country": "country",
            "population": number,
            "landmarks": ["landmark1", "landmark2"]
        }
        
        Only return the JSON object.
        """
        
        response = model.generate_content(prompt)
        print(f"Response for JSON query: {response.text[:200]}...")
        
        # Try to parse the JSON
        try:
            import re
            json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response.text)
            if json_block_match:
                json_text = json_block_match.group(1).strip()
                json_data = json.loads(json_text)
                print(f"✅ Successfully parsed JSON response")
            else:
                # Try to find JSON object between braces
                json_object_match = re.search(r'({[\s\S]*?})', response.text)
                if json_object_match:
                    json_text = json_object_match.group(1).strip()
                    json_data = json.loads(json_text)
                    print(f"✅ Successfully parsed JSON response from unformatted text")
                else:
                    # Last attempt: treat the whole response as JSON
                    json_data = json.loads(response.text)
                    print(f"✅ Successfully parsed JSON from raw response")
            
            print(f"   Parsed data: {json_data}")
        except Exception as json_error:
            print(f"❌ Failed to parse JSON response: {str(json_error)}")
    
    except Exception as e:
        print(f"❌ Direct query failed: {str(e)}")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    print("=== GEMINI API TEST ===")
    test_api_key()
    test_model_config()
    test_generate_explanation()
    test_analyze_relationship()
    test_direct_gemini_query()
    print("\n=== TEST COMPLETE ===") 