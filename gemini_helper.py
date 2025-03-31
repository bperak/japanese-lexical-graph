"""
Helper module for integrating with Google's Gemini API.
Provides functions for generating explanations, analyzing relationships,
and enhancing node information with AI-generated content.
"""

import os
import json
import logging
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from cache_helper import cache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'your_gemini_api_key_here':
        logger.warning("No valid Gemini API key found in environment variables.")
        HAS_VALID_API_KEY = False
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        HAS_VALID_API_KEY = True
except Exception as e:
    logger.error(f"Error configuring Gemini API: {e}")
    HAS_VALID_API_KEY = False

# Default model to use
DEFAULT_MODEL = 'gemini-2.0-flash'

def is_available():
    """Check if Gemini API is available with valid API key."""
    return HAS_VALID_API_KEY

def generate_explanation(term, context=None, model_name=DEFAULT_MODEL):
    """
    Generate an explanation for a Japanese term using Gemini.
    
    Args:
        term (str): The Japanese term to explain
        context (dict, optional): Additional context to help with explanation
        model_name (str): Gemini model to use
        
    Returns:
        dict: The explanation results
    """
    if not HAS_VALID_API_KEY:
        return {"error": "No valid Gemini API key configured"}

    # Check cache first
    cache_key = f"gemini_explanation_{term}_{model_name}"
    cached_result = cache.get(cache_key)
    if cached_result:
        try:
            return json.loads(cached_result)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache for term '{term}'. Regenerating content.")
            # Cache was corrupted, continue with generation
    
    try:
        # Format prompt with context if provided
        if context:
            prompt = f"""
            Explain the Japanese term "{term}" in detail. 
            
            Additional context:
            - Parts of speech: {context.get('pos', 'Unknown')}
            - English meanings: {context.get('english', ['Unknown'])}
            - Related terms: {context.get('related', [])}
            
            IMPORTANT: Your response MUST be a valid JSON object with the EXACT following structure:
            {{
                "overview": "Brief overview of what the term means",
                "cultural_context": "Cultural context if relevant",
                "usage_examples": ["example 1", "example 2", "example 3"],
                "nuances": "Any nuances in meaning or usage"
            }}
            
            DO NOT include any text before or after the JSON.
            DO NOT use markdown formatting or code blocks around the JSON.
            ONLY return the raw JSON object itself.
            """
        else:
            prompt = f"""
            Explain the Japanese term "{term}" in detail.
            
            IMPORTANT: Your response MUST be a valid JSON object with the EXACT following structure:
            {{
                "overview": "Brief overview of what the term means",
                "cultural_context": "Cultural context if relevant",
                "usage_examples": ["example 1", "example 2", "example 3"],
                "nuances": "Any nuances in meaning or usage"
            }}
            
            DO NOT include any text before or after the JSON.
            DO NOT use markdown formatting or code blocks around the JSON.
            ONLY return the raw JSON object itself.
            """
        
        # Add logging for debugging
        logger.info(f"Sending request to Gemini API for term: {term} using model: {model_name}")
        
        # Try working models only - specifically avoid 'gemini-pro'
        models_to_try = ['gemini-2.0-flash', 'gemini-2.0-flash-lite']
        if model_name not in models_to_try:
            # Add the provided model to the beginning of the list if it's not already there
            models_to_try.insert(0, model_name)
            
        response = None
        model_used = None
        
        for try_model in models_to_try:
            try:
                model = genai.GenerativeModel(try_model)
                logger.info(f"Attempting with model: {try_model}")
                response = model.generate_content(prompt)
                model_used = try_model
                logger.info(f"Successfully generated content with model: {try_model}")
                break
            except Exception as model_error:
                logger.warning(f"Error with model {try_model}: {model_error}")
                # Continue to next model in the list
        
        # If all models failed
        if response is None:
            logger.error("All model attempts failed")
            return {
                "overview": f"Error calling Gemini API for '{term}': All model attempts failed",
                "cultural_context": "N/A",
                "usage_examples": [],
                "nuances": "N/A",
                "error": "Failed to generate content with any model"
            }
        
        # Log the raw response for debugging
        logger.info(f"Raw Gemini API response for term '{term}': {response.text!r}")
        
        # Create an explanation with the raw response always included
        explanation = {
            "overview": f"Information about {term}.",
            "cultural_context": "Information not available.",
            "usage_examples": [f"Example usage of {term}"],
            "nuances": "Information not available.",
            "raw_response": response.text,  # Always include the raw response
            "_model_used": model_used  # Include which model was used
        }
            
        # Parse response as JSON - handle empty responses gracefully
        if not response.text or response.text.strip() == "":
            logger.warning(f"Empty response from Gemini API for term '{term}'")
            explanation["generation_note"] = "Failed to generate content - received empty response"
        else:
            try:
                # Clean the response text - try to extract JSON from various formats
                json_text = response.text.strip()
                logger.info(f"Initial cleaned JSON text for '{term}': {json_text!r}")
                
                # Check if response is wrapped in ```json code blocks and extract just the JSON part
                import re
                json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
                if json_block_match:
                    # Extract just the JSON content from within the code block
                    json_text = json_block_match.group(1).strip()
                    logger.info(f"Extracted JSON from code block for '{term}': {json_text!r}")
                
                # Try to find JSON object between braces if not a complete JSON yet
                if not (json_text.startswith('{') and json_text.endswith('}')):
                    json_object_match = re.search(r'({[\s\S]*?})', json_text)
                    if json_object_match:
                        json_text = json_object_match.group(1).strip()
                        logger.info(f"Extracted JSON object for '{term}': {json_text!r}")
                
                # Now parse the cleaned JSON
                logger.info(f"Final JSON text before parsing for '{term}': {json_text!r}")
                parsed_json = json.loads(json_text)
                logger.info(f"Successfully parsed JSON for '{term}'")
                
                # Update the explanation with parsed values
                explanation.update(parsed_json)
                
                # Ensure all required fields exist
                required_fields = ["overview", "cultural_context", "usage_examples", "nuances"]
                for field in required_fields:
                    if field not in explanation:
                        logger.warning(f"Missing field '{field}' in response for '{term}', adding default value")
                        if field == "usage_examples":
                            explanation[field] = []
                        else:
                            explanation[field] = f"No information about {field} available"
                
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Invalid response from Gemini API for term '{term}': {e}")
                # The fallback values are already in explanation
                explanation["generation_note"] = f"Parse error: {str(e)}"
        
        # Cache the result for 3 days
        try:
            cache.set(cache_key, json.dumps(explanation), 3 * 24 * 60 * 60)
        except Exception as e:
            logger.warning(f"Failed to cache explanation for '{term}': {e}")
        
        return explanation
    
    except Exception as e:
        logger.error(f"Error generating explanation for {term}: {e}")
        return {
            "overview": f"An error occurred while generating information about '{term}'.",
            "cultural_context": "N/A",
            "usage_examples": [],
            "nuances": "N/A",
            "error": str(e)
        }

