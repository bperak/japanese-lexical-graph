from flask import Flask, render_template, jsonify, request
import networkx as nx
import pickle
import ssl

app = Flask(__name__)

# Load the NetworkX graph from pickle file
try:
    filename = 'G_synonyms_2024_09_18.pickle'
    with open(filename, 'rb') as f:
        G = pickle.load(f)

    # Ispis osnovnih informacija o grafu
    print(f"Broj čvorova: {G.number_of_nodes()}")
    print(f"Broj veza: {G.number_of_edges()}")

except Exception as e:
    print(f"Greška pri učitavanju grafa: {e}")

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

    print(f"Returning {len(nodes)} nodes and {len(links)} links")  # Add this line
    return jsonify({'nodes': nodes, 'links': links})

if __name__ == '__main__':
    # Setup SSL context for secure HTTP
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain("/home/Liks/certs/liks.cer", "/home/Liks/certs/liks.key")

    # Run the Flask application with SSL
    # app.run(host='31.147.206.155', port=8001, debug=True, ssl_context=context)
    app.run(host='31.147.206.155', port=8003, debug=True, ssl_context=context)