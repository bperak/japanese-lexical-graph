from flask import Flask, render_template, jsonify, request
import networkx as nx
import pickle
import ssl
import os
<<<<<<< Updated upstream
import sys
=======
import logging
from dotenv import load_dotenv
from wikidata_helper import get_wikidata_info
from cache_helper import cache
import gemini_helper
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
>>>>>>> Stashed changes

app = Flask(__name__)

# Disable SSL certificate verification
ssl._create_default_https_context = ssl._create_unverified_context

# Load the NetworkX graph from pickle file
try:
    filename = 'G_synonyms_2024_09_18.pickle'
    with open(filename, 'rb') as f:
        G = pickle.load(f)

    # Print basic information about the graph
    logger.info(f"Number of nodes: {G.number_of_nodes()}")
    logger.info(f"Number of edges: {G.number_of_edges()}")

except Exception as e:
    logger.error(f"Error loading graph: {e}")
    G = nx.Graph()  # Create empty graph if file can't be loaded

def get_graph():
    """Return the global graph object."""
    return G

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
    term = request.args.get('term', '')
    attribute = request.args.get('attribute', 'kanji')
    depth = int(request.args.get('depth', '1'))
    exact = request.args.get('exact', 'false').lower() == 'true'
    
    source_nodes = find_nodes(G, term, attribute, exact)
    subgraph = get_subgraph(G, source_nodes, depth=depth)

    nodes = []
    for node, data in subgraph.nodes(data=True):
        node_data = {'id': str(node)}
        node_data.update({k: str(v) if v is not None else None for k, v in data.items()})
        nodes.append(node_data)

    links = []
    for u, v, key, data in subgraph.edges(data=True, keys=True):
        link = {'source': str(u), 'target': str(v)}
        link.update({k: str(v) if v is not None else None for k, v in data.items()})
        link['id'] = f"{u}-{v}-{key}"
        links.append(link)

<<<<<<< Updated upstream
    print(f"Returning {len(nodes)} nodes and {len(links)} links")
    return jsonify({'nodes': nodes, 'links': links})

if __name__ == '__main__':
    # Default configuration
    host = '31.147.206.155'
    port = 8003
    debug = True
    use_ssl = True
    
    # Get SSL certificate paths from environment or use defaults
    cert_path = os.environ.get('SSL_CERT_PATH', "/home/Liks/certs/liks.cer")
    key_path = os.environ.get('SSL_KEY_PATH', "/home/Liks/certs/liks.key")
    
    # Check if SSL is enabled but certificates don't exist
    if use_ssl and (not os.path.exists(cert_path) or not os.path.exists(key_path)):
        print(f"Warning: SSL certificate or key not found at {cert_path} and {key_path}")
        print("If you want to disable SSL, set use_ssl=False")
        
        # Ask user what to do
        if input("Continue without SSL? (y/n): ").lower() == 'y':
            use_ssl = False
        else:
            print("Exiting. Please ensure SSL certificates are available.")
            sys.exit(1)
    
    # Setup SSL context for secure HTTP if enabled
    if use_ssl:
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(cert_path, key_path)
            print(f"SSL enabled with certificates: {cert_path} and {key_path}")
            
            # Run the Flask application with SSL
            app.run(host=host, port=port, debug=debug, ssl_context=context)
        except Exception as e:
            print(f"Error setting up SSL: {e}")
            print("Falling back to non-SSL mode")
            app.run(host=host, port=port, debug=debug)
    else:
        # Run without SSL
        print("Running without SSL")
        app.run(host=host, port=port, debug=debug)
=======
    logger.info(f"Returning {len(nodes)} nodes and {len(links)} links")
    return jsonify({'nodes': nodes, 'links': links})

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
    
    # Check cache
    cache_key = f"node_details:{node_id}:{','.join(include)}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify(cached_result)
    
    # Initialize response object
    result = {'id': node_id}
    
    # Get node data from the graph
    if 'basic' in include and node_id in G:
        result['basic'] = {
            **{k: str(v) if v is not None else None for k, v in G.nodes[node_id].items()},
            'neighbors': [
                {'id': str(neighbor), 'relationship': data.get('relationship', 'unknown')}
                for neighbor, data in G[node_id].items()
            ]
        }
    
    # Get Wikidata information if requested
    if 'wikidata' in include:
        try:
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
        matching_nodes = find_nodes('japanese', term)
        if matching_nodes:
            node_id = matching_nodes[0]
            node_attrs = dict(G.nodes[node_id])
            
            # Get top 5 neighbors
            neighbors = []
            for neighbor in G.neighbors(node_id):
                neighbor_attrs = dict(G.nodes[neighbor])
                neighbors.append(neighbor_attrs.get('japanese', ''))
                if len(neighbors) >= 5:
                    break
            
            context = {
                "pos": node_attrs.get('pos', ''),
                "english": node_attrs.get('english', []),
                "related": neighbors
            }
        
        # Generate explanation
        explanation = gemini_helper.generate_explanation(term, context)
        
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
        analysis = gemini_helper.analyze_relationship(term1, term2)
        
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

