"""
Helper module for integrating with Google's Gemini API.
Provides functions for generating explanations, analyzing relationships,
and enhancing node information with AI-generated content.
"""

import os
import json
import logging
import time
import google.generativeai as genai
from PIL import Image
from cache_helper import cache
import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
try:
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'your_gemini_api_key_here':
        logger.warning("No valid Gemini API key found in config.py.")
        HAS_VALID_API_KEY = False
    else:
        genai.configure(api_key=config.GEMINI_API_KEY)
        HAS_VALID_API_KEY = True
except Exception as e:
    logger.error(f"Error configuring Gemini API: {e}")
    HAS_VALID_API_KEY = False

# Default model to use
DEFAULT_MODEL = config.GEMINI_DEFAULT_MODEL

def is_available():
    """Check if Gemini API is available with valid API key."""
    return HAS_VALID_API_KEY

def generate_explanation(term, context=None, model_name=None):
    """
    Generate an explanation for a Japanese term using Gemini.
    
    Args:
        term (str): The Japanese term to explain
        context (dict, optional): Additional context to help with explanation
        model_name (str, optional): Gemini model to use. Defaults to GEMINI_DEFAULT_MODEL from config.
        
    Returns:
        dict: The explanation results
    """
    if not HAS_VALID_API_KEY:
        return {"error": "No valid Gemini API key configured"}

    current_model_name = model_name if model_name else DEFAULT_MODEL

    # Check cache first
    cache_key = f"gemini_explanation_{term}_{current_model_name}"
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
        
        logger.info(f"Sending request to Gemini API for term: {term} using model: {current_model_name}")
        
        model = genai.GenerativeModel(current_model_name)
        response = model.generate_content(prompt)
        model_used = current_model_name
        
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
                
                # Try multiple parsing strategies
                parsed_json = None
                parse_errors = []
                
                # Strategy 1: Direct parsing
                try:
                    parsed_json = json.loads(json_text)
                    logger.info(f"Successfully parsed JSON for '{term}' using direct parsing")
                except json.JSONDecodeError as e:
                    parse_errors.append(f"Direct parsing failed: {e}")
                
                # Strategy 2: If direct parsing failed, try to fix common issues
                if parsed_json is None:
                    try:
                        # Fix common issues like unescaped quotes in strings
                        fixed_json = json_text
                        
                        # Try to parse again
                        parsed_json = json.loads(fixed_json)
                        logger.info(f"Successfully parsed JSON for '{term}' using fixed JSON")
                    except json.JSONDecodeError as e:
                        parse_errors.append(f"Fixed parsing failed: {e}")
                
                # Strategy 3: If all else fails, try to extract individual fields manually
                if parsed_json is None:
                    logger.warning(f"JSON parsing failed for '{term}', attempting manual field extraction")
                    logger.warning(f"Parse errors: {parse_errors}")
                    
                    # Try to extract fields manually using regex
                    import re
                    
                    manual_json = {}
                    
                    # Extract overview
                    overview_match = re.search(r'"overview"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', json_text, re.DOTALL)
                    if overview_match:
                        manual_json["overview"] = overview_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                    
                    # Extract cultural_context
                    context_match = re.search(r'"cultural_context"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', json_text, re.DOTALL)
                    if context_match:
                        manual_json["cultural_context"] = context_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                    
                    # Extract nuances
                    nuances_match = re.search(r'"nuances"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', json_text, re.DOTALL)
                    if nuances_match:
                        manual_json["nuances"] = nuances_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                    
                    # Extract usage_examples array
                    examples_match = re.search(r'"usage_examples"\s*:\s*\[(.*?)\]', json_text, re.DOTALL)
                    if examples_match:
                        examples_text = examples_match.group(1)
                        # Extract individual examples
                        example_matches = re.findall(r'"([^"]*(?:\\.[^"]*)*)"', examples_text)
                        manual_json["usage_examples"] = [ex.replace('\\"', '"').replace('\\n', '\n') for ex in example_matches]
                    
                    if manual_json:
                        parsed_json = manual_json
                        logger.info(f"Successfully extracted fields manually for '{term}': {list(manual_json.keys())}")
                
                if parsed_json:
                    # Update the explanation with parsed values
                    explanation.update(parsed_json)
                    logger.info(f"Updated explanation for '{term}' with parsed data")
                else:
                    logger.error(f"All parsing strategies failed for '{term}'. Parse errors: {parse_errors}")
                    explanation["generation_note"] = f"Parse errors: {'; '.join(parse_errors)}"
                
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

