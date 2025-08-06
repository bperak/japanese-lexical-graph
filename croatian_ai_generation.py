#!/usr/bin/env python
"""
Croatian AI Generation Script

This script generates AI-powered lexical relations for Croatian nodes in
the Croatian lexical graph. It is adapted from the Japanese version
and uses Gemini AI to generate synonyms and antonyms.
"""

import json
import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
import pickle
import networkx as nx
from cache_helper import cache
from croatian_helper import load_croatian_graph, save_croatian_graph, CROATIAN_POS_MAPPING, get_croatian_node_info
import config

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

def generate_croatian_lexical_relations(node_id, G=None, model_name=DEFAULT_MODEL):
    """
    Generate AI-powered lexical relations for a Croatian node.
    
    Args:
        node_id (str): The ID of the Croatian node (lempos format)
        G (NetworkX graph): Optional in-memory graph to use instead of loading from disk
        model_name (str): Gemini model to use
        
    Returns:
        dict: Generated lexical relations
    """
    if not HAS_VALID_API_KEY:
        return {"error": "No valid Gemini API key configured"}
    
    # Check cache first
    cache_key = f"croatian_ai_generation_{node_id}_{model_name}"
    cached_result = cache.get(cache_key)
    if cached_result:
        try:
            return json.loads(cached_result)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache for node '{node_id}'. Regenerating content.")
    
    # Load Croatian graph if not provided
    if G is None:
        G = load_croatian_graph()
        if G is None:
            return {"error": "Failed to load Croatian graph"}
    
    # Check if node exists in the graph
    if node_id not in G.nodes():
        return {
            "error": f"Node '{node_id}' not found in the Croatian graph",
            "source_lexeme": {
                "lemma": node_id,
                "natuknica": "",
                "pos": "",
                "translation": ""
            },
            "lexeme_synonyms": [],
            "lexeme_antonyms": []
        }
    
    # Get node data from the graph
    node_data = G.nodes[node_id]
    natuknica = node_data.get('natuknica', '')
    pos = node_data.get('pos', '')
    upos = node_data.get('UPOS', '')
    translation = node_data.get('translation', '')
    tekst = node_data.get('tekst', '')
    
    # Prepare additional context from existing graph data
    existing_neighbors = []
    for neighbor in G.neighbors(node_id):
        neighbor_data = G.nodes[neighbor]
        edge_data = G.get_edge_data(node_id, neighbor)
        
        # Handle edge types and add to existing neighbors
        relation_type = "connected"
        if edge_data:
            # Check for synonym relationships
            if 'synonym' in edge_data:
                relation_type = "synonym"
            elif 'antonym' in edge_data:
                relation_type = "antonym"
            
        existing_neighbors.append({
            "node": neighbor,
            "natuknica": neighbor_data.get('natuknica', ''),
            "translation": neighbor_data.get('translation', ''),
            "pos": neighbor_data.get('UPOS', ''),
            "relation_type": relation_type
        })
    
    # Create the prompt for Croatian
    prompt = f"""
    You are a Croatian language expert AI assistant. Your task is to analyze the Croatian lexeme "{node_id}" and generate accurate lexical relations.

    TASKS:
    1. Provide accurate grammatical information for "{node_id}"
    2. Generate English translation with correct part of speech
    3. Create comprehensive lists of synonyms (at least 10) and antonyms (at least 5) in Croatian
    4. Include ALL required attributes for each relation as specified below
    
    OUTPUT FORMAT:
    Return ONLY a valid JSON object with the following EXACT structure:

    {{
      "source_lexeme": {{
        "lemma": "{node_id}",
        "natuknica": "string",       # Croatian word (without POS tag)
        "pos": "string",             # Croatian POS tag
        "UPOS": "string",            # Universal POS tag (NOUN, VERB, ADJ, etc.)
        "translation": {{
          "target_language": "English",
          "target_lemma": "string",   # English translation
          "target_POS": "string"      # English part of speech (noun, verb, adjective, etc.)
        }},
        "tekst": "string"            # Definition or explanation in Croatian
      }},
      "lexeme_synonyms": [
        {{
          "synonym_lemma": "string",          # Croatian synonym
          "synonym_natuknica": "string",      # Croatian word without POS
          "POS": "string",                    # Croatian POS tag
          "UPOS": "string",                   # Universal POS tag
          "synonym_strength": 0.0,            # Float value (0.0 to 1.0) - MUST include decimal point
          "synonym_translation": "string",    # English translation of synonym
          "mutual_sense": "string",           # Shared meaning in Croatian
          "mutual_sense_translation": "string", # English translation of mutual_sense
          "synonymy_domain": "string",        # Domain/context in Croatian
          "synonymy_domain_translation": "string", # English translation of domain
          "synonymy_explanation": "string"    # Explanation of synonymy in English
        }},
        # Repeat for at least 9 more synonyms...
      ],
      "lexeme_antonyms": [
        {{
          "antonym_lemma": "string",          # Croatian antonym
          "antonym_natuknica": "string",      # Croatian word without POS
          "POS": "string",                    # Croatian POS tag
          "UPOS": "string",                   # Universal POS tag
          "antonym_translation": "string",    # English translation of antonym
          "antonym_strength": 0.0,            # Float value (0.0 to 1.0) - MUST include decimal point
          "antonymy_domain": "string",        # Domain/context in Croatian
          "antonymy_domain_translation": "string", # English translation of domain
          "antonym_explanation": "string"     # Explanation of antonymy in English
        }},
        # Repeat for at least 4 more antonyms...
      ]
    }}

    IMPORTANT RULES:
    - Return ONLY valid JSON - no explanations, markdown, or other text
    - ALWAYS include ALL fields shown above for each object
    - Use consistent UNIVERSAL POS values (NOUN, VERB, ADJ, ADV, etc.) for ALL POS fields
    - For Croatian terms, use Universal POS tags in both 'POS' and 'UPOS' fields
    - ALL 'strength' values MUST be floating-point numbers between 0.0 and 1.0 (with decimal point)
    - DO NOT include any null or empty values - provide meaningful content for all fields
    - Ensure proper nesting of objects and arrays
    - Check that all JSON syntax is valid (quotes, commas, brackets)
    - Use correct spelling 'strength' (not 'strenght') for consistency

    UNIVERSAL POS TAGS TO USE:
    - NOUN: imenica (noun)
    - VERB: glagol (verb)  
    - ADJ: pridjev (adjective)
    - ADV: prilog (adverb)
    - PRON: zamjenica (pronoun)
    - ADP: prijedlog (preposition)
    - CCONJ: veznik (conjunction)
    - NUM: broj (numeral)
    - PART: čestica (particle)
    - INTJ: uzvik (interjection)

    COMMON ERRORS TO AVOID:
    - Missing required fields for some entries
    - Incorrect JSON syntax (missing commas, unmatched brackets)
    - Non-float values for strength fields (must be like 0.8, not 0.8f or "0.8")
    - Inconsistent structure across entries
    """
    
    # Provide existing data as context if available
    if natuknica or pos or translation or tekst or existing_neighbors:
        prompt += "\n\nADDITIONAL CONTEXT (use this to make your response more accurate):\n"
        if natuknica:
            prompt += f"- Existing Croatian word: {natuknica}\n"
        if pos:
            prompt += f"- Existing Croatian POS: {pos}\n"
        if upos:
            prompt += f"- Existing Universal POS: {upos}\n"
        if translation:
            prompt += f"- Existing English translation: {translation}\n"
        if tekst:
            prompt += f"- Existing definition: {tekst[:200]}...\n"
        if existing_neighbors:
            prompt += "- Existing related terms in the lexical graph:\n"
            for neighbor in existing_neighbors[:10]:  # Limit to 10 neighbors
                prompt += f"  • {neighbor['node']} ({neighbor['natuknica']}): {neighbor['translation']} [{neighbor['relation_type']}]\n"
    
    try:
        logger.info(f"Sending request to Gemini API for Croatian node: {node_id} using model: {model_name}")
        
        # Try working models in order
        models_to_try = ['gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-1.5-flash']
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
                    "natuknica": natuknica,
                    "pos": pos,
                    "translation": translation
                }
            }
        
        # Log the raw response for debugging
        logger.info(f"Raw Gemini API response for Croatian node '{node_id}': {response.text!r}")
        
        # Try to parse the JSON response
        try:
            # Clean up the response - remove markdown code blocks if present
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            generated_data = json.loads(response_text)
            
            # Add metadata
            generated_data['_model_used'] = model_used
            generated_data['_raw_response'] = response.text
            
            # Cache the result
            cache.set(cache_key, json.dumps(generated_data))  # Cache the result
            
            logger.info(f"Successfully generated and cached Croatian lexical relations for '{node_id}'")
            return generated_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response for Croatian node '{node_id}': {e}")
            return {
                "error": f"Invalid JSON response: {e}",
                "raw_response": response.text,
                "source_lexeme": {
                    "lemma": node_id,
                    "natuknica": natuknica,
                    "pos": pos,
                    "translation": translation
                }
            }
            
    except Exception as e:
        logger.error(f"Error generating Croatian lexical relations for '{node_id}': {e}")
        return {
            "error": f"API request failed: {e}",
            "source_lexeme": {
                "lemma": node_id,
                "natuknica": natuknica,
                "pos": pos,
                "translation": translation
            }
        }

