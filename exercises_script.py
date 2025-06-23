"""
Lexical Exercises Script for Japanese Lexical Graph

This script generates interactive language learning exercises based on
the currently selected node in the Japanese lexical graph. It is designed
to be incorporated into the Node Information pane as a "Lexical Exercises" tab.

The exercises adapt to different learning levels and include translations
and transliterations for beginner levels.
"""

import json
import os
import logging
import pickle
import networkx as nx
from dotenv import load_dotenv
import google.generativeai as genai
from cache_helper import cache
import random

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

# Learning level descriptions
LEVEL_DESCRIPTIONS = {
    1: "Beginner 1 - Basic vocabulary and simple sentence structures with full romaji support",
    2: "Beginner 2 - Elementary vocabulary with hiragana focus and partial romaji",
    3: "Intermediate 1 - Common everyday vocabulary with basic kanji, minimal romaji",
    4: "Intermediate 2 - Expanded vocabulary and more complex sentence patterns",
    5: "Advanced 1 - Sophisticated vocabulary and natural expressions",
    6: "Advanced 2 - Native-like vocabulary and cultural nuances"
}

def is_available():
    """Check if Gemini API is available with valid API key."""
    return HAS_VALID_API_KEY

def get_graph():
    """Get the shared NetworkX graph from the main app."""
    try:
        # Import the graph from app.py to ensure consistency
        from app import G
        logger.info(f"Using shared graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        return G
    except ImportError:
        logger.warning("Could not import graph from app.py, falling back to loading from pickle")
        # Fallback to loading from pickle file
        try:
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
            logger.info(f"Loaded graph from pickle with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
            return G
        except Exception as e:
            logger.error(f"Error loading graph from pickle: {e}")
            return nx.Graph()  # Return empty graph on error

def get_node_context(node_id, max_neighbors=7):
    """Get context about a node and its neighbors from the graph."""
    G = get_graph()
    
    if node_id not in G.nodes:
        # Instead of returning an error, provide a fallback context
        # This allows exercises to be generated even for nodes not in the graph
        logger.warning(f"Node '{node_id}' not found in graph, using fallback context")
        return {
            "node": {
                "id": node_id,
                "hiragana": "",
                "romaji": "",
                "translation": "",
                "pos": ""
            },
            "neighbors": [],
            "fallback": True  # Flag to indicate this is fallback data
        }
    
    # Get node data
    node_data = dict(G.nodes[node_id])
    
    # Get neighbor data
    neighbors = []
    for neighbor in G.neighbors(node_id):
        neighbor_data = dict(G.nodes[neighbor])
        edge_data = G.get_edge_data(node_id, neighbor)
        
        # Determine relationship type (synonym, antonym, etc.)
        relationship_type = "related"
        relationship_strength = 0.5
        
        if edge_data:
            # Look through all multiedge keys
            for key, data in edge_data.items():
                if 'synonym_strength' in data:
                    relationship_type = "synonym"
                    relationship_strength = float(data['synonym_strength'])
                    break
                elif 'antonym_strength' in data:
                    relationship_type = "antonym"
                    relationship_strength = float(data['antonym_strength'])
                    break
        
        neighbors.append({
            "id": neighbor,
            "hiragana": neighbor_data.get('hiragana', ''),
            "romaji": neighbor_data.get('romaji', ''),
            "translation": neighbor_data.get('translation', ''),
            "pos": neighbor_data.get('pos', ''),
            "relationship": relationship_type,
            "strength": relationship_strength
        })
    
    # Sort by relationship strength and limit to max_neighbors
    neighbors.sort(key=lambda x: x['strength'], reverse=True)
    neighbors = neighbors[:max_neighbors]
    
    return {
        "node": {
            "id": node_id,
            "hiragana": node_data.get('hiragana', ''),
            "romaji": node_data.get('romaji', ''),
            "translation": node_data.get('translation', ''),
            "pos": node_data.get('pos', '')
        },
        "neighbors": neighbors
    }

def generate_exercise(node_id, level=1, session_history=None, mode="exercise", model_name=DEFAULT_MODEL):
    """
    Generate an interactive language learning exercise for the given node.
    
    Args:
        node_id (str): The ID of the node (Japanese word/kanji)
        level (int): Learning level from 1-6
        session_history (list): Previous conversation history in this session
        mode (str): Exercise mode - "exercise" for structured learning, "conversation" for free-form practice
        model_name (str): Gemini model to use
        
    Returns:
        dict: Generated exercise content
    """
    if not HAS_VALID_API_KEY:
        return {
            "error": "No valid Gemini API key configured",
            "content": "Unable to generate exercises: API key not configured."
        }
    
    # Check cache first (only if no session history)
    if not session_history:
        cache_key = f"{mode}_{node_id}_{level}_{model_name}"
        cached_result = cache.get(cache_key)
        if cached_result:
            try:
                return json.loads(cached_result)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in cache for {mode} '{node_id}'. Regenerating content.")
    
    # Get node context from the graph
    context = get_node_context(node_id)
    
    # Check if we're using fallback data
    is_fallback = context.get("fallback", False)
    if is_fallback:
        logger.info(f"Using fallback context for node '{node_id}' - exercise generation will proceed with limited context")
    
    # Create a more human-friendly level description
    level_description = LEVEL_DESCRIPTIONS.get(level, "Intermediate level")
    
    # Prepare the prompt based on the level
    # The prompt will be different depending on whether this is the first message or a continuation
    if not session_history:
        # Initial prompt
        if mode == "exercise":
            # Structured exercise mode
            prompt = f"""
            You are a Japanese language teacher who specializes in interactive, engaging learning experiences. Create an interactive exercise for the Japanese word "{node_id}" ({context['node'].get('hiragana', '')}) meaning "{context['node'].get('translation', '')}".

            CURRENT LEARNING LEVEL: {level} - {level_description}

            CREATE AN INTERACTIVE CHATBOT EXERCISE that:
            1. Introduces the word "{node_id}" in a natural, conversational way
            2. Creates an engaging scenario or conversation that uses this word
            3. Includes at least 2-3 related words from the following list: {', '.join([n['id'] for n in context['neighbors']])}
            4. Asks the learner questions that encourage them to practice using the word
            5. Provides helpful corrections when needed
            
            SPECIFIC REQUIREMENTS FOR LEVEL {level}:
            """
            
            # Add level-specific requirements
            if level <= 2:  # Beginner levels
                prompt += f"""
                - Include romaji (transliteration) for ALL Japanese text
                - Use very simple sentence structures
                - Explain each new word with a clear definition
                - Use mostly hiragana with minimal kanji
                - Include English translations for all sentences
                """
            elif level <= 4:  # Intermediate levels
                prompt += f"""
                - Include romaji only for difficult or new words
                - Use natural, everyday conversational Japanese
                - Include some cultural context where appropriate
                - Gradually introduce more complex sentence patterns
                - Provide translations only when necessary
                """
            else:  # Advanced levels
                prompt += f"""
                - Use natural, native-like Japanese with appropriate kanji
                - Include nuanced cultural references and context
                - Challenge the learner with idiomatic expressions
                - Focus on natural production and communication
                - Limit translations to only the most complex concepts
                """
                
            prompt += f"""
            FORMAT YOUR RESPONSE:
            1. Start with a brief introduction of yourself as a Japanese language tutor
            2. Create a natural conversational scenario using "{node_id}"
            3. Format any teaching elements clearly with:
               - Japanese text (kanji/hiragana)
               - Romaji transliteration (for levels 1-4 only)
               - English translations (as appropriate for the level)
            4. Ask an engaging question at the end to prompt a response
            
            Begin your Japanese tutoring session now!
            """
        else:
            # Conversation mode - more free-form practice
            prompt = f"""
            You are a native Japanese speaker chatting with a language learner. Start a natural conversation that incorporates the Japanese word "{node_id}" ({context['node'].get('hiragana', '')}) meaning "{context['node'].get('translation', '')}".

            CURRENT LEARNING LEVEL: {level} - {level_description}

            CREATE A NATURAL CONVERSATION that:
            1. Feels authentic and casual, as between friends or acquaintances
            2. Introduces "{node_id}" in a natural, conversational context
            3. Incorporates at least one or two related words from: {', '.join([n['id'] for n in context['neighbors'][:5]])}
            4. Asks open-ended questions to encourage meaningful responses
            5. Is culturally appropriate and contextually realistic
            
            SPECIFIC REQUIREMENTS FOR THE CONVERSATION:
            """
            
            # Add level-specific requirements
            if level <= 2:  # Beginner levels
                prompt += f"""
                - Include romaji (transliteration) for ALL Japanese text
                - Use simple, everyday conversational patterns
                - Include English translations for all sentences
                - Focus on common situations and practical usage
                """
            elif level <= 4:  # Intermediate levels
                prompt += f"""
                - Include romaji only for difficult words
                - Use natural expressions and some colloquialisms
                - Provide translations only for challenging concepts
                - Introduce some culturally specific elements
                """
            else:  # Advanced levels
                prompt += f"""
                - Use authentic, native-like Japanese with natural kanji usage
                - Include colloquialisms, slang, or regional expressions when appropriate
                - Limit translations to only the most specialized terms
                - Create a rich, nuanced conversation that could happen between native speakers
                """
                
            prompt += f"""
            FORMAT YOUR RESPONSE:
            1. Start with a casual greeting appropriate to the context
            2. Write a natural opening that introduces yourself and the conversational context
            3. Include:
               - Japanese text (with kanji appropriate to the level)
               - Romaji transliteration (as appropriate for the level)
               - Translations (as appropriate for the level)
            4. End with an open-ended question to encourage conversation
            
            Begin your conversation now!
            """
    else:
        # This is a continuation of a conversation
        # Format the history for the model
        history_text = "\n".join([
            f"User: {msg['user']}\nTutor: {msg['tutor']}" 
            for msg in session_history
        ])
        
        # Create continuation prompt based on mode
        if mode == "exercise":
            # Structured exercise continuation
            prompt = f"""
            Continue this Japanese language learning conversation about the word "{node_id}". You are a helpful, encouraging Japanese tutor.

            CURRENT LEARNING LEVEL: {level} - {level_description}

            CONVERSATION HISTORY:
            {history_text}

            USER'S LAST MESSAGE: {session_history[-1]['user']}

            GUIDELINES FOR YOUR RESPONSE:
            1. Respond directly to the user's message in a natural, conversational way
            2. Continue to incorporate the target word "{node_id}" and related vocabulary
            3. Provide gentle corrections if the user makes mistakes
            4. Keep maintaining the appropriate level of language complexity for Level {level}
            """
            
            # Add level-specific requirements
            if level <= 2:  # Beginner levels
                prompt += f"""
                5. Continue to include romaji (transliteration) for ALL Japanese text
                6. Provide English translations for all sentences
                7. Keep your language simple and encouraging
                """
            elif level <= 4:  # Intermediate levels
                prompt += f"""
                5. Include romaji only for difficult or new words
                6. Provide translations only when necessary
                7. Encourage more complex sentence formation
                """
            else:  # Advanced levels
                prompt += f"""
                5. Maintain natural, native-like Japanese with appropriate kanji
                6. Challenge the learner with nuanced expressions
                7. Focus on fluency and natural communication
                """
        else:
            # Conversation mode continuation
            prompt = f"""
            Continue this natural Japanese conversation that includes the word "{node_id}". You are a native Japanese speaker chatting with a language learner.

            CURRENT LEARNING LEVEL: {level} - {level_description}

            CONVERSATION HISTORY:
            {history_text}

            USER'S LAST MESSAGE: {session_history[-1]['user']}

            GUIDELINES FOR YOUR RESPONSE:
            1. Respond directly and naturally to the user's message
            2. Keep the conversation flowing in an authentic way
            3. Continue using "{node_id}" or related vocabulary naturally when appropriate
            4. Adjust to the user's language level while gently challenging them
            """
            
            # Add level-specific requirements
            if level <= 2:  # Beginner levels
                prompt += f"""
                5. Continue to include romaji for all Japanese text
                6. Provide translations for all sentences
                7. Keep your language simple and natural
                """
            elif level <= 4:  # Intermediate levels
                prompt += f"""
                5. Include romaji only for difficult words
                6. Translate only when necessary for comprehension
                7. Use more natural expressions and some colloquialisms
                """
            else:  # Advanced levels
                prompt += f"""
                5. Use fully authentic, native-like Japanese
                6. Include natural expressions, idioms, or cultural references
                7. Respond as you would to another native speaker, with minimal accommodations
                """
        
        prompt += f"""
        Format your response with appropriate Japanese, romaji (as needed for the level), and translations (as needed for the level).
        
        Your response:
        """

    try:
        # Generate content with Gemini
        genai_model = genai.GenerativeModel(model_name)
        response = genai_model.generate_content(prompt)
        
        # Extract and format the response
        content = response.text
        
        # Cache the result (only for initial messages)
        if not session_history:
            cache_key = f"{mode}_{node_id}_{level}_{model_name}"
            cache.set(cache_key, json.dumps({
                "node_id": node_id,
                "level": level,
                "mode": mode,
                "content": content,
                "model": model_name
            }), ex=86400)  # Cache for 24 hours
        
        return {
            "node_id": node_id,
            "level": level,
            "mode": mode,
            "content": content,
            "model": model_name
        }
    
    except Exception as e:
        logger.error(f"Error generating {mode} for '{node_id}': {e}")
        return {
            "error": str(e),
            "content": f"An error occurred while generating the {mode}: {str(e)}"
        } 