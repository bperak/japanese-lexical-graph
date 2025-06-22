from flask import Flask, render_template, jsonify, request
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
    filename = os.path.join('graph_models', 'G_synonyms_2024_09_18.pickle')
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
    """
    node_id = request.args.get('id', '')
    if not node_id:
        return jsonify({"error": "No node ID provided"}), 400
    
    try:
        # Check if AI generation is available
        if not ai_generation_single.is_available():
            return jsonify({
                "status": "error",
                "message": "AI Generation is not available. Please check your API key configuration."
            }), 503
        
        # Generate relations for the node
        logger.info(f"Generating AI relations for node: {node_id}")
        result = ai_generation_single.generate_node_relations(node_id, G)
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
                    # Get the valid nodes that exist in the graph
                    valid_source_nodes = [node for node in source_nodes if node in G.nodes]
                    if len(valid_source_nodes) < len(source_nodes):
                        missing_nodes = [node for node in source_nodes if node not in G.nodes]
                        logger.warning(f"Some nodes weren't found in the graph and will be skipped: {missing_nodes}")
                    
                    # Continue with valid nodes
                    subgraph = get_subgraph(G, valid_source_nodes, depth=depth)
                    logger.info(f"Got subgraph with {subgraph.number_of_nodes()} nodes and {subgraph.number_of_edges()} edges")
                    
                    # Format nodes and links
                    nodes = []
                    for node, data in subgraph.nodes(data=True):
                        node_data = {'id': str(node)}
                        node_data.update({k: str(v) if v is not None else None for k, v in data.items()})
                        nodes.append(node_data)
                    
                    links = []
                    for u, v, key, data in subgraph.edges(data=True, keys=True):
                        # Check that both nodes exist in the nodes list
                        if u in subgraph.nodes() and v in subgraph.nodes():
                            link = {'source': str(u), 'target': str(v)}
                            link.update({k: str(v) if v is not None else None for k, v in data.items()})
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
                    
                    # Add the graph data to the result
                    result["graph_data"] = {
                        "nodes": nodes,
                        "links": links
                    }
                    logger.info(f"Added graph_data to response with {len(nodes)} nodes and {len(links)} links")
                    
                    # Add update statistics
                    result["update_stats"] = {
                        "nodes_before": G.number_of_nodes() - len(result.get("changes", {}).get("updated_nodes", [])),
                        "nodes_after": G.number_of_nodes(),
                        "edges_before": G.number_of_edges() - (
                            result.get("changes", {}).get("synonyms_added", 0) + 
                            result.get("changes", {}).get("antonyms_added", 0)
                        ),
                        "edges_after": G.number_of_edges(),
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
                        if node_id in G.nodes:
                            minimal_subgraph = nx.Graph()
                            minimal_subgraph.add_node(node_id, **G.nodes[node_id])
                            
                            # Add immediate valid neighbors
                            for neighbor in G.neighbors(node_id):
                                minimal_subgraph.add_node(neighbor, **G.nodes[neighbor])
                                # Get edge data for each connection (could be multiple)
                                for _, _, key, data in G.edges([node_id, neighbor], data=True, keys=True):
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
                                "nodes_before": G.number_of_nodes() - len(result.get("changes", {}).get("updated_nodes", [])),
                                "nodes_after": G.number_of_nodes(),
                                "edges_before": G.number_of_edges() - (
                                    result.get("changes", {}).get("synonyms_added", 0) + 
                                    result.get("changes", {}).get("antonyms_added", 0)
                                ),
                                "edges_after": G.number_of_edges(),
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
    
    # Check if Gemini API is available (optional here if gemini_helper handles it, but good for early exit)
    if not gemini_helper.is_available():
        # Construct a more complete error response matching what enhance_with_gemini might return on error
        return jsonify({
            "id": node_id,
            "explanation": {"error": "Gemini API is not available. Please check your API key."},
            "neighbors": gemini_helper.get_neighbor_info(node_id), # Attempt to get basic neighbors
            "relationships": [],
            "error": "Gemini API is not available. Please check your API key."
        }), 503

    # Call the centralized enhance_with_gemini from gemini_helper.py
    # This single call now handles explanation and relationship analysis internally.
    enhanced_data = gemini_helper.enhance_with_gemini(node_id, model_name=model_name) 
    
    return jsonify(enhanced_data)

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
        
        # Get JLPT level distribution if available
        if "JLPT" in attribute_keys:
            jlpt_distribution = {}
            jlpt_counts = Counter()
            
            for node in sample_nodes:
                if isinstance(node, float) and math.isnan(node):
                    continue
                if "JLPT" in G.nodes[node]:
                    jlpt = G.nodes[node]["JLPT"]
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
            # JLPT level analysis
            jlpt_distribution = {}
            node_counts = {}
            
            # Check if JLPT attribute exists
            has_jlpt = False
            for node in list(G.nodes())[:min(1000, G.number_of_nodes())]:
                if isinstance(node, float) and math.isnan(node):
                    continue
                if 'JLPT' in G.nodes[node]:
                    has_jlpt = True
                    break
            
            if not has_jlpt:
                return jsonify({"error": "Graph does not contain JLPT data"}), 400
            
            # Count nodes by JLPT level
            for node in G.nodes():
                if isinstance(node, float) and math.isnan(node):
                    continue
                    
                if 'JLPT' in G.nodes[node]:
                    jlpt_value = G.nodes[node]['JLPT']
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
            
            # Calculate average degree by JLPT level
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