def add_generated_relations_to_croatian_graph(node_id, generated_data, G=None):
    """
    Add generated lexical relations to the Croatian graph.
    
    Args:
        node_id (str): The source node ID
        generated_data (dict): Generated lexical relations
        G (NetworkX graph): Optional in-memory graph to use instead of loading from disk
        
    Returns:
        dict: Summary of changes made
    """
    if G is None:
        G = load_croatian_graph()
        if G is None:
            return {"error": "Failed to load Croatian graph"}
    
    changes = {
        "synonyms_added": 0,
        "antonyms_added": 0,
        "nodes_added": 0,
        "edges_added": 0,
        "updated_nodes": [],
        "translations_generated": 0,
        "pos_inferred": 0
    }
    
    # Add synonyms to the graph
    for synonym in generated_data.get('lexeme_synonyms', []):
        synonym_lemma = synonym.get('synonym_lemma')
        if not synonym_lemma:
            continue
        
        try:
            # Create lempos format if not already
            synonym_pos = synonym.get('UPOS', '')
            synonym_natuknica = synonym.get('synonym_natuknica', synonym_lemma)
            if '-' not in synonym_lemma and synonym_pos:
                synonym_node_id = f"{synonym_natuknica}-{synonym_pos}"
            else:
                synonym_node_id = synonym_lemma
            
            # Add the synonym node if it doesn't exist
            if synonym_node_id not in G.nodes():
                G.add_node(synonym_node_id)
                
                # Set basic attributes from AI generation
                natuknica = synonym.get('synonym_natuknica', '')
                pos = synonym.get('POS', '')
                upos = synonym.get('UPOS', '')
                translation = synonym.get('synonym_translation', '')
                
                # Generate missing translation and POS if needed
                if not translation or not pos or not upos:
                    logger.info(f"Generating translation and POS for new synonym node: {synonym_node_id}")
                    ai_result = generate_translation_and_pos(
                        word=synonym_node_id,
                        natuknica=natuknica,
                        context=f"Synonym of {node_id}"
                    )
                    
                    if 'error' not in ai_result:
                        if not translation:
                            translation = ai_result.get('translation', '')
                            changes["translations_generated"] += 1
                        if not pos or not upos:
                            # Use Universal POS tags for consistency
                            universal_pos = ai_result.get('upos', '') or ai_result.get('pos', '')
                            if not pos:
                                pos = universal_pos
                            if not upos:
                                upos = universal_pos
                            changes["pos_inferred"] += 1
                        
                        logger.info(f"✅ Generated for '{synonym_node_id}': translation='{translation}', pos='{pos}', upos='{upos}'")
                    else:
                        logger.warning(f"Failed to generate translation/POS for '{synonym_node_id}': {ai_result.get('error')}")
                
                # Set node attributes
                G.nodes[synonym_node_id]['natuknica'] = natuknica
                G.nodes[synonym_node_id]['pos'] = upos  # Use Universal POS for consistency
                G.nodes[synonym_node_id]['UPOS'] = upos
                G.nodes[synonym_node_id]['translation'] = translation
                G.nodes[synonym_node_id]['language'] = 'croatian'
                G.nodes[synonym_node_id]['source'] = 'ai_generated'
                
                changes["nodes_added"] += 1
                changes["updated_nodes"].append(synonym_node_id)
            
            # Add or update the synonym edge
            if not G.has_edge(node_id, synonym_node_id) or 'synonym' not in G[node_id].get(synonym_node_id, {}):
                # For MultiGraph, add edge with 'synonym' key
                G.add_edge(node_id, synonym_node_id, key='synonym',
                          synonym={
                              'synonym_strength': synonym.get('synonym_strength', 0.5),
                              'mutual_sense': synonym.get('mutual_sense', ''),
                              'mutual_sense_translation': synonym.get('mutual_sense_translation', ''),
                              'synonymy_domain': synonym.get('synonymy_domain', ''),
                              'synonymy_domain_translation': synonym.get('synonymy_domain_translation', ''),
                              'synonymy_explanation': synonym.get('synonymy_explanation', '')
                          },
                          type='synonym',
                          weight=synonym.get('synonym_strength', 0.5))
                changes["synonyms_added"] += 1
                changes["edges_added"] += 1
                
        except Exception as e:
            logger.error(f"Error adding synonym '{synonym_lemma}' to graph: {e}")
    
    # Add antonyms to the graph
    for antonym in generated_data.get('lexeme_antonyms', []):
        antonym_lemma = antonym.get('antonym_lemma')
        if not antonym_lemma:
            continue
        
        try:
            # Create lempos format if not already
            antonym_pos = antonym.get('UPOS', '')
            antonym_natuknica = antonym.get('antonym_natuknica', antonym_lemma)
            if '-' not in antonym_lemma and antonym_pos:
                antonym_node_id = f"{antonym_natuknica}-{antonym_pos}"
            else:
                antonym_node_id = antonym_lemma
            
            # Add the antonym node if it doesn't exist
            if antonym_node_id not in G.nodes():
                G.add_node(antonym_node_id)
                
                # Set basic attributes from AI generation
                natuknica = antonym.get('antonym_natuknica', '')
                pos = antonym.get('POS', '')
                upos = antonym.get('UPOS', '')
                translation = antonym.get('antonym_translation', '')
                
                # Generate missing translation and POS if needed
                if not translation or not pos or not upos:
                    logger.info(f"Generating translation and POS for new antonym node: {antonym_node_id}")
                    ai_result = generate_translation_and_pos(
                        word=antonym_node_id,
                        natuknica=natuknica,
                        context=f"Antonym of {node_id}"
                    )
                    
                    if 'error' not in ai_result:
                        if not translation:
                            translation = ai_result.get('translation', '')
                            changes["translations_generated"] += 1
                        if not pos or not upos:
                            # Use Universal POS tags for consistency
                            universal_pos = ai_result.get('upos', '') or ai_result.get('pos', '')
                            if not pos:
                                pos = universal_pos
                            if not upos:
                                upos = universal_pos
                            changes["pos_inferred"] += 1
                        
                        logger.info(f"✅ Generated for '{antonym_node_id}': translation='{translation}', pos='{pos}', upos='{upos}'")
                    else:
                        logger.warning(f"Failed to generate translation/POS for '{antonym_node_id}': {ai_result.get('error')}")
                
                # Set node attributes
                G.nodes[antonym_node_id]['natuknica'] = natuknica
                G.nodes[antonym_node_id]['pos'] = upos  # Use Universal POS for consistency
                G.nodes[antonym_node_id]['UPOS'] = upos
                G.nodes[antonym_node_id]['translation'] = translation
                G.nodes[antonym_node_id]['language'] = 'croatian'
                G.nodes[antonym_node_id]['source'] = 'ai_generated'
                
                changes["nodes_added"] += 1
                changes["updated_nodes"].append(antonym_node_id)
            
            # Add or update the antonym edge
            if not G.has_edge(node_id, antonym_node_id) or 'antonym' not in G[node_id].get(antonym_node_id, {}):
                # For MultiGraph, add edge with 'antonym' key
                G.add_edge(node_id, antonym_node_id, key='antonym',
                          antonym={
                              'antonym_strength': antonym.get('antonym_strength', 0.5),
                              'antonymy_domain': antonym.get('antonymy_domain', ''),
                              'antonymy_domain_translation': antonym.get('antonymy_domain_translation', ''),
                              'antonym_explanation': antonym.get('antonym_explanation', '')
                          },
                          type='antonym',
                          weight=antonym.get('antonym_strength', 0.5))
                changes["antonyms_added"] += 1
                changes["edges_added"] += 1
                
        except Exception as e:
            logger.error(f"Error adding antonym '{antonym_lemma}' to graph: {e}")
    
    # Save the updated graph
    if save_croatian_graph(G):
        logger.info(f"Successfully saved Croatian graph with {changes['edges_added']} new edges, {changes['nodes_added']} new nodes, {changes['translations_generated']} translations generated, {changes['pos_inferred']} POS tags inferred")
    else:
        logger.error("Failed to save Croatian graph")
    
    return changes

