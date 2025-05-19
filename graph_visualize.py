#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
graph_visualize.py - NetworkX Graph Visualization Script

This script loads the Japanese lexical graph from a pickle file and
visualizes a small subgraph centered around a selected word.
"""

import os
import sys
import pickle
import math
import time
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

def load_graph(pickle_path):
    """Load NetworkX graph from pickle file."""
    start_time = time.time()
    print(f"Loading graph from {pickle_path}...")
    
    try:
        with open(pickle_path, 'rb') as f:
            G = pickle.load(f)
        
        load_time = time.time() - start_time
        print(f"Graph loaded successfully in {load_time:.2f} seconds.")
        
        # Clean up any NaN node values which can cause issues
        nan_nodes = [node for node in G.nodes() if isinstance(node, float) and math.isnan(node)]
        if nan_nodes:
            print(f"Warning: Found {len(nan_nodes)} NaN nodes in the graph. Removing them.")
            G.remove_nodes_from(nan_nodes)
        
        return G
    except Exception as e:
        print(f"Error loading graph: {e}")
        sys.exit(1)

def extract_ego_network(G, center_word, radius=1):
    """Extract an ego network (neighborhood) around a center word."""
    if center_word not in G:
        print(f"Error: Word '{center_word}' not found in the graph.")
        print("Here are some example words from the graph:")
        for node in list(G.nodes())[:10]:
            print(f"  - {node}")
        return None
    
    # Create ego network (all nodes within radius of center_word)
    ego_net = nx.ego_graph(G, center_word, radius=radius, undirected=True)
    
    # If too many nodes, limit to the most central ones
    if ego_net.number_of_nodes() > 50:
        print(f"Ego network is large ({ego_net.number_of_nodes()} nodes). Limiting to most connected neighbors.")
        # Sort neighbors by degree
        neighbors = list(G.neighbors(center_word))
        neighbors_with_degree = [(n, G.degree(n)) for n in neighbors]
        sorted_neighbors = sorted(neighbors_with_degree, key=lambda x: x[1], reverse=True)
        
        # Take top 20 neighbors
        top_neighbors = [n for n, d in sorted_neighbors[:20]]
        
        # Create subgraph with center and top neighbors
        nodes_to_keep = [center_word] + top_neighbors
        ego_net = G.subgraph(nodes_to_keep)
    
    print(f"Created ego network with {ego_net.number_of_nodes()} nodes and {ego_net.number_of_edges()} edges")
    return ego_net

def add_node_attributes(G, ego_net):
    """Add node attributes from the original graph to the ego network."""
    for node in ego_net.nodes():
        attrs = G.nodes[node]
        for key, value in attrs.items():
            ego_net.nodes[node][key] = value
    return ego_net

def visualize_graph(ego_net, center_word, output_file='graph_visualization.png'):
    """Visualize the ego network and save to a file."""
    plt.figure(figsize=(12, 10))
    
    # Set up the layout
    pos = nx.spring_layout(ego_net, seed=42)
    
    # Node sizes based on degree
    node_sizes = [300 + 100 * ego_net.degree(n) for n in ego_net.nodes()]
    
    # Node colors - highlight center word
    node_colors = ['red' if n == center_word else 'skyblue' for n in ego_net.nodes()]
    
    # Draw nodes
    nx.draw_networkx_nodes(ego_net, pos, 
                          node_size=node_sizes,
                          node_color=node_colors, 
                          alpha=0.8)
    
    # Draw edges
    nx.draw_networkx_edges(ego_net, pos, width=1.0, alpha=0.5)
    
    # Draw labels with Japanese text
    try:
        # Try to find a font that supports Japanese characters
        japanese_fonts = [f for f in font_manager.findSystemFonts() 
                         if any(name in f.lower() for name in ['gothic', 'mincho', 'yu', 'meiryo', 'msgothic', 'japan'])]
        
        if japanese_fonts:
            # Use the first found Japanese font
            font_path = japanese_fonts[0]
            font_prop = font_manager.FontProperties(fname=font_path)
            nx.draw_networkx_labels(ego_net, pos, font_size=12, font_family=font_prop.get_name())
            print(f"Using Japanese font: {font_prop.get_name()}")
        else:
            # Fallback to default font
            nx.draw_networkx_labels(ego_net, pos, font_size=12)
            print("Warning: No Japanese fonts found. Labels may not display correctly.")
    except:
        # Fallback if font detection fails
        nx.draw_networkx_labels(ego_net, pos, font_size=12)
        print("Warning: Error setting font. Labels may not display correctly.")
    
    # Add title and remove axes
    plt.title(f"Japanese Lexical Network around '{center_word}'", fontsize=16)
    plt.axis('off')
    
    # Save figure
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {output_file}")
    
    # Try to display if running in an environment with a display
    try:
        plt.show()
    except:
        pass

def get_node_info(G, node):
    """Get and print detailed information about a node."""
    if node not in G:
        print(f"Node '{node}' not found in the graph.")
        return
    
    attrs = G.nodes[node]
    neighbors = list(G.neighbors(node))
    
    print(f"\nInformation for word: {node}")
    print("-" * 50)
    
    # Print attributes
    print("Attributes:")
    for key, value in attrs.items():
        print(f"  {key}: {value}")
    
    # Print neighbors (synonyms)
    print("\nSynonyms/Connected Words:")
    for i, neighbor in enumerate(sorted(neighbors)[:20]):  # Limit to first 20
        print(f"  {i+1}. {neighbor}")
    
    if len(neighbors) > 20:
        print(f"  ... and {len(neighbors) - 20} more")
    
    print("-" * 50)

def main():
    """Main execution function."""
    pickle_path = "G_synonyms_2024_09_18.pickle"
    
    if not os.path.exists(pickle_path):
        print(f"Error: File {pickle_path} not found.")
        sys.exit(1)
    
    # Let user specify a word, default to a common word if none provided
    if len(sys.argv) > 1:
        center_word = sys.argv[1]
    else:
        center_word = "時間"  # "time" - a common word likely to have many connections
    
    # Load the graph
    G = load_graph(pickle_path)
    
    # Get detailed info about the center word
    get_node_info(G, center_word)
    
    # Extract and visualize ego network
    ego_net = extract_ego_network(G, center_word, radius=1)
    if ego_net:
        ego_net = add_node_attributes(G, ego_net)
        output_file = f"japanese_graph_{center_word}.png"
        visualize_graph(ego_net, center_word, output_file)

if __name__ == "__main__":
    main() 