def analyze_relationship(term1, term2, model_name=DEFAULT_MODEL):
    """
    Analyze the semantic relationship between two Japanese terms.
    
    Args:
        term1 (str): First Japanese term
        term2 (str): Second Japanese term
        model_name (str): Gemini model to use
        
    Returns:
        dict: Analysis of the relationship
    """
    if not HAS_VALID_API_KEY:
        return {"error": "No valid Gemini API key configured"}
    
    # Check cache first
    cache_key = f"gemini_relationship_{term1}_{term2}_{model_name}"
    cached_result = cache.get(cache_key)
    if cached_result:
        try:
            return json.loads(cached_result)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache for relationship '{term1}'-'{term2}'. Regenerating content.")
            # Cache was corrupted, continue with generation
    
    try:
        prompt = f"""
        Analyze the semantic relationship between the Japanese terms "{term1}" and "{term2}".
        
        IMPORTANT: Your response MUST be a valid JSON object with the EXACT following structure:
        {{
            "relationship": "Description of semantic relationship",
            "differences": "Key differences in meaning",
            "usage_contexts": "Contexts where one would be preferred",
            "similarity_score": 85  // numeric score between 0-100
        }}
        
        DO NOT include any text before or after the JSON.
        DO NOT use markdown formatting or code blocks around the JSON.
        ONLY return the raw JSON object itself.
        
        Consider:
        1. How these terms are semantically related
        2. Key differences in meaning
        3. Contexts where one would be preferred over the other
        4. A similarity score from 0-100 where 100 is identical meaning
        """
        
        # Add logging for debugging
        logger.info(f"Sending request to Gemini API for relationship between '{term1}' and '{term2}' using model: {model_name}")
        
        # Try working models only - specifically avoid 'gemini-pro'
        models_to_try = ['gemini-2.0-flash', 'gemini-2.0-flash-lite'] 
        if model_name not in models_to_try:
            # Add the provided model to the beginning of the list if it's not already there
            models_to_try.insert(0, model_name)
            
        response = None
        model_used = None
        
        for try_model in models_to_try:
            try:
                model = genai.GenerativeModel(try_model)
                logger.info(f"Attempting with model: {try_model}")
                response = model.generate_content(prompt)
                model_used = try_model
                logger.info(f"Successfully generated content with model: {try_model}")
                break
            except Exception as model_error:
                logger.warning(f"Error with model {try_model}: {model_error}")
                # Continue to next model in the list
                
        # If all models failed
        if response is None:
            logger.error("All model attempts failed")
            return {
                "relationship": f"Error calling Gemini API: All model attempts failed",
                "differences": "Error occurred",
                "usage_contexts": "Error occurred",
                "similarity_score": 0,
                "error": "Failed to generate content with any model"
            }
        
        # Log the raw response for debugging
        logger.info(f"Raw Gemini API response for relationship '{term1}'-'{term2}': {response.text!r}")
        
        # Create an analysis with the raw response always included
        analysis = {
            "relationship": f"Information about the relationship between '{term1}' and '{term2}' is currently unavailable.",
            "differences": "No information available",
            "usage_contexts": "No information available",
            "similarity_score": 0,
            "raw_response": response.text,  # Always include the raw response
            "_model_used": model_used      # Include which model was used
        }
            
        # Parse response as JSON - handle empty responses gracefully
        if not response.text or response.text.strip() == "":
            logger.warning(f"Empty response from Gemini API for relationship between '{term1}' and '{term2}'")
            analysis["generation_note"] = "Failed to generate content - received empty response"
        else:
            try:
                # Clean the response text - try to extract JSON from various formats
                json_text = response.text.strip()
                
                # Check if response is wrapped in ```json code blocks and extract just the JSON part
                import re
                json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
                if json_block_match:
                    # Extract just the JSON content from within the code block
                    json_text = json_block_match.group(1).strip()
                
                # Try to find JSON object between braces if not a complete JSON yet
                if not (json_text.startswith('{') and json_text.endswith('}')):
                    json_object_match = re.search(r'({[\s\S]*?})', json_text)
                    if json_object_match:
                        json_text = json_object_match.group(1).strip()
                
                # Now parse the cleaned JSON
                parsed_json = json.loads(json_text)
                
                # Update the analysis with parsed values
                analysis.update(parsed_json)
                
                # Ensure all required fields exist
                required_fields = ["relationship", "differences", "usage_contexts", "similarity_score"]
                for field in required_fields:
                    if field not in analysis:
                        if field == "similarity_score":
                            analysis[field] = 0
                        else:
                            analysis[field] = f"No information about {field} available"
                
                # Ensure similarity_score is a number
                if not isinstance(analysis["similarity_score"], (int, float)):
                    try:
                        analysis["similarity_score"] = float(analysis["similarity_score"])
                    except (ValueError, TypeError):
                        analysis["similarity_score"] = 0
                
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Invalid response from Gemini API for relationship: {e}")
                # The fallback values are already in analysis
                analysis["generation_note"] = f"Parse error: {str(e)}"
        
        # Cache the result for 3 days
        try:
            cache.set(cache_key, json.dumps(analysis), 3 * 24 * 60 * 60)
        except Exception as e:
            logger.warning(f"Failed to cache relationship analysis for '{term1}'-'{term2}': {e}")
        
        return analysis
    
    except Exception as e:
        logger.error(f"Error analyzing relationship between {term1} and {term2}: {e}")
        return {
            "relationship": f"An error occurred while analyzing the relationship between '{term1}' and '{term2}'.",
            "differences": "Error occurred",
            "usage_contexts": "Error occurred",
            "similarity_score": 0,
            "error": str(e)
        }

