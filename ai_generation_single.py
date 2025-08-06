"""
AI Generation Script for Japanese Lexical Graph

This script generates AI-powered lexical relations for a single node in
the Japanese lexical graph. It is designed to be incorporated into the
Node Information pane as an "AI Generation" tab.
"""

import json
import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
import pickle
import networkx as nx
from cache_helper import cache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

def get_graph():
    """Load the NetworkX graph from pickle file."""
    try:
        # Find the correct path to the pickle file
        pickle_paths = [
            'G_synonyms_2024_09_18.pickle',  # Root directory
            os.path.join('graph_models', 'G_synonyms_2024_09_18.pickle')  # In graph_models directory
        ]
        
        graph_file = None
        for path in pickle_paths:
            if os.path.exists(path):
                graph_file = path
                break
        
        if not graph_file:
            logger.error("Graph pickle file not found")
            return nx.Graph()  # Return empty graph if file not found
        
        with open(graph_file, 'rb') as f:
            G = pickle.load(f)
        logger.info(f"Loaded graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        return G
    except Exception as e:
        logger.error(f"Error loading graph: {e}")
        return nx.Graph()  # Return empty graph on error

def generate_lexical_relations(node_id, G=None, model_name=DEFAULT_MODEL):
    """
    Generate AI-powered lexical relations for a single node.
    
    Args:
        node_id (str): The ID of the node (typically a Japanese word/kanji)
        G (NetworkX graph): Optional in-memory graph to use instead of loading from disk
        model_name (str): Gemini model to use
        
    Returns:
        dict: Generated lexical relations
    """
    if not HAS_VALID_API_KEY:
        return {"error": "No valid Gemini API key configured"}
    
    # Check cache first
    cache_key = f"ai_generation_{node_id}_{model_name}"
    cached_result = cache.get(cache_key)
    if cached_result:
        try:
            return json.loads(cached_result)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache for node '{node_id}'. Regenerating content.")
    
    # Prefer the provided in-memory graph; fall back to loading from disk if not supplied
    if G is None:
        G = get_graph()
    
    # Check if node exists in the graph
    if node_id not in G.nodes():
        return {
            "error": f"Node '{node_id}' not found in the graph",
            "source_lexeme": {
                "lemma": node_id,
                "hiragana": "",
                "POS": "",
                "translation": ""
            },
            "lexeme_synonyms": [],
            "lexeme_antonyms": []
        }
    
    # Get node data from the graph
    node_data = G.nodes[node_id]
    hiragana = node_data.get('hiragana', '')
    pos = node_data.get('pos', '')
    translation = node_data.get('translation', '')
    
    # Prepare additional context from existing graph data
    existing_neighbors = []
    for neighbor in G.neighbors(node_id):
        neighbor_data = G.nodes[neighbor]
        edge_data = G.get_edge_data(node_id, neighbor)
        
        # Handle edge types and add to existing neighbors
        relation_type = "unknown"
        if edge_data:
            # Handle MultiGraph (multiple parallel edges) vs. simple Graph
            if hasattr(G, 'is_multigraph') and G.is_multigraph():
                # For MultiGraph, get attribute dict of the first edge key
                edge_key = list(edge_data.keys())[0] if edge_data else 0
                edge_attr = edge_data[edge_key] if edge_key in edge_data else {}
            else:
                # For regular Graph, edge_data is already the attribute dict
                edge_attr = edge_data
            
            # Determine edge type – prefer explicit 'type', otherwise infer from edge key or nested keys
            relation_type = edge_attr.get('type')
            if relation_type is None:
                # For MultiGraph, check the edge key first
                if hasattr(G, 'is_multigraph') and G.is_multigraph() and 'edge_key' in locals():
                    if edge_key == 'synonym':
                        relation_type = 'synonym'
                    elif edge_key == 'antonym':
                        relation_type = 'antonym'
                    else:
                        relation_type = 'unknown'
                else:
                    # For regular graphs, check nested keys
                    if 'synonym' in edge_attr:
                        relation_type = 'synonym'
                    elif 'antonym' in edge_attr:
                        relation_type = 'antonym'
                    else:
                        relation_type = 'unknown'
            
        existing_neighbors.append({
            "node": neighbor,
            "hiragana": neighbor_data.get('hiragana', ''),
            "translation": neighbor_data.get('translation', ''),
            "relation_type": relation_type
        })
    
    # Create the prompt
    prompt = f"""
    You are a Japanese language expert AI assistant. Your task is to analyze the Japanese lexeme "{node_id}" and generate accurate lexical relations.

    TASKS:
    1. Provide accurate transliteration and grammatical information for "{node_id}"
    2. Generate English translation with correct part of speech
    3. Create comprehensive lists of synonyms (at least 10) and antonyms (at least 5) in Japanese
    4. Include ALL required attributes for each relation as specified below
    
    OUTPUT FORMAT:
    Return ONLY a valid JSON object with the following EXACT structure:

    {{
      "source_lexeme": {{
        "lemma": "{node_id}",
        "hiragana": "string", # Hiragana reading of the lemma
        "POS": "string",      # Part of speech (名詞, 動詞, 形容詞, etc.)
        "translation": {{
          "target_language": "English",
          "target_lemma": "string",   # English translation
          "target_POS": "string"      # English part of speech (noun, verb, adj, etc.)
        }}
      }},
      "lexeme_synonyms": [
        {{
          "synonym_lemma": "string",          # Japanese synonym (kanji/kana)
          "synonym_hiragana": "string",       # Hiragana reading of the synonym
          "POS": "string",                    # Part of speech
          "synonym_strenght": 0.0 to 1.0,     # Float value (0.0 to 1.0) - MUST include decimal point
          "synonym_translation": "string",    # English translation of synonym
          "mutual_sense": "string",           # Shared meaning in Japanese
          "mutual_sense_hiragana": "string",  # Hiragana reading of mutual_sense
          "mutual_sense_translation": "string", # English translation of mutual_sense
          "synonymy_domain": "string",        # Domain/context in Japanese
          "synonymy_domain_hiragana": "string", # Hiragana reading of domain
          "synonymy_domain_translation": "string", # English translation of domain
          "synonymy_explanation": "string"    # Explanation of synonymy in English
        }},
        # Repeat for at least 14 more synonyms...
      ],
      "lexeme_antonyms": [
        {{
          "antonym_lemma": "string",          # Japanese antonym (kanji/kana) 
          "antonym_hiragana": "string",       # Hiragana reading of the antonym
          "POS": "string",                    # Part of speech
          "antonym_translation": "string",    # English translation of antonym
          "antonym_strenght": 0.0 to 1.0,     # Float value (0.0 to 1.0) - MUST include decimal point
          "antonymy_domain": "string",        # Domain/context in Japanese
          "antonymy_domain_hiragana": "string", # Hiragana reading of domain
          "antonymy_domain_translation": "string", # English translation of domain
          "antonym_explanation": "string"     # Explanation of antonymy in English
        }},
        # Repeat for at least 4 more antonyms...
      ]
    }}

    IMPORTANT RULES:
    - Return ONLY valid JSON - no explanations, markdown, or other text
    - ALWAYS include ALL fields shown above for each object
    - Use consistent POS values (名詞, 動詞, 形容詞, etc.) for Japanese terms
    - ALL 'strength' values MUST be floating-point numbers between 0.0 and 1.0 (with decimal point)
    - Ensure all Japanese text has corresponding hiragana readings
    - DO NOT include any null or empty values - provide meaningful content for all fields
    - Ensure proper nesting of objects and arrays
    - Check that all JSON syntax is valid (quotes, commas, brackets)
    - Use correct spelling 'strenght' (not 'strength') to maintain compatibility

    COMMON ERRORS TO AVOID:
    - Missing required fields for some entries
    - Incorrect JSON syntax (missing commas, unmatched brackets)
    - Non-float values for strength fields (must be like 0.8, not 0.8f or "0.8")
    - Inconsistent structure across entries
    """
    
    # Provide existing data as context if available
    if hiragana or pos or translation or existing_neighbors:
        prompt += "\n\nADDITIONAL CONTEXT (use this to make your response more accurate):\n"
        if hiragana:
            prompt += f"- Existing hiragana reading: {hiragana}\n"
        if pos:
            prompt += f"- Existing part of speech: {pos}\n"
        if translation:
            prompt += f"- Existing English translation: {translation}\n"
        if existing_neighbors:
            prompt += "- Existing related terms in the lexical graph:\n"
            for neighbor in existing_neighbors[:10]:  # Limit to 10 neighbors to avoid too large prompt
                prompt += f"  • {neighbor['node']} ({neighbor['hiragana']}): {neighbor['translation']} [{neighbor['relation_type']}]\n"
    
    try:
        logger.info(f"Sending request to Gemini API for node: {node_id} using model: {model_name}")
        
        # Try working models in order
        models_to_try = ['gemini-2.0-flash', 'gemini-2.0-flash-lite']
        if model_name not in models_to_try:
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
        
        # If all models failed
        if response is None:
            logger.error("All model attempts failed")
            return {
                "error": "Failed to generate content with any model",
                "source_lexeme": {
                    "lemma": node_id,
                    "hiragana": hiragana,
                    "POS": pos,
                    "translation": translation
                }
            }
        
        # Log the raw response for debugging
        logger.info(f"Raw Gemini API response for node '{node_id}': {response.text!r}")
        
        # Parse response as JSON
        try:
            # Clean the response text - try to extract JSON from various formats
            json_text = response.text.strip()
            
            # Check if response is wrapped in code blocks and extract just the JSON part
            import re
            json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
            if json_block_match:
                json_text = json_block_match.group(1).strip()
                logger.info(f"Extracted JSON from code block for '{node_id}'")
            
            # Try to find JSON object if not a complete JSON yet
            if not (json_text.startswith('{') and json_text.endswith('}')):
                json_object_match = re.search(r'({[\s\S]*?})', json_text)
                if json_object_match:
                    json_text = json_object_match.group(1).strip()
                    logger.info(f"Extracted JSON object for '{node_id}'")
            
            # Parse the cleaned JSON
            logger.info(f"Parsing JSON for '{node_id}'")
            result = json.loads(json_text)
            
            # Add model information
            result["_model_used"] = model_used
            
            # Cache the result for 7 days
            cache.set(cache_key, json.dumps(result), 7 * 24 * 60 * 60)
            
            return result
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Invalid JSON response for node '{node_id}': {e}")
            return {
                "error": f"Failed to parse response: {str(e)}",
                "raw_response": response.text,
                "source_lexeme": {
                    "lemma": node_id,
                    "hiragana": hiragana,
                    "POS": pos,
                    "translation": translation
                }
            }
    
    except Exception as e:
        logger.error(f"Error generating lexical relations for {node_id}: {e}")
        return {
            "error": str(e),
            "source_lexeme": {
                "lemma": node_id,
                "hiragana": hiragana,
                "POS": pos,
                "translation": translation
            }
        }

def add_generated_relations_to_graph(node_id, generated_data, G=None):
    """
    Add AI-generated lexical relations to the graph.
    
    Args:
        node_id (str): The ID of the node
        generated_data (dict): Generated lexical relations data
        G (NetworkX graph): Optional in-memory graph to use instead of loading from disk
        
    Returns:
        dict: Summary of changes made to the graph
    """
    if G is None:
        G = get_graph()
    if node_id not in G.nodes():
        return {"error": f"Node '{node_id}' not found in the graph"}
    
    changes = {
        "synonyms_added": 0,
        "antonyms_added": 0,
        "updated_nodes": [],
        "skipped_nodes": [] # Track nodes we had to skip
    }
    
    # Update the source node data if needed
    source_data = generated_data.get('source_lexeme', {})
    node_updated = False
    
    for key, value in source_data.items():
        if key != 'lemma' and value and (key not in G.nodes[node_id] or not G.nodes[node_id].get(key)):
            G.nodes[node_id][key] = value
            node_updated = True
    
    if node_updated:
        changes["updated_nodes"].append(node_id)
    
    # Add synonyms to the graph
    for synonym in generated_data.get('lexeme_synonyms', []):
        synonym_lemma = synonym.get('synonym_lemma')
        if not synonym_lemma:
            continue
        
        try:
            # Add the synonym node if it doesn't exist
            if synonym_lemma not in G.nodes():
                G.add_node(synonym_lemma)
                G.nodes[synonym_lemma]['hiragana'] = synonym.get('synonym_hiragana', '')
                G.nodes[synonym_lemma]['POS'] = synonym.get('POS', '')
                G.nodes[synonym_lemma]['pos'] = synonym.get('POS', '')
                G.nodes[synonym_lemma]['translation'] = synonym.get('synonym_translation', '')
                changes["updated_nodes"].append(synonym_lemma)
            
            # Add or update the edge
            if not G.has_edge(node_id, synonym_lemma) or 'synonym' not in G[node_id][synonym_lemma]:
                # Compute strength once to reuse
                synonym_strength = synonym.get('synonym_strenght', 0.5)

                # Create synonym edge data with explicit weight and type metadata
                synonym_data = {
                    'synonym': {
                        'synonym_strength': synonym_strength,
                        'mutual_sense': synonym.get('mutual_sense', ''),
                        'mutual_sense_hiragana': synonym.get('mutual_sense_hiragana', ''),
                        'mutual_sense_translation': synonym.get('mutual_sense_translation', ''),
                        'synonymy_domain': synonym.get('synonymy_domain', ''),
                        'synonymy_domain_hiragana': synonym.get('synonymy_domain_hiragana', ''),
                        'synonymy_domain_translation': synonym.get('synonymy_domain_translation', ''),
                        'synonymy_explanation': synonym.get('synonymy_explanation', '')
                    },
                    'type': 'synonym',  # Explicitly mark relationship type
                    'weight': synonym_strength  # Top-level weight for easy access
                }

                # Add or update the edge with new metadata
                if G.has_edge(node_id, synonym_lemma):
                    # For MultiGraph, update the synonym edge specifically
                    if hasattr(G, 'is_multigraph') and G.is_multigraph():
                        if 'synonym' in G[node_id][synonym_lemma]:
                            G[node_id][synonym_lemma]['synonym'].update(synonym_data['synonym'])
                            G[node_id][synonym_lemma]['synonym']['type'] = 'synonym'
                            G[node_id][synonym_lemma]['synonym']['weight'] = synonym_strength
                        else:
                            G.add_edge(node_id, synonym_lemma, key='synonym', **synonym_data)
                    else:
                        G[node_id][synonym_lemma]['synonym'] = synonym_data['synonym']
                        G[node_id][synonym_lemma]['type'] = 'synonym'
                        G[node_id][synonym_lemma]['weight'] = synonym_strength
                else:
                    # Add new edge with proper key for MultiGraph
                    if hasattr(G, 'is_multigraph') and G.is_multigraph():
                        G.add_edge(node_id, synonym_lemma, key='synonym', **synonym_data)
                    else:
                        G.add_edge(node_id, synonym_lemma, **synonym_data)

                changes["synonyms_added"] += 1
        except Exception as e:
            logger.warning(f"Error adding synonym '{synonym_lemma}': {e}")
            changes["skipped_nodes"].append({"node": synonym_lemma, "reason": str(e), "type": "synonym"})
    
    # Add antonyms to the graph
    for antonym in generated_data.get('lexeme_antonyms', []):
        antonym_lemma = antonym.get('antonym_lemma')
        if not antonym_lemma:
            continue
        
        try:
            # Add the antonym node if it doesn't exist
            if antonym_lemma not in G.nodes():
                G.add_node(antonym_lemma)
                G.nodes[antonym_lemma]['hiragana'] = antonym.get('antonym_hiragana', '')
                G.nodes[antonym_lemma]['POS'] = antonym.get('POS', '')
                G.nodes[antonym_lemma]['pos'] = antonym.get('POS', '')
                G.nodes[antonym_lemma]['translation'] = antonym.get('antonym_translation', '')
                changes["updated_nodes"].append(antonym_lemma)
            
            # Add or update the edge
            if not G.has_edge(node_id, antonym_lemma) or 'antonym' not in G[node_id][antonym_lemma]:
                # Compute antonym strength once
                antonym_strength = antonym.get('antonym_strenght', 0.5)

                # Create antonym edge data with metadata
                antonym_data = {
                    'antonym': {
                        'antonym_strength': antonym_strength,
                        'antonymy_domain': antonym.get('antonymy_domain', ''),
                        'antonymy_domain_hiragana': antonym.get('antonymy_domain_hiragana', ''),
                        'antonymy_domain_translation': antonym.get('antonymy_domain_translation', ''),
                        'antonym_explanation': antonym.get('antonym_explanation', '')
                    },
                    'type': 'antonym',
                    'weight': antonym_strength
                }

                # Add or update the edge
                if G.has_edge(node_id, antonym_lemma):
                    # For MultiGraph, update the antonym edge specifically
                    if hasattr(G, 'is_multigraph') and G.is_multigraph():
                        if 'antonym' in G[node_id][antonym_lemma]:
                            G[node_id][antonym_lemma]['antonym'].update(antonym_data['antonym'])
                            G[node_id][antonym_lemma]['antonym']['type'] = 'antonym'
                            G[node_id][antonym_lemma]['antonym']['weight'] = antonym_strength
                        else:
                            G.add_edge(node_id, antonym_lemma, key='antonym', **antonym_data)
                    else:
                        G[node_id][antonym_lemma]['antonym'] = antonym_data['antonym']
                        G[node_id][antonym_lemma]['type'] = 'antonym'
                        G[node_id][antonym_lemma]['weight'] = antonym_strength
                else:
                    # Add new edge with proper key for MultiGraph
                    if hasattr(G, 'is_multigraph') and G.is_multigraph():
                        G.add_edge(node_id, antonym_lemma, key='antonym', **antonym_data)
                    else:
                        G.add_edge(node_id, antonym_lemma, **antonym_data)

                changes["antonyms_added"] += 1
        except Exception as e:
            logger.warning(f"Error adding antonym '{antonym_lemma}': {e}")
            changes["skipped_nodes"].append({"node": antonym_lemma, "reason": str(e), "type": "antonym"})
    
    # Save the updated graph
    try:
        # Use the same filename search logic as `get_graph()` so we overwrite the correct file
        pickle_paths = [
            os.path.join('graph_models', 'G_synonyms_2024_09_18.pickle'),
            'G_synonyms_2024_09_18.pickle'
        ]

        pickle_path = None
        for p in pickle_paths:
            if os.path.exists(p):
                pickle_path = p
                break

        # Default to first path if nothing found (new file will be created)
        if pickle_path is None:
            pickle_path = pickle_paths[0]

        with open(pickle_path, 'wb') as f:
            pickle.dump(G, f)
        logger.info(
            f"Graph saved to {pickle_path} with {changes['synonyms_added']} new synonyms and {changes['antonyms_added']} new antonyms"
        )
        # Optionally, you might also want to timestamp backups or keep versions here
    except Exception as e:
        logger.error(f"Error saving graph: {e}")
        changes["error_saving"] = str(e)
    
    return changes

# Flask API endpoint function that can be imported in app.py
def generate_node_relations(node_id, G=None):
    """
    Generate AI-powered lexical relations for a node and add them to the graph.
    
    This function can be imported and used as a Flask endpoint.
    
    Args:
        node_id (str): The ID of the node
        G (NetworkX graph): Optional in-memory graph to use instead of loading from disk
        
    Returns:
        dict: Generated data and changes made to the graph
    """
    if not is_available():
        return {"error": "Gemini API is not available. Please check your API key."}
    
    # Generate relations
    generated_data = generate_lexical_relations(node_id, G=G)
    
    # Check for generation error
    if "error" in generated_data and not generated_data.get('source_lexeme', {}).get('lemma'):
        return {
            "status": "error",
            "message": generated_data["error"],
            "generated_data": generated_data
        }
    
    # Add to graph
    changes = add_generated_relations_to_graph(node_id, generated_data, G=G)
    
    return {
        "status": "success" if "error" not in changes else "partial_success",
        "message": f"Generated {changes.get('synonyms_added', 0)} synonyms and {changes.get('antonyms_added', 0)} antonyms for {node_id}",
        "generated_data": generated_data,
        "changes": changes
    }

if __name__ == "__main__":
    # Simple test code when script is run directly
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ai_generation_single.py <japanese_term>")
        sys.exit(1)
    
    term = sys.argv[1]
    print(f"Generating lexical relations for {term}...")
    
    G_cli = get_graph()
    result = generate_node_relations(term, G_cli)
    print(json.dumps(result, indent=2, ensure_ascii=False)) 