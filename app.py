from flask import Flask, render_template, jsonify, request, url_for
import networkx as nx
import pickle
import ssl
import os
import logging
from dotenv import load_dotenv
from wikidata_helper import get_wikidata_info
from cache_helper import cache
import gemini_helper
import json
import time
import math
import numpy as np
from collections import Counter, defaultdict
# Import our new AI generation script
import ai_generation_single
# Import our new lexical exercises script
import exercises_script
# Import readability helper
import readability_helper
# Import uuid for unique file prefixes and our new TTS helper
import uuid
import tts_helper
# Import Croatian helper functions
import croatian_helper
import croatian_ai_generation
import croatian_exercises
import cando_helper


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Disable SSL certificate verification
ssl._create_default_https_context = ssl._create_unverified_context

# Load the NetworkX graph from pickle file
try:
    # Updated path to pickle file in graph_models folder
    filename = os.path.join('graph_models', 'G_japanese_2025.pickle')
    with open(filename, 'rb') as f:
        G = pickle.load(f)

    # Clean up any NaN nodes which can cause issues
    nan_nodes = [node for node in G.nodes() if isinstance(node, float) and math.isnan(node)]
    if nan_nodes:
        logger.warning(f"Found {len(nan_nodes)} NaN nodes in the graph. Removing them.")
        G.remove_nodes_from(nan_nodes)

    # Print basic information about the graph
    logger.info(f"Number of nodes: {G.number_of_nodes()}")
    logger.info(f"Number of edges: {G.number_of_edges()}")

    # ------------------------------------------------------------------
    # Ensure each edge has a numeric 'weight' attribute for consistency
    # ------------------------------------------------------------------
    # Reason: Several parts of the application (e.g. gemini_helper.get_neighbor_info)
    #   expect a 'weight' attribute on edges to rank or filter relationships. The
    #   original graph pickle only stores a 'synonym_strength' attribute. Here we
    #   propagate that value (if present) to a unified 'weight' key. If neither
    #   is available we default to 1 so existing behaviour is preserved.

    for u, v, k, data in G.edges(data=True, keys=True):
        # Skip if weight already present
        if 'weight' in data:
            continue

        # Prefer explicit numeric synonym_strength when available
        strength = data.get('synonym_strength')
        if isinstance(strength, (int, float)) and not math.isnan(strength):
            data['weight'] = float(strength)
        else:
            # Fallback to 1 to keep edge usable
            data['weight'] = 1.0

    logger.info("Edge 'weight' attribute normalisation complete.")

except Exception as e:
    logger.error(f"Error loading graph: {e}")
    G = nx.Graph()  # Create empty graph if file can't be loaded

# Load Croatian graph
try:
    G_croatian = croatian_helper.load_croatian_graph()
    if G_croatian:
        logger.info(f"Croatian graph loaded: {G_croatian.number_of_nodes()} nodes, {G_croatian.number_of_edges()} edges")
        
        # ------------------------------------------------------------------
        # Ensure Croatian edges have a numeric 'weight' attribute for consistency
        # ------------------------------------------------------------------
        # Reason: Frontend expects a unified 'weight' field for displaying neighbor strengths.
        # Croatian edges store weights in nested structures like synonym->synonym_strength
        # or antonym->antonym_strength. Extract and normalize these to a top-level weight field.
        
        for u, v, data in G_croatian.edges(data=True):
            # Skip if weight already present
            if 'weight' in data:
                continue
            
            # Extract weight from nested synonym/antonym structures
            weight = None
            
            # Check for synonym strength
            if 'synonym' in data and isinstance(data['synonym'], dict):
                weight = data['synonym'].get('synonym_strength')
            
            # Check for antonym strength
            elif 'antonym' in data and isinstance(data['antonym'], dict):
                weight = data['antonym'].get('antonym_strength')
            
            # Use extracted weight if valid, otherwise default to 1.0
            if isinstance(weight, (int, float)) and not math.isnan(weight):
                data['weight'] = float(weight)
            else:
                data['weight'] = 1.0
        
        logger.info("Croatian edge 'weight' attribute normalisation complete.")
    else:
        logger.warning("Croatian graph not found, creating empty graph")
        G_croatian = nx.Graph()
except Exception as e:
    logger.error(f"Error loading Croatian graph: {e}")
    G_croatian = nx.Graph()

def get_graph():
    """Return the global graph object."""
    return G

def get_graph_for_node(node_id):
    """
    Determine which graph a node belongs to and return (graph, language).
    
    Args:
        node_id (str): Node ID to check
        
    Returns:
        tuple: (graph, language) where language is 'japanese' or 'croatian'
    """
    # Check Croatian graph first (lempos format like "abeceda-NOUN")
    if G_croatian and node_id in G_croatian.nodes():
        return G_croatian, 'croatian'
    
    # Check Japanese graph 
    if G and node_id in G.nodes():
        return G, 'japanese'
    
    # Default to Japanese graph if node not found
    return G, 'japanese'

def detect_language_from_search(term, attribute):
    """
    Detect language from search term and attribute.
    
    Args:
        term (str): Search term
        attribute (str): Search attribute
        
    Returns:
        str: 'japanese' or 'croatian'
    """
    # Check if term contains Croatian-specific patterns
    if attribute in ['natuknica', 'natuknica_norm', 'UPOS']:
        return 'croatian'
    
    # Check if term follows Croatian lempos pattern (word-POS)
    if '-' in term and any(pos in term.upper() for pos in ['NOUN', 'VERB', 'ADJ', 'ADV']):
        return 'croatian'
    
    # Check if term exists in Croatian graph
    if G_croatian and term in G_croatian.nodes():
        return 'croatian'
    
    # Check if term exists in Croatian node attributes
    if G_croatian:
        for node_id, attrs in G_croatian.nodes(data=True):
            if (term.lower() in attrs.get('natuknica', '').lower() or
                term.lower() in attrs.get('natuknica_norm', '').lower() or
                term.lower() in attrs.get('translation', '').lower()):
                return 'croatian'
    
    # Default to Japanese
    return 'japanese'

def find_nodes_multilingual(term, attribute, exact=False, language=None):
    """
    Find nodes in both Japanese and Croatian graphs.
    
    Args:
        term (str): Search term
        attribute (str): Search attribute
        exact (bool): Whether to do exact matching
        language (str): Force specific language ('japanese' or 'croatian')
        
    Returns:
        tuple: (nodes, graph, language)
    """
    if not term:
        return [], G, 'japanese'
    
    # Auto-detect language if not specified, but respect explicit language choice
    if language is None:
        language = detect_language_from_search(term, attribute)
    elif language not in ['japanese', 'croatian']:
        # Handle any invalid language values by defaulting to Japanese
        logger.warning(f"Invalid language parameter '{language}', defaulting to Japanese")
        language = 'japanese'
    
    if language == 'croatian':
        # Search Croatian graph with attribute-specific logic
        try:
            nodes = find_croatian_nodes_by_attribute(G_croatian, term, attribute, exact)
            return nodes, G_croatian, 'croatian'
        except Exception as e:
            logger.error(f"Error searching Croatian nodes: {e}")
            return [], G_croatian, 'croatian'
    
    else:
        # Search Japanese graph (existing logic)
        nodes = find_nodes(G, term, attribute, exact)
        return nodes, G, 'japanese'