def get_neighbor_info(node_id):
    """
    Get information about the neighbors of a node.
    
    Args:
        node_id (str): ID of the node to get neighbors for
        
    Returns:
        list: List of neighbor information
    """
    from app import get_graph  # Import here to avoid circular imports
    
    graph = get_graph()
    if not graph:
        logger.error("Graph not available")
        return []
    
    try:
        neighbors = []
        # Get all neighbors
        for neighbor_id in graph.neighbors(node_id):
            edge_data = graph.get_edge_data(node_id, neighbor_id)
            if edge_data:
                # Get the first edge if there are multiple (using 0 as default key)
                edge_key = list(edge_data.keys())[0] if edge_data else 0
                edge_weight = edge_data[edge_key].get('weight', 1) if edge_key in edge_data else 1
                
                neighbors.append({
                    'id': neighbor_id,
                    'edge_weight': edge_weight,
                    'edge_type': edge_data[edge_key].get('type', 'unknown') if edge_key in edge_data else 'unknown'
                })
        
        return neighbors
    except Exception as e:
        logger.error(f"Error getting neighbors for node {node_id}: {e}")
        return []

def enhance_with_gemini(node_id, model_name=DEFAULT_MODEL):
    """
    Enhance a node with information from the Gemini API.

    Args:
        node_id (str): ID of the node to enhance
        model_name (str): Gemini model to use

    Returns:
        dict: Enhanced node information
    """
    try:
        # Attempt to get explanation for the term
        explanation = generate_explanation(node_id, model_name=model_name)
        
        # Get neighbor information
        neighbors = get_neighbor_info(node_id)
        
        # Analyze interesting relationships if we have enough neighbors
        relationships = []
        if neighbors and len(neighbors) > 0:
            # Sort neighbors by edge weight and get top ones
            sorted_neighbors = sorted(neighbors, key=lambda x: x['edge_weight'], reverse=True)
            top_neighbors = sorted_neighbors[:min(3, len(sorted_neighbors))]
            
            for neighbor in top_neighbors:
                relationship = analyze_relationship(node_id, neighbor['id'], model_name=model_name)
                relationships.append({
                    'term1': node_id,
                    'term2': neighbor['id'],
                    'analysis': relationship
                })
        
        return {
            'id': node_id,
            'explanation': explanation,
            'neighbors': neighbors,
            'relationships': relationships
        }
    except Exception as e:
        logger.error(f"Error enhancing node {node_id} with Gemini: {e}")
        # Return a structured error response
        return {
            'id': node_id,
            'explanation': {
                'overview': f"An error occurred while retrieving information for '{node_id}'.",
                'cultural_context': "No information available due to an error.",
                'usage_examples': [],
                'nuances': "No information available.",
                'error': str(e)
            },
            'neighbors': [],
            'relationships': []
        } 