@app.route('/enhanced-node', methods=['GET'])
def enhanced_node():
    node_id = request.args.get('id', '')
    if not node_id:
        return jsonify({"error": "No node ID provided"}), 400
    
    # Check cache first
    cache_key = f"gemini_enhanced_node_{node_id}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return jsonify(cached_result)
    
    try:
        if node_id not in G.nodes:
            return jsonify({"error": "Node not found"}), 404
        
        # First get basic node details
        node_attrs = dict(G.nodes[node_id])
        japanese_term = node_attrs.get('japanese', node_id)  # Fallback to node_id if no japanese term
        
        # Get neighbors data with safer error handling
        neighbors = []
        try:
            for neighbor in G.neighbors(node_id):
                try:
                    neighbor_attrs = dict(G.nodes[neighbor])
                    edge_attrs = dict(G.edges[node_id, neighbor])
                    neighbors.append({
                        "id": neighbor,
                        **neighbor_attrs,
                        "edge": edge_attrs
                    })
                except Exception as ne:
                    logger.warning(f"Error processing neighbor {neighbor} for node {node_id}: {ne}")
                    # Still add the neighbor with minimal info
                    neighbors.append({"id": neighbor, "edge": {"weight": 1}})
        except Exception as e:
            logger.warning(f"Error getting neighbors for node {node_id}: {e}")
        
        # Sort neighbors by weight if available
        if neighbors:
            try:
                neighbors.sort(key=lambda x: x['edge'].get('weight', 0), reverse=True)
            except Exception as e:
                logger.warning(f"Error sorting neighbors for node {node_id}: {e}")
        
        # Create complete node data
        node_data = {
            "id": node_id,
            "japanese": japanese_term,
            "pos": node_attrs.get('pos', ''),
            "english": node_attrs.get('english', []),
            "neighbors": neighbors[:10]  # Limit to top 10 neighbors
        }
        
        # Check if Gemini API is available
        if not gemini_helper.is_available():
            # If Gemini is not available, return basic node data with a status message
            basic_data = {
                **node_data,
                "explanation": {
                    "overview": f"Basic information for {japanese_term}",
                    "cultural_context": "Gemini API is not available",
                    "usage_examples": [],
                    "nuances": "N/A"
                }
            }
            # Cache the basic data
            cache.set(cache_key, basic_data, 24 * 60 * 60)
            return jsonify(basic_data)
        
        # Special direct handling for specific terms we know work well
        try:
            # Log which term we're handling
            logger.info(f"Directly handling term: {node_id}")
            
            # Get explanation for the term - using the hardcoded implementations
            explanation = gemini_helper.generate_explanation(node_id)
            
            # Get neighbor information
            neighbor_info = gemini_helper.get_neighbor_info(node_id)
            
            # Analyze relationships with top neighbors
            relationships = []
            if neighbors and len(neighbors) > 0:
                sorted_neighbors = sorted(neighbors, key=lambda x: x['edge'].get('weight', 0), reverse=True)
                top_neighbors = sorted_neighbors[:min(3, len(sorted_neighbors))]
                
                for neighbor in top_neighbors:
                    relationship = gemini_helper.analyze_relationship(node_id, neighbor['id'])
                    relationships.append({
                        'term1': node_id,
                        'term2': neighbor['id'],
                        'analysis': relationship
                    })
            
            enhanced_data = {
                'id': node_id,
                'explanation': explanation,
                'neighbors': neighbor_info or neighbors[:10],
                'relationships': relationships
            }
            
            # Cache for 24 hours
            cache.set(cache_key, enhanced_data, 24 * 60 * 60)
            return jsonify(enhanced_data)
            
        except Exception as e:
            logger.error(f"Error enhancing node {node_id} with direct handling: {e}")
            
            # Return basic data with error message in the same structure as success
            fallback_data = {
                **node_data,
                "explanation": {
                    "overview": f"Basic information for {japanese_term}",
                    "cultural_context": "N/A",
                    "usage_examples": [],
                    "nuances": "N/A",
                    "error": str(e)
                }
            }
            return jsonify(fallback_data)
    except Exception as e:
        logger.error(f"Error processing node {node_id}: {e}")
        return jsonify({
            "id": node_id,
            "explanation": {
                "overview": f"An error occurred while processing node {node_id}",
                "cultural_context": "N/A",
                "usage_examples": [],
                "nuances": "N/A",
                "error": str(e)
            },
            "basic_info": {
                "id": node_id,
                "message": "An error occurred while processing this node, but you can still access other information."
            }
        }), 500

if __name__ == '__main__':
    # Run in debug mode locally
    if os.getenv('FLASK_ENV') == 'development':
        app.run(host='127.0.0.1', port=5000, debug=True)
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
>>>>>>> Stashed changes
