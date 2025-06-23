#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
graph_analysis.py - NetworkX Graph Structure Analysis Script

This script loads and analyzes the structure of a Japanese lexical graph
from a pickle file, providing detailed metrics and insights about the graph.
"""

import os
import sys
import pickle
import time
import networkx as nx
from collections import Counter, defaultdict
import numpy as np
from datetime import datetime
import math
import pandas as pd
from tabulate import tabulate
import json

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

def basic_graph_stats(G):
    """Calculate and print basic graph statistics."""
    print("\n=== BASIC GRAPH STATISTICS ===")
    print(f"Number of nodes: {G.number_of_nodes():,}")
    print(f"Number of edges: {G.number_of_edges():,}")
    
    if nx.is_directed(G):
        print("Graph type: Directed")
    else:
        print("Graph type: Undirected")
    
    # Density
    density = nx.density(G)
    print(f"Graph density: {density:.8f}")
    
    # Check if graph is connected
    try:
        if nx.is_directed(G):
            is_strongly_connected = nx.is_strongly_connected(G)
            print(f"Is strongly connected: {is_strongly_connected}")
            
            if not is_strongly_connected:
                strongly_connected_components = list(nx.strongly_connected_components(G))
                print(f"Number of strongly connected components: {len(strongly_connected_components):,}")
                sizes = [len(c) for c in strongly_connected_components]
                print(f"Largest strongly connected component size: {max(sizes):,} nodes")
                print(f"Percentage of nodes in largest component: {max(sizes) / G.number_of_nodes() * 100:.2f}%")
        else:
            try:
                is_connected = nx.is_connected(G)
                print(f"Is connected: {is_connected}")
                
                if not is_connected:
                    connected_components = list(nx.connected_components(G))
                    print(f"Number of connected components: {len(connected_components):,}")
                    sizes = [len(c) for c in connected_components]
                    print(f"Largest connected component size: {max(sizes):,} nodes")
                    print(f"Percentage of nodes in largest component: {max(sizes) / G.number_of_nodes() * 100:.2f}%")
            except Exception as e:
                print(f"Error analyzing connectivity: {e}")
                print("Computing connected components using a safer method...")
                
                # Alternative method to find connected components
                components = []
                nodes = set(G.nodes())
                
                while nodes:
                    # Get a node from remaining nodes
                    root = next(iter(nodes))
                    try:
                        # Try to get its component
                        component = nx.node_connected_component(G, root)
                        components.append(component)
                        nodes -= component
                    except Exception as e2:
                        print(f"Error with node {root}: {e2}")
                        # Remove just this problematic node
                        nodes.remove(root)
                
                print(f"Found {len(components):,} connected components using alternative method")
                if components:
                    sizes = [len(c) for c in components]
                    print(f"Largest component size: {max(sizes):,} nodes")
                    print(f"Percentage of nodes in largest component: {max(sizes) / G.number_of_nodes() * 100:.2f}%")
    except Exception as e:
        print(f"Error analyzing graph connectivity: {e}")

def degree_distribution(G):
    """Analyze and plot the degree distribution of the graph."""
    print("\n=== DEGREE DISTRIBUTION ===")
    
    if nx.is_directed(G):
        in_degrees = [d for n, d in G.in_degree()]
        out_degrees = [d for n, d in G.out_degree()]
        
        # Calculate statistics
        avg_in_degree = sum(in_degrees) / len(in_degrees)
        avg_out_degree = sum(out_degrees) / len(out_degrees)
        max_in_degree = max(in_degrees)
        max_out_degree = max(out_degrees)
        
        print(f"Average in-degree: {avg_in_degree:.2f}")
        print(f"Average out-degree: {avg_out_degree:.2f}")
        print(f"Maximum in-degree: {max_in_degree}")
        print(f"Maximum out-degree: {max_out_degree}")
        
        # Find nodes with highest in-degree and out-degree
        max_in_node = max(G.in_degree(), key=lambda x: x[1])[0]
        max_out_node = max(G.out_degree(), key=lambda x: x[1])[0]
        
        print(f"Node with highest in-degree: {max_in_node} (degree: {G.in_degree(max_in_node)})")
        print(f"Node with highest out-degree: {max_out_node} (degree: {G.out_degree(max_out_node)})")
        
        # Degree distribution analysis
        in_degree_counts = Counter(in_degrees)
        out_degree_counts = Counter(out_degrees)
        
        print("\nIn-degree distribution overview:")
        for degree in sorted(in_degree_counts.keys())[:10]:
            print(f"  In-degree {degree}: {in_degree_counts[degree]:,} nodes")
        
        print("\nOut-degree distribution overview:")
        for degree in sorted(out_degree_counts.keys())[:10]:
            print(f"  Out-degree {degree}: {out_degree_counts[degree]:,} nodes")
    
    else:  # Undirected graph
        degrees = [d for n, d in G.degree()]
        
        # Calculate statistics
        avg_degree = sum(degrees) / len(degrees)
        max_degree = max(degrees)
        
        print(f"Average degree: {avg_degree:.2f}")
        print(f"Maximum degree: {max_degree}")
        
        # Find node with highest degree
        max_degree_node = max(G.degree(), key=lambda x: x[1])[0]
        print(f"Node with highest degree: {max_degree_node} (degree: {G.degree(max_degree_node)})")
        
        # Degree distribution analysis
        degree_counts = Counter(degrees)
        
        print("\nDegree distribution overview:")
        for degree in sorted(degree_counts.keys())[:10]:
            print(f"  Degree {degree}: {degree_counts[degree]:,} nodes")

def centrality_analysis(G, sample_size=1000):
    """Calculate centrality measures for a sample of nodes."""
    print(f"\n=== CENTRALITY ANALYSIS (Sample of {sample_size} nodes) ===")
    
    # Create a clean subgraph for analysis
    # Ensure no problematic nodes are included in the sample
    valid_nodes = [n for n in G.nodes() if not (isinstance(n, float) and math.isnan(n))]
    
    if len(valid_nodes) > sample_size:
        # Sample nodes for analysis to avoid excessive computation
        try:
            sampled_nodes = np.random.choice(valid_nodes, sample_size, replace=False)
            subgraph = G.subgraph(sampled_nodes)
            print(f"Analyzing a random sample of {sample_size} nodes due to graph size.")
        except Exception as e:
            print(f"Error sampling nodes: {e}")
            print("Using first {sample_size} nodes instead")
            sampled_nodes = valid_nodes[:sample_size]
            subgraph = G.subgraph(sampled_nodes)
    else:
        subgraph = G.subgraph(valid_nodes)
        print(f"Analyzing {len(valid_nodes)} valid nodes for centrality measures.")
    
    print("Computing centrality measures (this may take some time)...")
    
    start_time = time.time()
    
    try:
        # Degree centrality
        if nx.is_directed(G):
            in_degree_centrality = nx.in_degree_centrality(subgraph)
            out_degree_centrality = nx.out_degree_centrality(subgraph)
            
            top_in_degree = sorted(in_degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
            top_out_degree = sorted(out_degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
            
            print("\nTop 5 nodes by in-degree centrality:")
            for node, centrality in top_in_degree:
                print(f"  Node: {node}, Centrality: {centrality:.4f}")
                
            print("\nTop 5 nodes by out-degree centrality:")
            for node, centrality in top_out_degree:
                print(f"  Node: {node}, Centrality: {centrality:.4f}")
        else:
            degree_centrality = nx.degree_centrality(subgraph)
            top_degree = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
            
            print("\nTop 5 nodes by degree centrality:")
            for node, centrality in top_degree:
                print(f"  Node: {node}, Centrality: {centrality:.4f}")
        
        # Betweenness centrality (for smaller samples only)
        if subgraph.number_of_nodes() <= 1000:
            print("\nComputing betweenness centrality...")
            betweenness_centrality = nx.betweenness_centrality(subgraph, k=min(100, subgraph.number_of_nodes()))
            top_betweenness = sorted(betweenness_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
            
            print("\nTop 5 nodes by betweenness centrality:")
            for node, centrality in top_betweenness:
                print(f"  Node: {node}, Centrality: {centrality:.4f}")
        else:
            print("\nSkipping betweenness centrality calculation due to graph size.")
        
        elapsed_time = time.time() - start_time
        print(f"\nCentrality analysis completed in {elapsed_time:.2f} seconds.")
    
    except Exception as e:
        print(f"Error during centrality analysis: {e}")

def community_detection(G):
    """Detect communities in the graph."""
    print("\n=== COMMUNITY DETECTION ===")
    
    try:
        # Ensure there are no NaN nodes
        valid_nodes = [n for n in G.nodes() if not (isinstance(n, float) and math.isnan(n))]
        clean_graph = G.subgraph(valid_nodes).copy()
        
        # Use largest connected component for community detection
        if nx.is_directed(clean_graph):
            # For directed graphs, work with the largest strongly connected component
            try:
                largest_cc = max(nx.strongly_connected_components(clean_graph), key=len)
            except Exception as e:
                print(f"Error finding strongly connected components: {e}")
                print("Converting to undirected graph for component analysis")
                undirected = clean_graph.to_undirected()
                largest_cc = max(nx.connected_components(undirected), key=len)
        else:
            # For undirected graphs, work with the largest connected component
            try:
                largest_cc = max(nx.connected_components(clean_graph), key=len)
            except Exception as e:
                print(f"Error finding connected components: {e}")
                # Alternative approach - find a valid component
                components = []
                nodes = set(clean_graph.nodes())
                
                while nodes and len(components) < 1:
                    root = next(iter(nodes))
                    try:
                        component = nx.node_connected_component(clean_graph, root)
                        components.append(component)
                        nodes -= component
                    except Exception as e2:
                        print(f"Error with node {root}: {e2}")
                        nodes.remove(root)
                
                if components:
                    largest_cc = max(components, key=len)
                else:
                    print("Could not find any valid components for community detection")
                    return
        
        # Create subgraph of largest component
        largest_cc_graph = clean_graph.subgraph(largest_cc).copy()
        
        print(f"Performing community detection on largest connected component with {largest_cc_graph.number_of_nodes():,} nodes")
        
        # If the component is too large, sample it
        if largest_cc_graph.number_of_nodes() > 1000:
            print("Component is large, sampling 1000 nodes for community detection")
            try:
                sampled_nodes = np.random.choice(list(largest_cc_graph.nodes()), 1000, replace=False)
                largest_cc_graph = largest_cc_graph.subgraph(sampled_nodes).copy()
            except Exception as e:
                print(f"Error sampling nodes: {e}")
                # Take first 1000 nodes
                sampled_nodes = list(largest_cc_graph.nodes())[:1000]
                largest_cc_graph = largest_cc_graph.subgraph(sampled_nodes).copy()
        
        start_time = time.time()
        
        # Convert to undirected for community detection if necessary
        if nx.is_directed(largest_cc_graph):
            largest_cc_graph = largest_cc_graph.to_undirected()
        
        # Use greedy modularity maximization
        try:
            communities = list(nx.community.greedy_modularity_communities(largest_cc_graph))
            
            elapsed_time = time.time() - start_time
            print(f"Community detection completed in {elapsed_time:.2f} seconds")
            
            print(f"Number of communities detected: {len(communities)}")
            
            # Print sizes of top communities
            community_sizes = [len(c) for c in communities]
            print("\nTop 10 community sizes:")
            for i, size in enumerate(sorted(community_sizes, reverse=True)[:10]):
                print(f"  Community {i+1}: {size} nodes")
            
            # Calculate modularity
            modularity = nx.community.modularity(largest_cc_graph, communities)
            print(f"\nModularity: {modularity:.4f}")
        except Exception as e:
            print(f"Error during community detection algorithm: {e}")
            
    except Exception as e:
        print(f"Error during community detection: {e}")

def create_report(G, output_path="graph_analysis_report.txt"):
    """Create a comprehensive text report of the graph analysis."""
    print(f"\n=== GENERATING REPORT TO {output_path} ===")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Report header
            f.write("=" * 80 + "\n")
            f.write(f"GRAPH ANALYSIS REPORT\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Graph: G_synonyms_2024_09_18.pickle\n")
            f.write("=" * 80 + "\n\n")
            
            # Basic statistics
            f.write("BASIC GRAPH STATISTICS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Number of nodes: {G.number_of_nodes():,}\n")
            f.write(f"Number of edges: {G.number_of_edges():,}\n")
            f.write(f"Graph type: {'Directed' if nx.is_directed(G) else 'Undirected'}\n")
            f.write(f"Graph density: {nx.density(G):.8f}\n\n")
            
            # Check for problematic nodes
            nan_nodes = [node for node in G.nodes() if isinstance(node, float) and math.isnan(node)]
            if nan_nodes:
                f.write(f"Note: Graph contains {len(nan_nodes)} NaN nodes\n\n")
            
            # Node attributes
            f.write("NODE ATTRIBUTES\n")
            f.write("-" * 80 + "\n")
            
            # Get a sample node to check available attributes
            valid_nodes = [n for n in G.nodes() if not (isinstance(n, float) and math.isnan(n))]
            if valid_nodes:
                sample_node = valid_nodes[0]
                node_attrs = G.nodes[sample_node]
                
                f.write(f"Available node attributes: {list(node_attrs.keys())}\n\n")
                
                # Show sample of node values
                f.write("Sample node values:\n")
                for i, node in enumerate(valid_nodes[:5]):
                    f.write(f"  Node {i+1}: {node}\n")
                f.write("\n")
            else:
                f.write("No valid nodes found for attribute analysis\n\n")
            
            # Edge attributes
            if G.number_of_edges() > 0:
                f.write("EDGE ATTRIBUTES\n")
                f.write("-" * 80 + "\n")
                
                try:
                    # Get a sample edge to check available attributes
                    sample_edge = next(iter(G.edges()))
                    edge_attrs = G.edges[sample_edge]
                    
                    f.write(f"Available edge attributes: {list(edge_attrs.keys())}\n\n")
                    
                    # Show sample of edge values
                    f.write("Sample edges:\n")
                    edges = list(G.edges())[:5]
                    for i, edge in enumerate(edges):
                        f.write(f"  Edge {i+1}: {edge[0]} -- {edge[1]}\n")
                    f.write("\n")
                except Exception as e:
                    f.write(f"Error analyzing edge attributes: {e}\n\n")
            
            # Degree distribution summary
            f.write("DEGREE DISTRIBUTION SUMMARY\n")
            f.write("-" * 80 + "\n")
            
            if nx.is_directed(G):
                in_degrees = [d for n, d in G.in_degree() if not (isinstance(n, float) and math.isnan(n))]
                out_degrees = [d for n, d in G.out_degree() if not (isinstance(n, float) and math.isnan(n))]
                
                avg_in_degree = sum(in_degrees) / len(in_degrees) if in_degrees else 0
                avg_out_degree = sum(out_degrees) / len(out_degrees) if out_degrees else 0
                max_in_degree = max(in_degrees) if in_degrees else 0
                max_out_degree = max(out_degrees) if out_degrees else 0
                
                f.write(f"Average in-degree: {avg_in_degree:.2f}\n")
                f.write(f"Average out-degree: {avg_out_degree:.2f}\n")
                f.write(f"Maximum in-degree: {max_in_degree}\n")
                f.write(f"Maximum out-degree: {max_out_degree}\n\n")
                
                # In-degree frequency
                in_degree_counts = Counter(in_degrees)
                f.write("In-degree frequency (top 20):\n")
                for degree in sorted(in_degree_counts.keys())[:20]:
                    f.write(f"  In-degree {degree}: {in_degree_counts[degree]:,} nodes\n")
                f.write("\n")
                
                # Out-degree frequency
                out_degree_counts = Counter(out_degrees)
                f.write("Out-degree frequency (top 20):\n")
                for degree in sorted(out_degree_counts.keys())[:20]:
                    f.write(f"  Out-degree {degree}: {out_degree_counts[degree]:,} nodes\n")
                f.write("\n")
            else:
                degrees = [d for n, d in G.degree() if not (isinstance(n, float) and math.isnan(n))]
                
                avg_degree = sum(degrees) / len(degrees) if degrees else 0
                max_degree = max(degrees) if degrees else 0
                
                f.write(f"Average degree: {avg_degree:.2f}\n")
                f.write(f"Maximum degree: {max_degree}\n\n")
                
                # Degree frequency
                degree_counts = Counter(degrees)
                f.write("Degree frequency (top 20):\n")
                for degree in sorted(degree_counts.keys())[:20]:
                    f.write(f"  Degree {degree}: {degree_counts[degree]:,} nodes\n")
                f.write("\n")
            
            # Final summary
            f.write("ANALYSIS SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write("This analysis provides an overview of the graph structure including basic statistics,\n")
            f.write("connectivity information, and degree distribution. For a more detailed analysis,\n")
            f.write("run the graph_analysis.py script with advanced options.\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")
        
        print(f"Report successfully written to {output_path}")
    except Exception as e:
        print(f"Error generating report: {e}")

def analyze_node_attributes(G, sample_size=100):
    """Analyze and display detailed information about node attributes."""
    print("\n=== NODE ATTRIBUTE ANALYSIS ===")
    
    # Get valid nodes (non-NaN)
    valid_nodes = [n for n in G.nodes() if not (isinstance(n, float) and math.isnan(n))]
    
    # Get all available attribute keys
    attribute_keys = set()
    for node in valid_nodes[:min(1000, len(valid_nodes))]:  # Sample to find all keys
        attribute_keys.update(G.nodes[node].keys())
    
    print(f"Found {len(attribute_keys)} node attributes: {', '.join(sorted(attribute_keys))}")
    
    # Sample nodes for analysis
    if len(valid_nodes) > sample_size:
        sample_nodes = np.random.choice(valid_nodes, sample_size, replace=False)
    else:
        sample_nodes = valid_nodes
        
    print(f"Analyzing attributes for a sample of {len(sample_nodes)} nodes")
    
    # Analyze each attribute
    for attr in sorted(attribute_keys):
        print(f"\nAnalyzing attribute: '{attr}'")
        
        # Get attribute values for the sample
        values = []
        for node in sample_nodes:
            if attr in G.nodes[node]:
                values.append(G.nodes[node][attr])
        
        # Count value frequency
        value_counts = Counter(values)
        
        # Determine attribute type
        if all(isinstance(val, (int, float)) for val in values if not (isinstance(val, float) and math.isnan(val))):
            attr_type = "Numeric"
            non_nan_values = [v for v in values if not (isinstance(v, float) and math.isnan(v))]
            if non_nan_values:
                print(f"  Type: {attr_type}")
                print(f"  Min: {min(non_nan_values)}")
                print(f"  Max: {max(non_nan_values)}")
                print(f"  Mean: {sum(non_nan_values) / len(non_nan_values):.2f}")
            else:
                print(f"  Type: {attr_type} (all NaN values)")
        else:
            attr_type = "Categorical"
            print(f"  Type: {attr_type}")
            # Show most common values
            print(f"  Most common values:")
            for val, count in value_counts.most_common(10):
                val_str = str(val)
                if len(val_str) > 50:
                    val_str = val_str[:47] + "..."
                print(f"    {val_str}: {count} occurrences ({count/len(values)*100:.1f}%)")
        
        # Count missing values
        missing_count = sum(1 for node in sample_nodes if attr not in G.nodes[node] or 
                           (isinstance(G.nodes[node][attr], float) and math.isnan(G.nodes[node][attr])))
        if missing_count > 0:
            print(f"  Missing values: {missing_count} ({missing_count/len(sample_nodes)*100:.1f}%)")
    
    # Sample node display
    print("\n--- Sample Nodes with Attributes ---")
    for i, node in enumerate(sample_nodes[:5]):
        print(f"\nNode {i+1}: {node}")
        for attr, value in sorted(G.nodes[node].items()):
            print(f"  {attr}: {value}")

def analyze_edge_attributes(G, sample_size=1000):
    """Analyze the attributes available on edges."""
    print("\n=== EDGE ATTRIBUTE ANALYSIS ===")
    
    if not G.edges():
        print("No edges found in the graph.")
        return
    
    # Check if there are any edge attributes
    edge_attrs_present = False
    for edge in G.edges():
        edge_data = G.get_edge_data(*edge)
        if edge_data and len(edge_data) > 0:
            edge_attrs_present = True
            break
    
    if not edge_attrs_present:
        print("No edge attributes found in the graph.")
        return
    
    # Sample edges for analysis
    edge_list = list(G.edges())
    sample_size = min(sample_size, len(edge_list))
    
    if sample_size < len(edge_list):
        # Use indices for sampling to avoid issues with edge objects
        sampled_indices = np.random.choice(len(edge_list), sample_size, replace=False)
        sampled_edges = [edge_list[i] for i in sampled_indices]
    else:
        sampled_edges = edge_list
    
    # Collect all attribute keys
    all_attrs = set()
    for edge in sampled_edges:
        edge_data = G.get_edge_data(*edge)
        if edge_data:
            for attr in edge_data:
                all_attrs.add(attr)
    
    if not all_attrs:
        print("No attributes found in sampled edges.")
        return
    
    print(f"Found {len(all_attrs)} edge attributes: {sorted(all_attrs)}")
    
    # Analyze each attribute
    for attr in sorted(all_attrs):
        print(f"\nAttribute: {attr}")
        
        # Collect values
        values = []
        missing = 0
        complex_values = 0
        
        for edge in sampled_edges:
            edge_data = G.get_edge_data(*edge)
            if edge_data and attr in edge_data:
                value = edge_data[attr]
                
                # Handle different value types
                if isinstance(value, (int, float, str, bool)):
                    if isinstance(value, float) and math.isnan(value):
                        missing += 1
                    else:
                        values.append(value)
                else:
                    # For complex types like dictionaries, just count them
                    complex_values += 1
            else:
                missing += 1
        
        # Calculate statistics
        if values:
            value_counts = {}
            
            # For basic types, we can count occurrences
            if all(isinstance(v, (int, float)) for v in values):
                # Numeric attribute
                print(f"  Type: Numeric")
                if values:
                    print(f"  Min: {min(values)}")
                    print(f"  Max: {max(values)}")
                    print(f"  Mean: {np.mean(values)}")
                    print(f"  Median: {np.median(values)}")
            else:
                # Categorical attribute - only count if not complex objects
                print(f"  Type: Categorical")
                
                # Count frequencies, handling hashable types
                for v in values:
                    try:
                        if v in value_counts:
                            value_counts[v] += 1
                        else:
                            value_counts[v] = 1
                    except TypeError:
                        # Skip unhashable types
                        complex_values += 1
                
                # Show top categories
                if value_counts:
                    top_cats = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                    print(f"  Top values: {top_cats}")
        
        # Show missing and complex count
        print(f"  Valid values: {len(values)}")
        if complex_values > 0:
            print(f"  Complex values (unhashable): {complex_values}")
        print(f"  Missing values: {missing} ({missing/sample_size:.1%})")
    
    # Show some example edges with their attributes
    print("\nSample edges with attributes:")
    count = 0
    for edge in sampled_edges:
        edge_data = G.get_edge_data(*edge)
        if edge_data and len(edge_data) > 0:
            print(f"  Edge {edge[0]} -- {edge[1]}: {edge_data}")
            count += 1
            if count >= 5:
                break
    
    if count == 0:
        print("  No edges with attributes found in the sample.")

def analyze_node_relation_patterns(G, sample_size=100):
    """Analyze and display patterns in node relationships."""
    print("\n=== NODE RELATIONSHIP PATTERN ANALYSIS ===")
    
    # Get valid nodes (non-NaN)
    valid_nodes = [n for n in G.nodes() if not (isinstance(n, float) and math.isnan(n))]
    
    # Sample nodes for analysis
    if len(valid_nodes) > sample_size:
        sample_nodes = np.random.choice(valid_nodes, sample_size, replace=False)
    else:
        sample_nodes = valid_nodes
    
    # Get all node attribute keys
    attribute_keys = set()
    for node in sample_nodes:
        attribute_keys.update(G.nodes[node].keys())
    
    # For each attribute, see if it correlates with connection patterns
    print("Analyzing whether node attributes correlate with connection patterns...")
    
    for attr in sorted(attribute_keys):
        # Skip if the attribute is missing for most nodes
        missing_count = sum(1 for node in sample_nodes if attr not in G.nodes[node] or 
                           (isinstance(G.nodes[node][attr], float) and math.isnan(G.nodes[node][attr])))
        if missing_count > len(sample_nodes) * 0.5:  # Skip if missing from more than 50% of nodes
            continue
            
        # Group nodes by attribute value
        value_groups = defaultdict(list)
        for node in sample_nodes:
            if attr in G.nodes[node] and not (isinstance(G.nodes[node][attr], float) and math.isnan(G.nodes[node][attr])):
                value = G.nodes[node][attr]
                value_groups[value].append(node)
        
        # Only analyze groups with enough samples
        valid_groups = {val: nodes for val, nodes in value_groups.items() if len(nodes) >= 5}
        
        if len(valid_groups) >= 2:  # Need at least 2 groups to compare
            print(f"\nAnalyzing connection patterns by attribute: '{attr}'")
            
            # Calculate average degree for each group
            results = []
            for value, nodes in valid_groups.items():
                try:
                    # Calculate average degree
                    degrees = [G.degree(node) for node in nodes]
                    avg_degree = sum(degrees) / len(degrees) if degrees else 0
                    
                    # Count total edges between these nodes (internal edges)
                    # This can be expensive, so limit the calculation if too many nodes
                    if len(nodes) > 50:
                        # Sample for large groups
                        sample_for_edges = np.random.choice(nodes, 50, replace=False)
                        internal_edges = sum(1 for i, u in enumerate(sample_for_edges) 
                                            for v in sample_for_edges[i+1:] 
                                            if G.has_edge(u, v))
                        # Scale up the estimate
                        scaling_factor = (len(nodes) * (len(nodes) - 1)) / (50 * 49)
                        internal_edges = int(internal_edges * scaling_factor)
                    else:
                        internal_edges = sum(1 for i, u in enumerate(nodes) 
                                            for v in nodes[i+1:] 
                                            if G.has_edge(u, v))
                    
                    # Count all edges from these nodes
                    total_edges = sum(degrees)
                    
                    # Calculate homophily: what percentage of edges are to nodes with the same attribute value
                    # Each internal edge is counted twice (once from each endpoint)
                    homophily = (internal_edges * 2 / total_edges) if total_edges > 0 else 0
                    
                    value_str = str(value)
                    if len(value_str) > 20:
                        value_str = value_str[:17] + "..."
                        
                    results.append({
                        "Value": value_str,
                        "Nodes": len(nodes),
                        "Avg Degree": f"{avg_degree:.2f}",
                        "Homophily": f"{homophily:.2f}"
                    })
                except Exception as e:
                    print(f"  Error analyzing group '{value}': {e}")
            
            # Display the results as a table
            if results:
                print(tabulate(results, headers="keys", tablefmt="simple"))
            else:
                print("  No valid results to display")

def analyze_jlpt_level_patterns(G):
    """Analyze patterns related to JLPT levels in the graph."""
    print("\n=== JLPT LEVEL PATTERN ANALYSIS ===")
    
    # Check if old_JLPT is an attribute in the graph
    sample_nodes = [n for n in list(G.nodes())[:100] if not (isinstance(n, float) and math.isnan(n))]
    has_jlpt = any('old_JLPT' in G.nodes[n] for n in sample_nodes)
    
    if not has_jlpt:
        print("old_JLPT attribute not found in graph nodes.")
        return
    
    print("Analyzing patterns related to old_JLPT levels...")
    
    try:
        # Get all nodes with valid old_JLPT data
        jlpt_nodes = {}
        for node in G.nodes():
            if isinstance(node, float) and math.isnan(node):
                continue
            
            if 'old_JLPT' in G.nodes[node]:
                jlpt_value = G.nodes[node]['old_JLPT']
                # Skip NaN JLPT values
                if isinstance(jlpt_value, float) and math.isnan(jlpt_value):
                    continue
                
                # Convert to string for consistency if needed
                level = float(jlpt_value) if isinstance(jlpt_value, (int, float, str)) else jlpt_value
                
                if level not in jlpt_nodes:
                    jlpt_nodes[level] = []
                jlpt_nodes[level].append(node)
        
        if not jlpt_nodes:
            print("No valid JLPT data found in the graph.")
            return
            
        # Print JLPT level distribution
        print("\nJLPT Level Distribution:")
        total_jlpt_nodes = sum(len(nodes) for nodes in jlpt_nodes.values())
        for level, nodes in sorted(jlpt_nodes.items()):
            print(f"  JLPT N{level}: {len(nodes):,} words ({len(nodes)/total_jlpt_nodes*100:.2f}% of JLPT-tagged words)")
        
        # Calculate average degree by JLPT level
        print("\nAverage Degree by JLPT Level:")
        for level, nodes in sorted(jlpt_nodes.items()):
            degrees = [G.degree(node) for node in nodes]
            avg_degree = sum(degrees) / len(degrees) if degrees else 0
            print(f"  JLPT N{level}: {avg_degree:.2f}")
        
        # Analyze connections between JLPT levels (for levels with reasonable numbers of nodes)
        print("\nConnections Between JLPT Levels:")
        level_connections = {}
        total_pairs_checked = 0
        
        # Only analyze levels with a reasonable number of nodes
        valid_levels = {level: nodes for level, nodes in jlpt_nodes.items() if len(nodes) >= 10}
        
        if len(valid_levels) < 2:
            print("  Not enough JLPT levels with sufficient data to analyze connections.")
            return
            
        for level1, nodes1 in sorted(valid_levels.items()):
            level_connections[level1] = {}
            
            # Take a sample if too many nodes
            sample1 = nodes1
            if len(nodes1) > 100:
                sample1 = np.random.choice(nodes1, 100, replace=False)
                
            for level2, nodes2 in sorted(valid_levels.items()):
                # Only calculate for level1 <= level2 to avoid duplicating work
                if level1 <= level2:
                    # Take a sample if too many nodes
                    sample2 = nodes2
                    if len(nodes2) > 100:
                        sample2 = np.random.choice(nodes2, 100, replace=False)
                    
                    # Count edges between samples
                    edge_count = 0
                    pairs_checked = 0
                    
                    # Limit the number of pairs checked for very large levels
                    if len(sample1) * len(sample2) > 10000:
                        # Further subsample for very large combinations
                        subsample1 = np.random.choice(sample1, min(50, len(sample1)), replace=False)
                        subsample2 = np.random.choice(sample2, min(50, len(sample2)), replace=False)
                        
                        # Don't double-count pairs when level1 == level2
                        if level1 == level2:
                            edge_count = sum(1 for i, n1 in enumerate(subsample1) 
                                           for n2 in subsample1[i+1:] 
                                           if G.has_edge(n1, n2))
                            pairs_checked = len(subsample1) * (len(subsample1) - 1) // 2
                        else:
                            edge_count = sum(1 for n1 in subsample1 for n2 in subsample2 if G.has_edge(n1, n2))
                            pairs_checked = len(subsample1) * len(subsample2)
                        
                        # Scale up the estimate
                        if level1 == level2:
                            total_pairs = len(sample1) * (len(sample1) - 1) // 2
                        else:
                            total_pairs = len(sample1) * len(sample2)
                            
                        scaling_factor = total_pairs / pairs_checked if pairs_checked > 0 else 0
                        edge_count = int(edge_count * scaling_factor)
                        pairs_checked = total_pairs
                    else:
                        # For smaller samples, check all pairs
                        if level1 == level2:
                            edge_count = sum(1 for i, n1 in enumerate(sample1) 
                                           for n2 in sample1[i+1:] 
                                           if G.has_edge(n1, n2))
                            pairs_checked = len(sample1) * (len(sample1) - 1) // 2
                        else:
                            edge_count = sum(1 for n1 in sample1 for n2 in sample2 if G.has_edge(n1, n2))
                            pairs_checked = len(sample1) * len(sample2)
                    
                    # Calculate density
                    density = edge_count / pairs_checked if pairs_checked > 0 else 0
                    level_connections[level1][level2] = density
                    total_pairs_checked += pairs_checked
                    
        print(f"  Analyzed approximately {total_pairs_checked:,} potential connections between JLPT levels")
        
        # Print connectivity between levels
        print("\nConnectivity Density Between JLPT Levels:")
        levels = sorted(valid_levels.keys())
        header = ["From\\To"] + [f"N{level}" for level in levels]
        rows = []
        
        for level1 in levels:
            row = [f"N{level1}"]
            for level2 in levels:
                if level2 in level_connections.get(level1, {}):
                    row.append(f"{level_connections[level1][level2]:.6f}")
                elif level1 in level_connections.get(level2, {}):
                    row.append(f"{level_connections[level2][level1]:.6f}")
                else:
                    row.append("N/A")
            rows.append(row)
            
        print(tabulate(rows, headers=header, tablefmt="simple"))
        
    except Exception as e:
        print(f"Error during JLPT level analysis: {e}")
        import traceback
        traceback.print_exc()

def detailed_node_analysis(G, num_nodes=10):
    """Perform detailed analysis of specific high-degree nodes."""
    print(f"\n=== DETAILED ANALYSIS OF TOP {num_nodes} NODES ===")
    
    # Get nodes with highest degree
    valid_nodes = [n for n in G.nodes() if not (isinstance(n, float) and math.isnan(n))]
    node_degrees = [(node, G.degree(node)) for node in valid_nodes]
    top_nodes = sorted(node_degrees, key=lambda x: x[1], reverse=True)[:num_nodes]
    
    print(f"Analyzing the {num_nodes} highest-degree nodes in the graph")
    
    for node, degree in top_nodes:
        print(f"\nDetailed analysis for node: {node} (degree: {degree})")
        
        # Node attributes
        print("  Attributes:")
        for attr, value in sorted(G.nodes[node].items()):
            print(f"    {attr}: {value}")
        
        # Neighbors (relationships)
        neighbors = list(G.neighbors(node))
        print(f"  Connected to {len(neighbors)} nodes")
        
        # Neighbor attribute analysis
        if neighbors:
            # Get all attributes that appear in neighbors
            neighbor_attrs = set()
            for n in neighbors[:min(100, len(neighbors))]:
                neighbor_attrs.update(G.nodes[n].keys())
            
            # For selected attributes, analyze distribution in neighbors
            important_attrs = ['old_JLPT', 'POS'] if all(attr in neighbor_attrs for attr in ['old_JLPT', 'POS']) else list(neighbor_attrs)
            
            for attr in important_attrs[:3]:  # Limit to first 3 attributes
                print(f"  Neighbor {attr} distribution:")
                
                attr_values = []
                for n in neighbors:
                    if attr in G.nodes[n] and not (isinstance(G.nodes[n][attr], float) and math.isnan(G.nodes[n][attr])):
                        attr_values.append(G.nodes[n][attr])
                
                value_counts = Counter(attr_values)
                for val, count in value_counts.most_common(5):
                    val_str = str(val)
                    if len(val_str) > 30:
                        val_str = val_str[:27] + "..."
                    print(f"    {val_str}: {count} occurrences ({count/len(attr_values)*100:.1f}%)")
        
        # Sample of neighbors
        print("  Sample connected words:")
        for i, neighbor in enumerate(sorted(neighbors)[:5]):
            print(f"    {i+1}. {neighbor}")
        if len(neighbors) > 5:
            print(f"    ... and {len(neighbors) - 5} more")

def export_node_data_for_visualization(G, output_file="node_data.json", sample_size=5000):
    """Export node data in a format suitable for external visualization tools."""
    print(f"\n=== EXPORTING NODE DATA FOR VISUALIZATION ===")
    
    # Get valid nodes
    valid_nodes = [n for n in G.nodes() if not (isinstance(n, float) and math.isnan(n))]
    
    # Sample nodes if too many
    if len(valid_nodes) > sample_size:
        print(f"Sampling {sample_size} nodes from {len(valid_nodes)} total nodes.")
        nodes_to_export = set(np.random.choice(valid_nodes, sample_size, replace=False))
    else:
        print(f"Exporting all {len(valid_nodes)} nodes.")
        nodes_to_export = set(valid_nodes)
    
    # Create graph extract
    subgraph = G.subgraph(nodes_to_export).copy()
    
    # Convert to JSON format compatible with visualization tools
    node_data = []
    for node in subgraph.nodes():
        node_info = {
            "id": str(node),
            "label": str(node),
            "degree": subgraph.degree(node),
            "attributes": {}
        }
        
        # Add node attributes
        for attr, value in subgraph.nodes[node].items():
            if isinstance(value, (int, float, str, bool)) and not (isinstance(value, float) and math.isnan(value)):
                node_info["attributes"][attr] = value
        
        node_data.append(node_info)
    
    # Create edge data - using safe edge access
    edge_data = []
    for u, v in subgraph.edges():
        edge_info = {
            "source": str(u),
            "target": str(v),
            "attributes": {}
        }
        
        # Safely get edge attributes
        try:
            edge_attrs = subgraph.get_edge_data(u, v)
            # Only include serializable attributes
            if edge_attrs:
                for attr, value in edge_attrs.items():
                    if isinstance(value, (int, float, str, bool)):
                        if not (isinstance(value, float) and math.isnan(value)):
                            edge_info["attributes"][attr] = value
        except Exception as e:
            # Skip problematic edges
            print(f"  Warning: Skipping edge {u} -- {v} due to error: {e}")
            continue
        
        edge_data.append(edge_info)
    
    # Save to JSON file
    graph_data = {
        "nodes": node_data,
        "edges": edge_data,
        "metadata": {
            "description": "Japanese lexical graph data extract",
            "node_count": len(node_data),
            "edge_count": len(edge_data),
            "creation_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        print(f"Data exported to {output_file} ({len(node_data)} nodes, {len(edge_data)} edges)")
    except Exception as e:
        print(f"Error saving JSON file: {e}")

def main():
    """Main execution function."""
    pickle_path = "G_synonyms_2024_09_18.pickle"
    
    if not os.path.exists(pickle_path):
        print(f"Error: File {pickle_path} not found.")
        sys.exit(1)
    
    print(f"Starting analysis of graph: {pickle_path}")
    print("=" * 80)
    
    # Load the graph
    G = load_graph(pickle_path)
    
    # Define list of analysis functions to run 
    analyses = [
        ("Basic statistics", lambda: basic_graph_stats(G)),
        ("Degree distribution", lambda: degree_distribution(G)),
        ("Node attributes", lambda: analyze_node_attributes(G, sample_size=200)),
        ("Edge attributes", lambda: analyze_edge_attributes(G, sample_size=200)),
        ("Node relationship patterns", lambda: analyze_node_relation_patterns(G, sample_size=200)),
        ("JLPT level patterns", lambda: analyze_jlpt_level_patterns(G)),
        ("Detailed node analysis", lambda: detailed_node_analysis(G, num_nodes=10)),
        ("Data export for visualization", lambda: export_node_data_for_visualization(G, output_file="japanese_graph_data.json", sample_size=3000)),
        ("Centrality analysis", lambda: centrality_analysis(G, sample_size=1000)),
        ("Community detection", lambda: community_detection(G)),
        ("Report generation", lambda: create_report(G))
    ]
    
    # Run each analysis, continuing even if one fails
    for name, func in analyses:
        try:
            print(f"\nRunning analysis: {name}")
            func()
        except Exception as e:
            print(f"Error during {name}: {e}")
            print("Continuing with next analysis...")
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    start_time = time.time()
    try:
        main()
    except Exception as e:
        print(f"Unhandled error in main program: {e}")
        import traceback
        traceback.print_exc()
    finally:
        total_time = time.time() - start_time
        print(f"Total execution time: {total_time:.2f} seconds") 