def find_croatian_nodes_by_attribute(G, term, attribute, exact=False):
    """
    Find Croatian nodes by specific attribute.
    
    Args:
        G (nx.Graph): Croatian lexical graph
        term (str): Search term
        attribute (str): Search attribute
        exact (bool): Whether to do exact matching
        
    Returns:
        List[str]: List of matching node IDs
    """
    if not G or not term:
        return []
    
    import unicodedata
    
    def normalize_text(text):
        """Normalize text by removing accents and converting to lowercase."""
        if not text:
            return ""
        # Normalize to NFD (decomposed form), then remove combining characters
        normalized = unicodedata.normalize('NFD', str(text))
        ascii_text = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        return ascii_text.lower()
    
    matching_nodes = []
    term_normalized = normalize_text(term)
    
    # Map frontend attribute names to backend attribute names
    attribute_mapping = {
        'natuknica': 'natuknica',
        'normalized': 'natuknica_norm',
        'definition': 'tekst',
        'pos': 'pos',
        'upos': 'UPOS',
        'translation': 'translation'
    }
    
    # Use mapped attribute name
    search_attribute = attribute_mapping.get(attribute.lower(), attribute)
    
    for node_id, attrs in G.nodes(data=True):
        # Get the value of the specified attribute
        if search_attribute in attrs:
            attr_value = normalize_text(attrs[search_attribute])
            
            if exact:
                if term_normalized == attr_value:
                    matching_nodes.append(node_id)
            else:
                if term_normalized in attr_value:
                    matching_nodes.append(node_id)
        
        # Also check if searching by node ID (lempos format)
        if search_attribute == 'id' or attribute.lower() == 'id':
            node_id_normalized = normalize_text(node_id)
            if exact:
                if term_normalized == node_id_normalized:
                    matching_nodes.append(node_id)
            else:
                if term_normalized in node_id_normalized:
                    matching_nodes.append(node_id)
    
    # If no results found with normalization, try exact case-sensitive search
    if not matching_nodes and not exact:
        term_lower = term.lower()
        for node_id, attrs in G.nodes(data=True):
            if search_attribute in attrs:
                attr_value = str(attrs[search_attribute]).lower()
                if term_lower in attr_value:
                    matching_nodes.append(node_id)
            
            # Also check node ID
            if search_attribute == 'id' or attribute.lower() == 'id':
                if term_lower in node_id.lower():
                    matching_nodes.append(node_id)
    
    return matching_nodes

@app.route('/')
def index():
    return render_template('index.html')

def find_nodes(G, term, attribute, exact=False):
    if not term:
        return []
    term = str(term).lower()
    if attribute == 'kanji':
        return [node for node in G.nodes() 
                if (exact and term == str(node).lower()) or 
                   (not exact and term in str(node).lower())]
    else:
        return [node for node, data in G.nodes(data=True)
                if attribute in data and (
                    (exact and term == str(data[attribute]).lower()) or
                    (not exact and term in str(data[attribute]).lower())
                )]

def get_subgraph(G, source_nodes, depth=1):
    subgraph_nodes = set(source_nodes)
    for _ in range(depth):
        neighbors = set()
        for node in subgraph_nodes:
            neighbors.update(G.neighbors(node))
        subgraph_nodes.update(neighbors)
    return G.subgraph(subgraph_nodes)