def analyze_relationship(term1, term2, model_name=None):
    """
    Analyze the semantic relationship between two Japanese terms.
    
    Args:
        term1 (str): First Japanese term
        term2 (str): Second Japanese term
        model_name (str, optional): Gemini model to use. Defaults to GEMINI_DEFAULT_MODEL from config.
        
    Returns:
        dict: Analysis of the relationship
    """
    if not HAS_VALID_API_KEY:
        return {"error": "No valid Gemini API key configured"}

    current_model_name = model_name if model_name else DEFAULT_MODEL
    
    # Check cache first
    cache_key = f"gemini_relationship_{term1}_{term2}_{current_model_name}"
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
        
        Consider nuances, context, and any overlapping meanings.
        
        IMPORTANT: Your response MUST be a valid JSON object with the EXACT following structure:
        {{
            "relationship_summary": "Brief summary of the relationship (e.g., synonym, antonym, related, hierarchical)",
            "similarity_score": "A score from 0.0 to 1.0 indicating semantic similarity, where 1.0 is highly similar.",
            "key_differences": ["Difference 1", "Difference 2"],
            "key_similarities": ["Similarity 1", "Similarity 2"],
            "contextual_comparison": "How their usage might differ in context"
        }}
        
        DO NOT include any text before or after the JSON.
        DO NOT use markdown formatting or code blocks around the JSON.
        ONLY return the raw JSON object itself.
        """
        
        logger.info(f"Sending relationship analysis request to Gemini API for '{term1}' and '{term2}' using model: {current_model_name}")

        model = genai.GenerativeModel(current_model_name)
        response = model.generate_content(prompt)
        model_used = current_model_name
        
        # Log raw response
        logger.info(f"Raw Gemini API response for relationship '{term1}'-'{term2}': {response.text!r}")
        
        # Create an analysis with the raw response always included
        analysis = {
            "relationship_summary": f"Information about the relationship between '{term1}' and '{term2}' is currently unavailable.",
            "similarity_score": 0.0,
            "key_differences": ["Information not available"],
            "key_similarities": ["Information not available"],
            "contextual_comparison": "Information not available.",
            "raw_response": response.text,
            "_model_used": model_used
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
                required_fields = ["relationship_summary", "similarity_score", "key_differences", "key_similarities", "contextual_comparison"]
                for field in required_fields:
                    if field not in analysis:
                        if field == "similarity_score":
                            analysis[field] = 0.0
                        elif field in ["key_differences", "key_similarities"]:
                            analysis[field] = []
                        else:
                            analysis[field] = f"No information about {field} available"
                
                # Ensure similarity_score is float
                score_val = analysis.get("similarity_score")
                if isinstance(score_val, str):
                    analysis["similarity_score"] = float(score_val.strip())
                elif not isinstance(score_val, float):
                    analysis["similarity_score"] = 0.0
                
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
            "relationship_summary": f"An error occurred while analyzing the relationship between '{term1}' and '{term2}'.",
            "similarity_score": 0.0,
            "key_differences": ["Error occurred"],
            "key_similarities": ["Error occurred"],
            "contextual_comparison": "Error occurred",
            "error": str(e)
        }

def get_image_description(image_path, prompt_text, model_name=None):
    """
    Generate a description for an image using Gemini Vision.

    Args:
        image_path (str): Path to the image file.
        prompt_text (str): Text prompt to guide the description.
        model_name (str, optional): Gemini model to use (should be a vision-capable model). 
                                Defaults to GEMINI_DEFAULT_MODEL from config. 
                                It's recommended to use a vision model like 'gemini-pro-vision' or a multimodal one.

    Returns:
        str: The generated description or an error message.
    """
    if not HAS_VALID_API_KEY:
        return "Error: No valid Gemini API key configured"

    current_model_name = model_name if model_name else DEFAULT_MODEL
    
    # A more robust solution would be to have a separate DEFAULT_VISION_MODEL in config
    # or check capabilities if the genai library supports it.
    
    try:
        logger.info(f"Loading image from path: {image_path}")
        img = Image.open(image_path)
        
        logger.info(f"Sending image description request to Gemini API with model: {current_model_name}")

        # Warning for non-vision models (simple check)
        # gemini-1.5-pro-latest and gemini-1.5-flash-latest are multimodal
        if not any(keyword in current_model_name for keyword in ["vision", "pro-latest", "flash-latest"]):
             logger.warning(f"Model '{current_model_name}' might not be vision-capable. Consider using a specific vision or multimodal model.")

        model = genai.GenerativeModel(current_model_name)
        response = model.generate_content([prompt_text, img])
        
        logger.info(f"Raw Gemini API response for image description: {response.text!r}")
        return response.text
    except FileNotFoundError:
        logger.error(f"Image file not found at path: {image_path}")
        return f"Error: Image file not found at path: {image_path}"
    except Exception as e:
        logger.error(f"Error generating image description: {e}")
        return f"Error: {e}"

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
                # Handle MultiGraph (multiple parallel edges) vs. simple Graph
                if graph.is_multigraph():
                    # For MultiGraph, get attribute dict of the first edge key
                    edge_key = list(edge_data.keys())[0] if edge_data else 0
                    edge_attr = edge_data[edge_key] if edge_key in edge_data else {}
                else:
                    # For regular Graph, edge_data is already the attribute dict
                    edge_attr = edge_data

                # Determine edge weight – prefer explicit 'weight', otherwise fall back to nested strength fields
                edge_weight = edge_attr.get('weight')
                if edge_weight is None:
                    # Check nested synonym/antonym strength values
                    if 'synonym' in edge_attr:
                        edge_weight = edge_attr['synonym'].get('synonym_strength')
                    elif 'antonym' in edge_attr:
                        edge_weight = edge_attr['antonym'].get('antonym_strength')
                    # Final fallback
                    if edge_weight is None:
                        edge_weight = 1

                # Determine edge type – prefer explicit 'type', otherwise infer from edge key or nested keys
                edge_type = edge_attr.get('type')
                if edge_type is None:
                    # For MultiGraph, check the edge key first
                    if graph.is_multigraph() and edge_key:
                        if edge_key == 'synonym':
                            edge_type = 'synonym'
                        elif edge_key == 'antonym':
                            edge_type = 'antonym'
                        else:
                            edge_type = 'unknown'
                    else:
                        # For regular graphs, check nested keys
                        if 'synonym' in edge_attr:
                            edge_type = 'synonym'
                        elif 'antonym' in edge_attr:
                            edge_type = 'antonym'
                        else:
                            edge_type = 'unknown'

                neighbors.append({
                    'id': neighbor_id,
                    'edge_weight': edge_weight,
                    'edge_type': edge_type
                })
        
        return neighbors
    except Exception as e:
        logger.error(f"Error getting neighbors for node {node_id}: {e}")
        return []

def enhance_with_gemini(node_id, model_name=None):
    """
    Enhance a node with information from the Gemini API.
    This involves generating an explanation for the term and analyzing relationships
    with its top neighbors.

    Args:
        node_id (str): ID of the node to enhance.
        model_name (str, optional): Gemini model to use for underlying calls. 
                                Defaults to GEMINI_DEFAULT_MODEL from config.

    Returns:
        dict: Enhanced node information including explanation and relationships.
    """
    current_model_name = model_name if model_name else DEFAULT_MODEL

    if not HAS_VALID_API_KEY:
        return {
            'id': node_id,
            'explanation': {"error": "No valid Gemini API key configured"},
            'neighbors': [],
            'relationships': [],
            'status': "unavailable"
        }

    try:
        # Attempt to get explanation for the term
        explanation = generate_explanation(node_id, model_name=current_model_name)
        
        # Get neighbor information
        neighbors = get_neighbor_info(node_id)
        
        relationships = []
        if neighbors and len(neighbors) > 0:
            # Sort neighbors by edge weight and get top ones
            sorted_neighbors = sorted(neighbors, key=lambda x: x.get('edge_weight', 0), reverse=True)
            top_neighbors = sorted_neighbors[:min(3, len(sorted_neighbors))]
            
            for neighbor in top_neighbors:
                relationship = analyze_relationship(node_id, neighbor['id'], model_name=current_model_name)
                relationships.append({
                    'term1': node_id,
                    'term2': neighbor['id'],
                    'analysis': relationship
                })
                time.sleep(1)  # Add a 1-second delay to avoid hitting rate limits
        
        return {
            'id': node_id,
            'explanation': explanation,
            'neighbors': neighbors,
            'relationships': relationships,
            '_model_used_for_enhancement': current_model_name
        }
    except Exception as e:
        logger.error(f"Error enhancing node {node_id} with Gemini: {e}")
        return {
            'id': node_id,
            'explanation': {
                'overview': f"An error occurred while retrieving information for '{node_id}'.",
                'cultural_context': "No information available due to an error.",
                'usage_examples': [],
                'nuances': "No information available.",
                'error': str(e)
            },
            'neighbors': get_neighbor_info(node_id),
            'relationships': [],
            'error': str(e)
        } 