def test_ai_generation():
    """
    Test function for Croatian AI generation.
    """
    print("🧪 Testing Croatian AI Generation")
    print("=" * 40)
    
    # Check API availability
    if not is_available():
        print("❌ Gemini API not available")
        return
    
    print("✅ Gemini API available")
    
    # Load Croatian graph
    G = load_croatian_graph()
    if G is None:
        print("❌ Failed to load Croatian graph")
        return
    
    print(f"✅ Croatian graph loaded: {G.number_of_nodes()} nodes")
    
    # Test with a sample node
    test_node = "ljubav-NOUN"
    if test_node in G.nodes():
        print(f"🧪 Testing AI generation for: {test_node}")
        print("📡 Making API call...")
        result = generate_croatian_lexical_relations(test_node, G)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("✅ AI generation successful!")
            print(f"📊 Synonyms found: {len(result.get('lexeme_synonyms', []))}")
            print(f"📊 Antonyms found: {len(result.get('lexeme_antonyms', []))}")
            
            # Show first few synonyms
            if result.get('lexeme_synonyms'):
                print("\nFirst 3 synonyms:")
                for i, syn in enumerate(result['lexeme_synonyms'][:3], 1):
                    print(f"  {i}. {syn.get('synonym_lemma', 'N/A')} - {syn.get('synonym_translation', 'N/A')}")
    else:
        print(f"❌ Test node '{test_node}' not found in graph")