@app.route('/graph-data')
def graph_data():
    try:
        term = request.args.get('term', '')
        attribute = request.args.get('attribute', 'kanji')
        depth = int(request.args.get('depth', '1'))
        exact = request.args.get('exact', 'false').lower() == 'true'
        language = request.args.get('language', None)  # Allow explicit language selection
        
        logger.info(f"Graph data request: term='{term}', attribute='{attribute}', language='{language}'")
        
        if not term:
            return jsonify({'error': 'No search term provided'}), 400
        
        source_nodes, graph, detected_language = find_nodes_multilingual(term, attribute, exact, language)
        
        if not source_nodes:
            logger.info(f"No nodes found for term '{term}' in {detected_language} language")
            return jsonify({
                'nodes': [], 
                'links': [], 
                'language': detected_language,
                'source_nodes': [],
                'message': f'No nodes found for "{term}" in {detected_language} language'
            })
        
        subgraph = get_subgraph(graph, source_nodes, depth=depth)
    except Exception as e:
        logger.error(f"Error in graph_data endpoint: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

    nodes = []
    for node, data in subgraph.nodes(data=True):
        node_data = {'id': str(node)}
        node_data.update({k: str(v) if v is not None else None for k, v in data.items()})
        # Add language information
        node_data['language'] = detected_language
        nodes.append(node_data)

    links = []
    # Check if this is a MultiGraph before using keys parameter
    if hasattr(subgraph, 'is_multigraph') and subgraph.is_multigraph():
        for u, v, key, data in subgraph.edges(data=True, keys=True):
            link = {'source': str(u), 'target': str(v)}
            
            # Flatten nested edge attributes for MultiGraph
            for k, v_data in data.items():
                if isinstance(v_data, dict) and k in ['synonym', 'antonym']:
                    # Flatten the nested structure
                    for nested_k, nested_v in v_data.items():
                        if nested_v is not None:
                            link[nested_k] = nested_v
                else:
                    # Regular attribute - preserve numeric types for weight fields
                    if v_data is not None:
                        # Keep numeric types for weight-related fields
                        if k in ['weight', 'strength', 'synonym_strength', 'antonym_strength'] and isinstance(v_data, (int, float)):
                            link[k] = float(v_data)
                        else:
                            link[k] = str(v_data)
            
            # Ensure weight field is set for frontend consistency
            if 'weight' not in link:
                # Extract weight from flattened synonym/antonym strength
                if 'synonym_strength' in link:
                    link['weight'] = float(link['synonym_strength']) if isinstance(link['synonym_strength'], (str, int, float)) else 1.0
                elif 'antonym_strength' in link:
                    link['weight'] = float(link['antonym_strength']) if isinstance(link['antonym_strength'], (str, int, float)) else 1.0
                else:
                    link['weight'] = 1.0
            
            # Determine relationship type for easier front-end rendering
            # We inspect the multigraph edge key and known attribute patterns.
            # Reason: Users want to distinguish synonyms from antonyms in the neighbour list.
            relation_type = 'connected'
            try:
                if key == 'synonym' or 'synonym_strength' in link or 'synonym' in data:
                    relation_type = 'synonym'
                elif key == 'antonym' or 'antonym_strength' in link or 'antonym' in data:
                    relation_type = 'antonym'
            except Exception:
                # Fallback to default if any issue arises
                relation_type = 'connected'
            link['relationship'] = relation_type
            link['id'] = f"{u}-{v}-{key}"
            links.append(link)
    else:
        # For regular graphs, iterate without keys
        for u, v, data in subgraph.edges(data=True):
            link = {'source': str(u), 'target': str(v)}
            
            # Flatten nested edge attributes
            for k, v_data in data.items():
                if isinstance(v_data, dict) and k in ['synonym', 'antonym']:
                    # Flatten the nested structure
                    for nested_k, nested_v in v_data.items():
                        if nested_v is not None:
                            link[nested_k] = nested_v
                else:
                    # Regular attribute - preserve numeric types for weight fields
                    if v_data is not None:
                        # Keep numeric types for weight-related fields
                        if k in ['weight', 'strength', 'synonym_strength', 'antonym_strength'] and isinstance(v_data, (int, float)):
                            link[k] = float(v_data)
                        else:
                            link[k] = str(v_data)
            
            # Ensure weight field is set for frontend consistency
            if 'weight' not in link:
                # Extract weight from flattened synonym/antonym strength
                if 'synonym_strength' in link:
                    link['weight'] = float(link['synonym_strength']) if isinstance(link['synonym_strength'], (str, int, float)) else 1.0
                elif 'antonym_strength' in link:
                    link['weight'] = float(link['antonym_strength']) if isinstance(link['antonym_strength'], (str, int, float)) else 1.0
                else:
                    link['weight'] = 1.0
            
            # Determine relationship type
            relation_type = 'connected'
            try:
                if 'synonym_strength' in link or 'synonym' in data:
                    relation_type = 'synonym'
                elif 'antonym_strength' in link or 'antonym' in data:
                    relation_type = 'antonym'
            except Exception:
                relation_type = 'connected'
            link['relationship'] = relation_type
            link['id'] = f"{u}-{v}"
            links.append(link)

    logger.info(f"Returning {len(nodes)} nodes and {len(links)} links for {detected_language} language")
    return jsonify({
        'nodes': nodes, 
        'links': links, 
        'language': detected_language,
        'source_nodes': source_nodes
    })

@app.route('/search-cando')
def search_cando():
    """
    Endpoint to search for Can-do statements.
    """
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        results = cando_helper.search_cando_nodes(query)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error searching Can-do nodes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/cando-graph-data')
def cando_graph_data():
    """
    Endpoint to get Can-do graph data for visualization.
    """
    node_id = request.args.get('node_id')
    
    try:
        graph_data = cando_helper.get_cando_graph_data(node_id)
        return jsonify(graph_data)
    except Exception as e:
        logger.error(f"Error getting Can-do graph data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/wikidata-info')
def wikidata_info():
    """Endpoint to retrieve information about a term from Wikidata."""
    term = request.args.get('term', '')
    lang = request.args.get('language', 'ja')
    
    if not term:
        return jsonify({'error': 'No term provided'}), 400
    
    # Check cache first
    cache_key = f"wikidata:{term}:{lang}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for term '{term}'")
        return jsonify(cached_result)
    
    try:
        logger.info(f"Fetching Wikidata information for term '{term}'")
        wikidata_data = get_wikidata_info(term, lang)
        
        # Cache the result for 1 day
        cache.set(cache_key, wikidata_data, ex=86400)
        
        return jsonify(wikidata_data)
    except Exception as e:
        logger.error(f"Error retrieving Wikidata information: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/wikidata-related')
def wikidata_related():
    """Endpoint to retrieve related terms from Wikidata."""
    term = request.args.get('term', '')
    lang = request.args.get('language', 'ja')
    
    if not term:
        return jsonify({'error': 'No term provided'}), 400
    
    # Check cache first
    cache_key = f"wikidata_related:{term}:{lang}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for related terms of '{term}'")
        return jsonify(cached_result)
    
    try:
        # First get the basic Wikidata information
        wikidata_data = get_wikidata_info(term, lang)
        
        # Extract related terms from different relationship types
        related_terms = []
        
        for item_url, item_data in wikidata_data.items():
            # Add synonyms
            if "Synonyms" in item_data and item_data["Synonyms"]:
                for synonym in item_data["Synonyms"]:
                    related_terms.append({
                        "term": synonym,
                        "relationship": "synonym",
                        "source": "Wikidata"
                    })
            
            # Add instances and subclasses
            for relation_type in ["Instance of", "Subclass of", "Has part", "Part of"]:
                if relation_type in item_data and item_data[relation_type]:
                    for related in item_data[relation_type]:
                        related_terms.append({
                            "term": related,
                            "relationship": relation_type.lower(),
                            "source": "Wikidata"
                        })
        
        result = {
            "term": term,
            "related_terms": related_terms
        }
        
        # Cache the result for 1 day
        cache.set(cache_key, result, ex=86400)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error retrieving related terms: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/node-details')
def node_details():
    """Unified endpoint for all node details from multiple sources."""
    node_id = request.args.get('id', '')
    include = request.args.get('include', 'basic,wikidata').split(',')
    
    if not node_id:
        return jsonify({'error': 'No node ID provided'}), 400
    
    # Determine which graph this node belongs to
    graph, language = get_graph_for_node(node_id)
    
    # Check cache
    cache_key = f"node_details:{node_id}:{','.join(include)}:{language}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify(cached_result)
    
    # Initialize response object
    result = {'id': node_id, 'language': language}
    
    # Get node data from the appropriate graph
    if 'basic' in include and node_id in graph:
        if language == 'croatian':
            # Use Croatian-specific node info
            node_info = croatian_helper.get_croatian_node_info(graph, node_id)
            if node_info:
                result['basic'] = node_info
                # Add neighbors information
                neighbors_info = croatian_helper.get_croatian_neighbors_info(graph, node_id)
                result['basic']['neighbors'] = neighbors_info
        else:
            # Use Japanese node info (existing logic)
            result['basic'] = {
                **{k: str(v) if v is not None else None for k, v in graph.nodes[node_id].items()},
                'neighbors': [
                    {'id': str(neighbor), 'relationship': data.get('relationship', 'unknown')}
                    for neighbor, data in graph[node_id].items()
                ]
            }
    
    # Get Wikidata information if requested
    if 'wikidata' in include:
        try:
            # For Croatian nodes, try to get Wikidata info using natuknica
            if language == 'croatian' and node_id in graph:
                natuknica = graph.nodes[node_id].get('natuknica', node_id)
                wikidata_info = get_wikidata_info(natuknica, 'hr')  # Croatian language
            else:
                wikidata_info = get_wikidata_info(node_id)
            result['wikidata'] = wikidata_info
        except Exception as e:
            logger.error(f"Error fetching Wikidata info: {str(e)}")
            result['wikidata'] = {'error': str(e)}
    
    # Cache the result (expire after 1 hour)
    cache.set(cache_key, result, ex=3600)
    
    return jsonify(result)

@app.route('/gemini-explanation', methods=['GET'])
def gemini_explanation():
    term = request.args.get('term', '')
    model_name = request.args.get('model_name', None)
    if not term:
        return jsonify({"error": "No term provided"}), 400
    
    # Check if Gemini API is available
    if not gemini_helper.is_available():
        return jsonify({"error": "Gemini API is not available. Please check your API key."}), 503
    
    # Check cache first
    cache_key = f"gemini_endpoint_explanation_{term}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify(json.loads(cached_result))
    
    try:
        # Get node context if term is a node in our graph
        context = None
        matching_nodes = find_nodes(G, term, 'kanji')
        if matching_nodes:
            node_id = matching_nodes[0]
            node_attrs = dict(G.nodes[node_id])
            
            # Get top 5 neighbors
            neighbors = []
            for neighbor in G.neighbors(node_id):
                neighbor_attrs = dict(G.nodes[neighbor])
                neighbors.append(str(neighbor))
                if len(neighbors) >= 5:
                    break
            
            context = {
                "pos": node_attrs.get('POS', ''),
                "english": node_attrs.get('translation', ''),
                "related": neighbors
            }
        
        # Generate explanation
        explanation = gemini_helper.generate_explanation(term, context=context, model_name=model_name)
        
        response = {
            "term": term,
            "explanation": explanation
        }
        
        # Cache for 3 days
        cache.set(cache_key, json.dumps(response), 3 * 24 * 60 * 60)
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error generating Gemini explanation for {term}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/gemini-analyze', methods=['GET'])
def gemini_analyze():
    term1 = request.args.get('term1', '')
    term2 = request.args.get('term2', '')
    model_name = request.args.get('model_name', None)
    
    if not term1 or not term2:
        return jsonify({"error": "Both term1 and term2 must be provided"}), 400
    
    # Check if Gemini API is available
    if not gemini_helper.is_available():
        return jsonify({"error": "Gemini API is not available. Please check your API key."}), 503
    
    # Check cache first
    cache_key = f"gemini_endpoint_analyze_{term1}_{term2}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify(json.loads(cached_result))
    
    try:
        # Analyze relationship
        analysis = gemini_helper.analyze_relationship(term1, term2, model_name=model_name)
        
        response = {
            "term1": term1,
            "term2": term2,
            "analysis": analysis
        }
        
        # Cache for 3 days
        cache.set(cache_key, json.dumps(response), 3 * 24 * 60 * 60)
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error analyzing relationship with Gemini for {term1} and {term2}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/ai-generate-relations', methods=['GET'])
def ai_generate_relations():
    """
    Endpoint to generate AI-powered lexical relations for a node.
    This allows users to generate new synonyms and antonyms for a word,
    adding these to the graph database.
    Supports both Japanese and Croatian nodes.
    """
    node_id = request.args.get('id', '')
    if not node_id:
        return jsonify({"error": "No node ID provided"}), 400
    
    try:
        # Determine which graph this node belongs to
        graph, language = get_graph_for_node(node_id)
        logger.info(f"Generating AI relations for {language} node: {node_id}")
        
        # Check if AI generation is available for the detected language
        if language == 'croatian':
            if not croatian_ai_generation.is_available():
                return jsonify({
                    "status": "error",
                    "message": "Croatian AI Generation is not available. Please check your API key configuration."
                }), 503
            
            # Generate Croatian relations
            generated_data = croatian_ai_generation.generate_croatian_lexical_relations(node_id, G=graph)
            
            # Add relations to Croatian graph
            changes = croatian_ai_generation.add_generated_relations_to_croatian_graph(node_id, generated_data, G=graph)
            
            # Format result to match expected structure
            result = {
                "status": "success" if "error" not in changes else "partial_success",
                "message": f"Generated {changes.get('synonyms_added', 0)} synonyms and {changes.get('antonyms_added', 0)} antonyms for {node_id}",
                "generated_data": generated_data,
                "changes": changes
            }
        else:
            # Japanese AI generation (existing logic)
            if not ai_generation_single.is_available():
                return jsonify({
                    "status": "error",
                    "message": "AI Generation is not available. Please check your API key configuration."
                }), 503
            
            # Generate relations for the node
            result = ai_generation_single.generate_node_relations(node_id, graph)
        
        logger.info(f"AI generation result status: {result.get('status')}")

        # If the generation was successful, include the updated graph data
        if result.get("status") in ["success", "partial_success"]:
            try:
                # Get the depth parameter or default to 1
                depth = int(request.args.get('depth', '1'))
                logger.info(f"Fetching subgraph with depth {depth} for {node_id}")
                
                # Include any newly added nodes in the source nodes
                source_nodes = [node_id]
                if "changes" in result and "updated_nodes" in result["changes"]:
                    source_nodes.extend(result["changes"]["updated_nodes"])
                    logger.info(f"Including updated nodes in subgraph: {result['changes']['updated_nodes']}")
                
                # Get the updated subgraph data - with additional error handling
                try:
                    # Get the valid nodes that exist in the appropriate graph
                    valid_source_nodes = [node for node in source_nodes if node in graph.nodes]
                    if len(valid_source_nodes) < len(source_nodes):
                        missing_nodes = [node for node in source_nodes if node not in graph.nodes]
                        logger.warning(f"Some nodes weren't found in the graph and will be skipped: {missing_nodes}")
                    
                    # Continue with valid nodes
                    subgraph = get_subgraph(graph, valid_source_nodes, depth=depth)
                    logger.info(f"Got subgraph with {subgraph.number_of_nodes()} nodes and {subgraph.number_of_edges()} edges")
                    
                    # Format nodes and links
                    nodes = []
                    for node, data in subgraph.nodes(data=True):
                        node_data = {'id': str(node)}
                        node_data.update({k: str(v) if v is not None else None for k, v in data.items()})
                        nodes.append(node_data)
                    
                    links = []
                    # Check if this is a MultiGraph before using keys parameter
                    if hasattr(subgraph, 'is_multigraph') and subgraph.is_multigraph():
                        for u, v, key, data in subgraph.edges(data=True, keys=True):
                            # Check that both nodes exist in the nodes list
                            if u in subgraph.nodes() and v in subgraph.nodes():
                                link = {'source': str(u), 'target': str(v)}
                                link.update({k: str(v) if v is not None else None for k, v in data.items()})
                                # Ensure weight field is set for frontend consistency
                                if 'weight' not in link:
                                    # Extract weight from flattened synonym/antonym strength
                                    if 'synonym_strength' in data or 'synonym' in data:
                                        link['weight'] = data.get('synonym_strength', 1.0)
                                # Determine relationship type for easier front-end rendering
                            # We inspect the multigraph edge key and known attribute patterns.
                            # Reason: Users want to distinguish synonyms from antonyms in the neighbour list.
                            relation_type = 'connected'
                            try:
                                if key == 'synonym' or 'synonym_strength' in data or 'synonym' in data:
                                    relation_type = 'synonym'
                                elif key == 'antonym' or 'antonym_strength' in data or 'antonym' in data:
                                    relation_type = 'antonym'
                            except Exception:
                                # Fallback to default if any issue arises
                                relation_type = 'connected'
                                link['relationship'] = relation_type
                                link['id'] = f"{u}-{v}-{key}"
                                links.append(link)
                    else:
                        # For regular graphs, iterate without keys
                        for u, v, data in subgraph.edges(data=True):
                            # Check that both nodes exist in the nodes list
                            if u in subgraph.nodes() and v in subgraph.nodes():
                                link = {'source': str(u), 'target': str(v)}
                                link.update({k: str(v) if v is not None else None for k, v in data.items()})
                                # Ensure weight field is set for frontend consistency
                                if 'weight' not in link:
                                    # Extract weight from flattened synonym/antonym strength
                                    if 'synonym_strength' in data or 'synonym' in data:
                                        link['weight'] = data.get('synonym_strength', 1.0)
                                # Determine relationship type
                                relation_type = 'connected'
                                try:
                                    if 'synonym_strength' in data or 'synonym' in data:
                                        relation_type = 'synonym'
                                    elif 'antonym_strength' in data or 'antonym' in data:
                                        relation_type = 'antonym'
                                except Exception:
                                    relation_type = 'connected'
                                link['relationship'] = relation_type
                                link['id'] = f"{u}-{v}"
                                links.append(link)
                    
                    # Add the graph data to the result
                    result["graph_data"] = {
                        "nodes": nodes,
                        "links": links
                    }
                    logger.info(f"Added graph_data to response with {len(nodes)} nodes and {len(links)} links")
                    
                    # Add update statistics
                    result["update_stats"] = {
                        "nodes_before": graph.number_of_nodes() - len(result.get("changes", {}).get("updated_nodes", [])),
                        "nodes_after": graph.number_of_nodes(),
                        "edges_before": graph.number_of_edges() - (
                            result.get("changes", {}).get("synonyms_added", 0) + 
                            result.get("changes", {}).get("antonyms_added", 0)
                        ),
                        "edges_after": graph.number_of_edges(),
                        "new_nodes": len(result.get("changes", {}).get("updated_nodes", [])),
                        "new_edges": (
                            result.get("changes", {}).get("synonyms_added", 0) + 
                            result.get("changes", {}).get("antonyms_added", 0)
                        )
                    }
                    logger.info(f"Added update_stats to response")
                except Exception as graph_error:
                    # If getting the subgraph fails, we'll still return the generation results
                    # but with an informative message about the graph update issue
                    logger.error(f"Error fetching subgraph data: {graph_error}")
                    result["message"] = f"{result['message']} (Warning: Graph visualization may be incomplete)"
                    result["graph_error"] = str(graph_error)
                    
                    # Try to get at least a minimal graph with just the original node
                    try:
                        if node_id in graph.nodes:
                            minimal_subgraph = nx.Graph()
                            minimal_subgraph.add_node(node_id, **graph.nodes[node_id])
                            
                            # Add immediate valid neighbors
                            for neighbor in graph.neighbors(node_id):
                                minimal_subgraph.add_node(neighbor, **graph.nodes[neighbor])
                                # Get edge data for each connection (could be multiple)
                                # Check if this is a MultiGraph before using keys parameter
                                if hasattr(graph, 'is_multigraph') and graph.is_multigraph():
                                    for _, _, key, data in graph.edges([node_id, neighbor], data=True, keys=True):
                                        if node_id != neighbor:  # Avoid self-loops
                                            minimal_subgraph.add_edge(node_id, neighbor, **data)
                                else:
                                    for _, _, data in graph.edges([node_id, neighbor], data=True):
                                        if node_id != neighbor:  # Avoid self-loops
                                            minimal_subgraph.add_edge(node_id, neighbor, **data)
                            
                            # Format nodes and links
                            nodes = []
                            for node, data in minimal_subgraph.nodes(data=True):
                                node_data = {'id': str(node)}
                                node_data.update({k: str(v) if v is not None else None for k, v in data.items()})
                                nodes.append(node_data)
                            
                            links = []
                            for u, v, data in minimal_subgraph.edges(data=True):
                                link = {'source': str(u), 'target': str(v)}
                                link.update({k: str(v) if v is not None else None for k, v in data.items()})
                                link['id'] = f"{u}-{v}-0"  # Use 0 as default key
                                links.append(link)
                            
                            # Add the minimal graph data to the result
                            result["graph_data"] = {
                                "nodes": nodes,
                                "links": links
                            }
                            logger.info(f"Added minimal fallback graph_data with {len(nodes)} nodes and {len(links)} links")
                            
                            # Still include update statistics
                            result["update_stats"] = {
                                "nodes_before": graph.number_of_nodes() - len(result.get("changes", {}).get("updated_nodes", [])),
                                "nodes_after": graph.number_of_nodes(),
                                "edges_before": graph.number_of_edges() - (
                                    result.get("changes", {}).get("synonyms_added", 0) + 
                                    result.get("changes", {}).get("antonyms_added", 0)
                                ),
                                "edges_after": graph.number_of_edges(),
                                "new_nodes": len(result.get("changes", {}).get("updated_nodes", [])),
                                "new_edges": (
                                    result.get("changes", {}).get("synonyms_added", 0) + 
                                    result.get("changes", {}).get("antonyms_added", 0)
                                )
                            }
                    except Exception as fallback_error:
                        logger.error(f"Error creating minimal fallback graph: {fallback_error}")
                        # Still maintain the original error
            except Exception as data_error:
                # If any part of gathering graph data fails, we'll still return the generation results
                logger.error(f"Error preparing graph data: {data_error}")
                result["graph_data_error"] = str(data_error)
        
        # Log the keys in the result for debugging
        logger.info(f"Final response keys: {', '.join(result.keys())}")
        
        # Return the results
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error generating AI relations for node {node_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}",
            "error": str(e)
        }), 500

@app.route('/enhanced-node', methods=['GET'])
def enhanced_node():
    node_id = request.args.get('id', '')
    model_name = request.args.get('model_name', None)
    if not node_id:
        return jsonify({"error": "No node ID provided"}), 400
    
    # Determine which graph this node belongs to
    graph, language = get_graph_for_node(node_id)
    
    if language == 'croatian':
        # Use Croatian AI explanation generation (faster and more focused than lexical relations)
        try:
            # Generate comprehensive Croatian explanation
            explanation_data = croatian_helper.generate_croatian_explanation(
                node_id, 
                G=graph, 
                model_name=model_name or 'gemini-2.0-flash'
            )
            
            # Get neighbors info
            neighbors_info = croatian_helper.get_croatian_neighbors_info(graph, node_id)
            
            if 'error' not in explanation_data:
                result = {
                    "id": node_id,
                    "language": "croatian",
                    "explanation": explanation_data,
                    "neighbors": neighbors_info,
                    "relationships": []
                }
                return jsonify(result)
            else:
                return jsonify({
                    "id": node_id,
                    "language": "croatian",
                    "explanation": explanation_data,
                    "neighbors": neighbors_info,
                    "relationships": [],
                    "error": explanation_data.get('error', 'Unknown error')
                })
        except Exception as e:
            logger.error(f"Error with Croatian AI explanation: {e}")
            return jsonify({
                "id": node_id,
                "language": "croatian",
                "explanation": {"error": f"Croatian AI explanation failed: {str(e)}"},
                "neighbors": croatian_helper.get_croatian_neighbors_info(graph, node_id),
                "relationships": [],
                "error": str(e)
            }), 500
    
    else:
        # Use Japanese AI generation (existing logic)
        # Check if Gemini API is available (optional here if gemini_helper handles it, but good for early exit)
        if not gemini_helper.is_available():
            # Construct a more complete error response matching what enhance_with_gemini might return on error
            return jsonify({
                "id": node_id,
                "language": "japanese",
                "explanation": {"error": "Gemini API is not available. Please check your API key."},
                "neighbors": gemini_helper.get_neighbor_info(node_id), # Attempt to get basic neighbors
                "relationships": [],
                "error": "Gemini API is not available. Please check your API key."
            }), 503

        # Call the centralized enhance_with_gemini from gemini_helper.py
        # This single call now handles explanation and relationship analysis internally.
        enhanced_data = gemini_helper.enhance_with_gemini(node_id, model_name=model_name) 
        enhanced_data['language'] = 'japanese'
        
        return jsonify(enhanced_data)