def main():
    """Main function for testing Croatian AI generation."""
    test_ai_generation()

def generate_translation_and_pos(word, natuknica=None, context=None, model_name=None):
    """
    Generate English translation and infer POS for a Croatian word using AI.
    
    Args:
        word (str): Croatian word to translate and analyze
        natuknica (str): Base form of the word if different from word
        context (str): Additional context about the word
        model_name (str): Gemini model to use
        
    Returns:
        dict: Contains 'translation', 'pos', 'upos', and 'confidence'
    """
    if not HAS_VALID_API_KEY:
        return {"error": "No valid Gemini API key configured"}

    current_model_name = model_name if model_name else DEFAULT_MODEL
    
    # Check cache first
    cache_key = f"croatian_translation_pos_{word}_{current_model_name}"
    cached_result = cache.get(cache_key)
    if cached_result:
        try:
            return json.loads(cached_result)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache for word '{word}'. Regenerating.")

    try:
        # Create comprehensive prompt
        prompt = f"""
        Analyze the Croatian word "{word}" and provide its English translation and part of speech.
        
        Additional context:
        - Croatian word: {word}
        - Base form (natuknica): {natuknica or word}
        - Context: {context or 'No additional context'}
        
        IMPORTANT: Your response MUST be a valid JSON object with the EXACT following structure:
        {{
            "translation": "Primary English translation (single word or short phrase)",
            "pos": "Universal POS tag (NOUN, VERB, ADJ, ADV, ADP, CCONJ, DET, INTJ, NUM, PART, PRON, PROPN, PUNCT, SCONJ, SYM, X)",
            "upos": "Universal POS tag (NOUN, VERB, ADJ, ADV, ADP, CCONJ, DET, INTJ, NUM, PART, PRON, PROPN, PUNCT, SCONJ, SYM, X)",
            "confidence": "Confidence level (high/medium/low)",
            "additional_meanings": ["Secondary meaning 1", "Secondary meaning 2"]
        }}
        
        Guidelines:
        - Provide the most common English translation
        - Use Universal POS tags for both 'pos' and 'upos' fields for consistency
        - Map Croatian grammatical categories to Universal POS tags accurately
        - Consider Croatian morphology and context
        - Confidence should reflect how certain you are about the translation
        
        DO NOT include any text before or after the JSON.
        DO NOT use markdown formatting or code blocks around the JSON.
        ONLY return the raw JSON object itself.
        """

        logger.info(f"Generating translation and POS for Croatian word: {word}")
        
        model = genai.GenerativeModel(current_model_name)
        response = model.generate_content(prompt)
        
        # Create fallback result
        result = {
            "translation": word,  # Fallback to word itself
            "pos": "",
            "upos": "",
            "confidence": "low",
            "additional_meanings": [],
            "raw_response": response.text,
            "_model_used": current_model_name
        }
            
        # Parse response as JSON
        if response.text and response.text.strip():
            try:
                # Clean the response text
                json_text = response.text.strip()
                
                # Extract JSON from code blocks if necessary
                import re
                json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
                if json_block_match:
                    json_text = json_block_match.group(1).strip()
                
                # Try to find JSON object between braces
                if not (json_text.startswith('{') and json_text.endswith('}')):
                    json_object_match = re.search(r'({[\s\S]*?})', json_text)
                    if json_object_match:
                        json_text = json_object_match.group(1).strip()
                
                # Parse the cleaned JSON
                parsed_json = json.loads(json_text)
                result.update(parsed_json)
                
                # Ensure required fields exist
                required_fields = ["translation", "pos", "upos", "confidence"]
                for field in required_fields:
                    if field not in result:
                        if field == "translation":
                            result[field] = word
                        elif field == "confidence":
                            result[field] = "low"
                        else:
                            result[field] = ""
                
                logger.info(f"Successfully generated translation for '{word}': {result['translation']}")
                
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Failed to parse AI response for '{word}': {e}")
                result["generation_note"] = f"Parse error: {str(e)}"
        
        # Cache the result for 7 days
        try:
            cache.set(cache_key, json.dumps(result), 7 * 24 * 60 * 60)
        except Exception as e:
            logger.warning(f"Failed to cache translation for '{word}': {e}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error generating translation for Croatian word '{word}': {e}")
        return {
            "translation": word,
            "pos": "",
            "upos": "",
            "confidence": "low",
            "error": str(e)
        }

if __name__ == "__main__":
    main() 