# Croatian-specific endpoints
@app.route('/croatian-node-info')
def croatian_node_info():
    """Endpoint specifically for Croatian node information."""
    node_id = request.args.get('id', '')
    if not node_id:
        return jsonify({'error': 'No node ID provided'}), 400
    
    # Check if this is a Croatian node
    if not G_croatian or node_id not in G_croatian.nodes():
        return jsonify({'error': f'Croatian node {node_id} not found'}), 404
    
    # Get Croatian node info
    node_info = croatian_helper.get_croatian_node_info(G_croatian, node_id)
    if not node_info:
        return jsonify({'error': 'Failed to get Croatian node info'}), 500
    
    # Get neighbors info
    neighbors_info = croatian_helper.get_croatian_neighbors_info(G_croatian, node_id)
    node_info['neighbors'] = neighbors_info
    
    return jsonify(node_info)

@app.route('/croatian-search')
def croatian_search():
    """Endpoint for searching Croatian nodes."""
    term = request.args.get('term', '')
    exact = request.args.get('exact', 'false').lower() == 'true'
    
    if not term:
        return jsonify({'error': 'No search term provided'}), 400
    
    # Search Croatian nodes
    matching_nodes = croatian_helper.find_croatian_nodes(G_croatian, term, exact)
    
    # Get basic info for each matching node
    results = []
    for node_id in matching_nodes[:50]:  # Limit to first 50 results
        node_info = croatian_helper.get_croatian_node_info(G_croatian, node_id)
        if node_info:
            results.append(node_info)
    
    return jsonify({
        'term': term,
        'total_matches': len(matching_nodes),
        'results': results
    })

# New endpoints for graph analysis
@app.route('/graph-stats')
def graph_stats():
    """Endpoint to get basic statistics about the graph."""
    try:
        # Calculate basic graph statistics
        stats = {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "is_directed": nx.is_directed(G),
            "density": nx.density(G),
            "avg_degree": sum(d for n, d in G.degree()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
        }
        
        # Count node attributes
        sample_nodes = list(G.nodes())[:min(100, G.number_of_nodes())]
        attribute_keys = set()
        for node in sample_nodes:
            if isinstance(node, float) and math.isnan(node):
                continue
            attribute_keys.update(G.nodes[node].keys())
        
        stats["node_attributes"] = sorted(list(attribute_keys))
        
        # Calculate distribution of POS if available
        if "POS" in attribute_keys:
            pos_distribution = {}
            pos_counts = Counter()
            
            for node in sample_nodes:
                if isinstance(node, float) and math.isnan(node):
                    continue
                if "POS" in G.nodes[node]:
                    pos = G.nodes[node]["POS"]
                    if pos and not (isinstance(pos, float) and math.isnan(pos)):
                        pos_counts[pos] += 1
            
            # Convert counter to dictionary for JSON serialization
            pos_distribution = {pos: count for pos, count in pos_counts.most_common(10)}
            stats["pos_distribution_sample"] = pos_distribution
        
        # Get old_JLPT level distribution if available
        if "old_JLPT" in attribute_keys:
            jlpt_distribution = {}
            jlpt_counts = Counter()
            
            for node in sample_nodes:
                if isinstance(node, float) and math.isnan(node):
                    continue
                if "old_JLPT" in G.nodes[node]:
                    jlpt = G.nodes[node]["old_JLPT"]
                    if jlpt and not (isinstance(jlpt, float) and math.isnan(jlpt)):
                        jlpt_counts[jlpt] += 1
            
            jlpt_distribution = {f"N{jlpt}": count for jlpt, count in jlpt_counts.most_common()}
            stats["jlpt_distribution_sample"] = jlpt_distribution
        
        # Find top-degree nodes
        top_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:10]
        stats["top_degree_nodes"] = [{"node": str(node), "degree": degree} for node, degree in top_nodes]
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error generating graph statistics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/graph-analysis', methods=['GET'])
def graph_analysis():
    """API endpoint to analyze specific parts of the graph."""
    analysis_type = request.args.get('type', 'basic')
    node_id = request.args.get('node', '')
    limit = int(request.args.get('limit', 100))
    
    # Check cache first
    cache_key = f"graph_analysis:{analysis_type}:{node_id}:{limit}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify(json.loads(cached_result))
    
    try:
        result = {}
        
        if analysis_type == 'basic':
            # Basic graph metrics
            result = {
                "node_count": G.number_of_nodes(),
                "edge_count": G.number_of_edges(),
                "density": nx.density(G),
                "is_directed": nx.is_directed(G),
            }
            
            # Compute connected components
            if not nx.is_directed(G):
                connected_components = list(nx.connected_components(G))
                result["connected_components"] = len(connected_components)
                largest_cc = max(connected_components, key=len)
                result["largest_component_size"] = len(largest_cc)
                result["largest_component_percentage"] = len(largest_cc) / G.number_of_nodes() * 100
            
        elif analysis_type == 'degrees':
            # Degree distribution analysis
            degrees = [d for n, d in G.degree()]
            degree_counts = Counter(degrees)
            
            result = {
                "average_degree": sum(degrees) / len(degrees) if degrees else 0,
                "max_degree": max(degrees) if degrees else 0,
                "min_degree": min(degrees) if degrees else 0,
                "degree_distribution": {str(d): count for d, count in degree_counts.most_common(20)}
            }
            
            # Top degree nodes
            top_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:10]
            result["top_degree_nodes"] = [{"node": str(node), "degree": degree} for node, degree in top_nodes]
            
        elif analysis_type == 'node':
            # Node-specific analysis
            if not node_id or node_id not in G:
                return jsonify({"error": "Invalid or missing node ID"}), 400
            
            # Get node attributes
            node_attrs = dict(G.nodes[node_id])
            
            # Get neighbors
            neighbors = list(G.neighbors(node_id))
            
            # Analyze neighbor attributes if they exist
            neighbor_attrs = {}
            if neighbors:
                # Check for common attributes
                sample_neighbor = neighbors[0]
                potential_attrs = G.nodes[sample_neighbor].keys()
                
                for attr in potential_attrs:
                    values = []
                    for neighbor in neighbors:
                        if attr in G.nodes[neighbor]:
                            value = G.nodes[neighbor][attr]
                            if not (isinstance(value, float) and math.isnan(value)):
                                values.append(value)
                    
                    if values:
                        # Count values
                        value_counts = Counter(values)
                        neighbor_attrs[attr] = {str(val): count for val, count in value_counts.most_common(10)}
            
            # Include sample neighbors
            sampled_neighbors = neighbors[:min(limit, len(neighbors))]
            neighbor_details = []
            for neighbor in sampled_neighbors:
                neighbor_data = {
                    "id": str(neighbor),
                    "attributes": {k: str(v) for k, v in G.nodes[neighbor].items()}
                }
                neighbor_details.append(neighbor_data)
            
            result = {
                "node_id": node_id,
                "attributes": node_attrs,
                "degree": G.degree(node_id),
                "neighbor_count": len(neighbors),
                "neighbor_attribute_distribution": neighbor_attrs,
                "sample_neighbors": neighbor_details
            }
            
        elif analysis_type == 'jlpt':
            # old_JLPT level analysis
            jlpt_distribution = {}
            node_counts = {}
            
            # Check if old_JLPT attribute exists
            has_jlpt = False
            for node in list(G.nodes())[:min(1000, G.number_of_nodes())]:
                if isinstance(node, float) and math.isnan(node):
                    continue
                if 'old_JLPT' in G.nodes[node]:
                    has_jlpt = True
                    break
            
            if not has_jlpt:
                return jsonify({"error": "Graph does not contain old_JLPT data"}), 400
            
            # Count nodes by old_JLPT level
            for node in G.nodes():
                if isinstance(node, float) and math.isnan(node):
                    continue
                    
                if 'old_JLPT' in G.nodes[node]:
                    jlpt_value = G.nodes[node]['old_JLPT']
                    if isinstance(jlpt_value, float) and math.isnan(jlpt_value):
                        continue
                        
                    level = float(jlpt_value)
                    if level not in jlpt_distribution:
                        jlpt_distribution[level] = 0
                        node_counts[level] = []
                    
                    jlpt_distribution[level] += 1
                    
                    # Store node IDs (limited to keep response size reasonable)
                    if len(node_counts[level]) < limit:
                        node_counts[level].append(str(node))
            
            # Calculate average degree by old_JLPT level
            avg_degree_by_jlpt = {}
            for level, nodes in node_counts.items():
                if nodes:
                    degrees = [G.degree(node) for node in nodes]
                    avg_degree_by_jlpt[level] = sum(degrees) / len(degrees)
                else:
                    avg_degree_by_jlpt[level] = 0
            
            result = {
                "jlpt_distribution": {f"N{level}": count for level, count in sorted(jlpt_distribution.items())},
                "avg_degree_by_jlpt": {f"N{level}": avg_degree for level, avg_degree in sorted(avg_degree_by_jlpt.items())},
                "sample_nodes_by_jlpt": {f"N{level}": nodes[:min(10, len(nodes))] for level, nodes in sorted(node_counts.items())}
            }
        
        # Cache the result (expire after 1 day)
        cache.set(cache_key, json.dumps(result), 24 * 60 * 60)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in graph analysis: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/generate-exercise', methods=['GET'])
def generate_exercise():
    """
    Endpoint to generate an interactive language learning exercise for a node.
    This allows users to learn Japanese through interactive conversations about a word.
    """
    node_id = request.args.get('id', '')
    level = int(request.args.get('level', '1'))
    mode = request.args.get('mode', 'exercise')  # New parameter: 'exercise' or 'conversation'
    
    if not node_id:
        return jsonify({"error": "No node ID provided"}), 400
    
    try:
        # Check if exercise generation is available
        if not exercises_script.is_available():
            return jsonify({
                "status": "error",
                "message": "Exercise generation is not available. Please check your API key configuration."
            }), 503
        
        # Generate exercise for the node
        logger.info(f"Generating {mode} for node: {node_id} at level {level}")
        
        # Pass the mode to the generate_exercise function
        result = exercises_script.generate_exercise(node_id, level, mode=mode)
        
        # Add node context
        node_context = exercises_script.get_node_context(node_id)
        if "error" not in node_context:
            result["node_context"] = node_context
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error generating {mode} for node {node_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}",
            "error": str(e)
        }), 500

@app.route('/continue-exercise', methods=['POST'])
def continue_exercise():
    """
    Endpoint to continue an interactive language learning exercise.
    This handles the conversation back-and-forth for the interactive learning session.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    node_id = data.get('node_id', '')
    level = int(data.get('level', '1'))
    user_message = data.get('message', '')
    session_history = data.get('history', [])
    mode = data.get('mode', 'exercise')  # New parameter: 'exercise' or 'conversation'
    
    if not node_id:
        return jsonify({"error": "No node ID provided"}), 400
    
    if not user_message:
        return jsonify({"error": "No user message provided"}), 400
    
    try:
        # Check if exercise generation is available
        if not exercises_script.is_available():
            return jsonify({
                "status": "error",
                "message": "Exercise generation is not available. Please check your API key configuration."
            }), 503
        
        # Add the current message to history
        if session_history:
            # If history exists, add the user's message to the last entry
            session_history.append({"user": user_message, "tutor": ""})
        else:
            # Initialize history with the current message
            session_history = [{"user": user_message, "tutor": ""}]
        
        # Generate response, passing the mode parameter
        logger.info(f"Continuing {mode} conversation for node: {node_id}")
        result = exercises_script.generate_exercise(node_id, level, session_history, mode=mode)
        
        # Update the history with the tutor's response
        if session_history:
            session_history[-1]["tutor"] = result.get("content", "")
            result["history"] = session_history
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error continuing {mode} for node {node_id}: {e}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}",
            "error": str(e)
        }), 500

# Register exercise routes explicitly
app.add_url_rule('/exercise-generate', view_func=generate_exercise, methods=['GET'])
app.add_url_rule('/exercise-continue', view_func=continue_exercise, methods=['POST'])

# Croatian exercise endpoints
@app.route('/generate-croatian-exercise', methods=['GET'])
def generate_croatian_exercise():
    """
    Endpoint to generate an interactive Croatian language learning exercise for a node.
    """
    try:
        node_id = request.args.get('node_id')
        level = int(request.args.get('level', 1))
        mode = request.args.get('mode', 'exercise')  # 'exercise' or 'conversation'
        
        if not node_id:
            return jsonify({'error': 'Node ID is required'}), 400
        
        # Check if Croatian exercise generation is available
        if not croatian_exercises.is_available():
            return jsonify({
                "available": False,
                "message": "Croatian exercise generation is not available. Please check your API key configuration."
            }), 503
        
        # Generate Croatian exercise for the node
        result = croatian_exercises.generate_croatian_exercise(node_id, level, mode=mode)
        
        # Also get Croatian node context for additional info
        node_context = croatian_exercises.get_croatian_node_context(node_id)
        
        return jsonify({
            "available": True,
            "exercise": result,
            "node_context": node_context,
            "modes": croatian_exercises.get_croatian_exercise_modes(),
            "levels": croatian_exercises.get_croatian_learning_levels()
        })
    
    except Exception as e:
        logger.error(f"Error generating Croatian exercise: {e}")
        return jsonify({
            "available": True,
            "error": f"Failed to generate Croatian exercise: {str(e)}"
        }), 500

@app.route('/continue-croatian-exercise', methods=['POST'])
def continue_croatian_exercise():
    """
    Endpoint to continue an interactive Croatian language learning exercise.
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        node_id = data.get('node_id')
        level = int(data.get('level', 1))
        session_history = data.get('session_history', [])
        user_message = data.get('message', '')
        mode = data.get('mode', 'exercise')  # 'exercise' or 'conversation'
        
        if not node_id:
            return jsonify({'error': 'Node ID is required'}), 400
        
        # Session history is optional - can be empty for first user message
        # if not session_history:
        #     return jsonify({'error': 'Session history is required for continuing exercise'}), 400
        
        # Check if Croatian exercise generation is available
        if not croatian_exercises.is_available():
            return jsonify({
                "available": False,
                "message": "Croatian exercise generation is not available. Please check your API key configuration."
            }), 503
        
        # Add current user message to session history if provided
        if user_message:
            # Create new session entry with user message (tutor response will be generated)
            session_history = session_history + [{'user': user_message, 'tutor': ''}]
        
        # Continue Croatian exercise
        result = croatian_exercises.generate_croatian_exercise(node_id, level, session_history, mode=mode)
        
        return jsonify({
            "available": True,
            "exercise": result
        })
    
    except Exception as e:
        logger.error(f"Error continuing Croatian exercise: {e}")
        return jsonify({
            "available": True,
            "error": f"Failed to continue Croatian exercise: {str(e)}"
        }), 500

# Register Croatian exercise routes explicitly
app.add_url_rule('/croatian-exercise-generate', view_func=generate_croatian_exercise, methods=['GET'])
app.add_url_rule('/croatian-exercise-continue', view_func=continue_croatian_exercise, methods=['POST'])

@app.route('/analyze-readability', methods=['GET', 'POST'])
def analyze_readability():
    """
    Endpoint to analyze the readability of Japanese text using jreadability.
    Supports both GET and POST requests.
    """
    try:
        # Handle both GET and POST requests
        if request.method == 'GET':
            text = request.args.get('text', '')
            japanese_only = request.args.get('japanese_only', 'true').lower() == 'true'
        else:  # POST
            data = request.json or {}
            text = data.get('text', '')
            japanese_only = data.get('japanese_only', True)
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Check if readability analysis is available
        if not readability_helper.is_readability_available():
            return jsonify({
                "available": False,
                "error": "jreadability library not available. Please install with: pip install jreadability"
            }), 503
        
        # Perform readability analysis
        logger.info(f"Analyzing readability for text: {text[:50]}...")
        analysis = readability_helper.analyze_text_readability(text, japanese_only)
        
        return jsonify(analysis)
    
    except Exception as e:
        logger.error(f"Error analyzing text readability: {e}")
        return jsonify({
            "available": True,
            "error": f"Failed to analyze readability: {str(e)}"
        }), 500

@app.route('/analyze-exercise-readability', methods=['POST'])
def analyze_exercise_readability():
    """
    Endpoint to analyze readability for exercise content.
    Designed specifically for the lexical exercises system.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract exercise content or text to analyze
        content = ""
        for field in ['content', 'text', 'question', 'prompt']:
            if field in data and data[field]:
                content = data[field]
                break
        
        if not content:
            return jsonify({"error": "No content found to analyze"}), 400
        
        # Check if readability analysis is available
        if not readability_helper.is_readability_available():
            return jsonify({
                "available": False,
                "error": "jreadability library not available"
            }), 503
        
        # Perform analysis
        analysis = readability_helper.analyze_text_readability(content, japanese_only=True)
        
        # Add exercise metadata to the response
        analysis['exercise_data'] = {
            'level': data.get('level'),
            'type': data.get('type'),
            'node_id': data.get('node_id')
        }
        
        return jsonify(analysis)
    
    except Exception as e:
        logger.error(f"Error analyzing exercise readability: {e}")
        return jsonify({
            "available": True,
            "error": f"Failed to analyze exercise readability: {str(e)}"
        }), 500

@app.route('/extract-japanese-text', methods=['POST'])
def extract_japanese_text():
    """
    Endpoint to extract Japanese text from provided content.
    Returns both the original text and the extracted Japanese characters.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract text from various possible fields
        text = ""
        for field in ['text', 'content', 'message', 'html']:
            if field in data and data[field]:
                text = data[field]
                break
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Check if readability analysis is available
        if not readability_helper.is_readability_available():
            return jsonify({
                "available": False,
                "error": "jreadability library not available"
            }), 503
        
        # Use the ReadabilityAnalyzer to extract Japanese text
        analyzer = readability_helper.ReadabilityAnalyzer()
        japanese_text = analyzer.extract_japanese_text(text)
        
        # Also extract different types of Japanese characters
        import re
        hiragana = ''.join(re.findall(r'[\u3040-\u309F]', text))  # Hiragana
        katakana = ''.join(re.findall(r'[\u30A0-\u30FF]', text))  # Katakana
        kanji = ''.join(re.findall(r'[\u4E00-\u9FAF]', text))     # Kanji
        punctuation = ''.join(re.findall(r'[\u3000-\u303F\uFF01-\uFF60\u30FC]', text))  # Japanese punctuation
        
        return jsonify({
            "original_text": text,
            "original_length": len(text),
            "japanese_text": japanese_text,
            "japanese_length": len(japanese_text),
            "breakdown": {
                "hiragana": hiragana,
                "hiragana_count": len(hiragana),
                "katakana": katakana,
                "katakana_count": len(katakana),
                "kanji": kanji,
                "kanji_count": len(kanji),
                "punctuation": punctuation,
                "punctuation_count": len(punctuation)
            }
        })
    
    except Exception as e:
        logger.error(f"Error extracting Japanese text: {e}")
        return jsonify({
            "available": True,
            "error": f"Failed to extract Japanese text: {str(e)}"
        }), 500

# TTS endpoint for multi-speaker audio generation
@app.route('/tts', methods=['POST'])
def tts():
    """
    Generate multi-speaker TTS for a conversation turn.
    Expects JSON: { japanese_text: str, translation_text: str }
    Returns: { files: [url1, url2, ...] }
    """
    data = request.json or {}
    japanese_text = data.get('japanese_text', '')
    translation_text = data.get('translation_text', '')

    if not japanese_text:
        return jsonify({'error': 'No Japanese text provided'}), 400
    if not translation_text:
        return jsonify({'error': 'No translation text provided'}), 400

    try:
        prefix = str(uuid.uuid4())
        output_dir = os.path.join(app.static_folder, 'tts')
        file_paths = tts_helper.generate_tts(
            japanese_text,
            translation_text,
            file_prefix=prefix,
            output_dir=output_dir,
            api_key=None
        )
        file_urls = [url_for('static', filename=f'tts/{os.path.basename(path)}') for path in file_paths]
        return jsonify({'files': file_urls})
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run in debug mode locally
    if os.getenv('FLASK_ENV') == 'development':
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        # Setup SSL context for secure HTTP in production
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain("/home/Liks/certs/liks.cer", "/home/Liks/certs/liks.key")
            app.run(host='31.147.206.155', port=8003, debug=False, ssl_context=context)
        except Exception as e:
            logger.error(f"SSL certificate error: {e}")
            # Fallback to non-SSL
            app.run(host='31.147.206.155', port=8003, debug=False)