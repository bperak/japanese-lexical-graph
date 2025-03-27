// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    let Graph;
    let graphData;
    let searchTerm = '';
    let searchAttribute = 'kanji';
    let highlightNodes = new Set();
    let highlightLinks = new Set();
    let hoverNode = null;
    let clickedNode = null;
    let is3D = false;
    let labelSizeMultiplier = 1.5;  // Default size multiplier

    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const focusCheckbox = document.getElementById('focus-checkbox');
    const fitToCanvasBtn = document.getElementById('fit-to-canvas-btn');
    const exactSearchCheckbox = document.getElementById('exact-search-checkbox');
    const dimensionSelect = document.getElementById('dimension-select');
    const labelSizeSlider = document.getElementById('label-size-slider');
    const labelSizeValue = document.getElementById('label-size-value');

    // Add slider event listener
    labelSizeSlider.addEventListener('input', (e) => {
        labelSizeMultiplier = parseFloat(e.target.value);
        labelSizeValue.textContent = `${labelSizeMultiplier}x`;
        if (graphData) {
            initializeGraph(graphData);
        }
    });

    function fetchGraphData(term, attribute = 'kanji', exact = true) {
        const depth = document.getElementById('search-depth').value;
        fetch(`/graph-data?term=${encodeURIComponent(term)}&attribute=${encodeURIComponent(attribute)}&depth=${encodeURIComponent(depth)}&exact=${exact}`)
            .then(response => response.json())
            .then(data => {
                console.log('Fetched graph data:', data);
                graphData = data;
                graphData.nodes.forEach(node => {
                    if (exact) {
                        node.isSearchMatch = (attribute === 'kanji' && node.id.toLowerCase() === term.toLowerCase()) ||
                                             (node[attribute] && node[attribute].toLowerCase() === term.toLowerCase());
                    } else {
                        node.isSearchMatch = (attribute === 'kanji' && node.id.toLowerCase().includes(term.toLowerCase())) ||
                                             (node[attribute] && node[attribute].toLowerCase().includes(term.toLowerCase()));
                    }
                });
                if (Graph) {
                    Graph.graphData(graphData);
                } else {
                    initializeGraph(graphData);
                }
                updateSearchInfo(term, attribute);
            })
            .catch(error => console.error('Error fetching graph data:', error));
    }

    function updateSearchInfo(term, attribute) {
        const searchInfoContent = document.getElementById('search-info-content');
        const searchMatchesContent = document.getElementById('search-matches-content');
        const searchMatchesCard = document.getElementById('search-matches');
        
        searchInfoContent.innerHTML = `
            <p><strong>Total Nodes:</strong> <span>${graphData.nodes.length}</span></p>
            <p><strong>Total Links:</strong> <span>${graphData.links.length}</span></p>
            <p><strong>Last Search:</strong> <span>${term ? `${term} (${attribute})` : 'None'}</span></p>
        `;

        const matchingNodes = graphData.nodes.filter(node => node.isSearchMatch);
        searchMatchesContent.innerHTML = `
            <p><strong>Matching Nodes:</strong> <span>${matchingNodes.length}</span></p>
            <ul>
                ${matchingNodes.map(node => `
                    <li>
                        <strong>Kanji:</strong> <span><a href="#" class="node-link" data-id="${node.id}">${node.id}</a></span><br>
                        <strong>Hiragana:</strong> <span>${node.hiragana || 'N/A'}</span><br>
                        <strong>Translation:</strong> <span>${node.translation || 'N/A'}</span><br>
                        <strong>POS:</strong> <span>${node.POS || 'N/A'}</span><br>
                        <strong>JLPT:</strong> <span>${node.JLPT || 'N/A'}</span>
                    </li>
                `).join('')}
            </ul>
        `;

        // Change background color if there are matching nodes
        if (matchingNodes.length > 0) {
            searchMatchesCard.style.backgroundColor = 'rgba(173, 101, 173, 0.4)'; // Lighter transparent purple
        } else {
            searchMatchesCard.style.backgroundColor = 'rgba(233, 236, 239, 0.6)'; // Gray background
        }

        // Add event listeners for the node links
        document.querySelectorAll('#search-matches-content .node-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const nodeId = e.target.dataset.id;
                searchInput.value = nodeId;
                document.getElementById('search-attribute').value = 'kanji';
                fetchGraphData(nodeId, 'kanji');
            });
        });
    }

    function initializeGraph(data) {
        if (Graph) {
            Graph = null;
        }
        const graphElement = document.getElementById('3d-graph');
        graphElement.innerHTML = '';

        // Add event listener for fit-to-canvas button
        fitToCanvasBtn.addEventListener('click', () => {
            if (is3D) {
                Graph.zoomToFit(400, 50);  // duration=400ms, padding=50px for 3D
            } else {
                Graph.zoomToFit(400, 20);  // less padding for 2D
            }
        });

        if (is3D) {
            Graph = ForceGraph3D()
                (graphElement)
                .graphData(data)
                .backgroundColor('#000000')
                .nodeThreeObject(node => {
                    const sprite = new SpriteText(node.id);
                    sprite.material.depthWrite = false;
                    sprite.color = getNodeColor(node);
                    const degree = getNodeDegree(node, data.links);
                    const minSize = 6 * labelSizeMultiplier;
                    const maxSize = 16 * labelSizeMultiplier;
                    const size = minSize + Math.sqrt(degree) * 0.5;
                    sprite.textHeight = Math.min(size, maxSize);
                    return sprite;
                })
                .nodeColor(getNodeColor)
                .nodeLabel(node => `${node.id}: ${node.translation}`)
                .linkLabel(link => link.synonym_strength ? `Strength: ${link.synonym_strength}` : '')
                .linkColor(getLinkColor)
                .linkWidth(getLinkWidth)
                .onNodeClick(handleNodeClick)
                .onNodeHover(handleNodeHover)
                .onLinkHover(handleLinkHover);

            // Set initial camera position
            Graph.cameraPosition({ x: 0, y: 0, z: 600 });

            // Add some forces for better 3D layout
            Graph.d3Force('charge').strength(-200);
            Graph.d3Force('link').distance(60);
        } else {
            Graph = ForceGraph()
                (graphElement)
                .graphData(data)
                .backgroundColor('#000000')
                .nodeLabel(node => `${node.id}: ${node.translation}`)
                .nodeCanvasObject((node, ctx, globalScale) => {
                    const label = node.id;
                    const degree = getNodeDegree(node, data.links);
                    const minSize = 12 * labelSizeMultiplier;
                    const maxSize = 24 * labelSizeMultiplier;
                    const size = minSize + Math.sqrt(degree) * 0.5;
                    const fontSize = Math.min(size, maxSize)/globalScale;
                    
                    ctx.font = `${fontSize}px Sans-Serif`;
                    const textWidth = ctx.measureText(label).width;
                    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);
                    
                    // Store dimensions for hit detection
                    node.__bckgDimensions = bckgDimensions;
                    
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
                    ctx.fillRect(
                        node.x - bckgDimensions[0] / 2,
                        node.y - bckgDimensions[1] / 2,
                        ...bckgDimensions
                    );
                    
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = getNodeColor(node);
                    ctx.fillText(label, node.x, node.y);
                })
                .nodePointerAreaPaint((node, color, ctx) => {
                    const bckgDimensions = node.__bckgDimensions;
                    if (bckgDimensions) {
                        ctx.fillStyle = color;
                        ctx.fillRect(
                            node.x - bckgDimensions[0] / 2,
                            node.y - bckgDimensions[1] / 2,
                            ...bckgDimensions
                        );
                    }
                })
                .onNodeDragEnd(node => {
                    handleNodeClick(node);
                })
                .linkColor(getLinkColor)
                .linkWidth(getLinkWidth)
                .onNodeClick(handleNodeClick)
                .onNodeHover(handleNodeHover)
                .onLinkHover(handleLinkHover);

            // Center and fit the graph after it's initialized
            setTimeout(() => {
                Graph.zoomToFit(400, 20);
                Graph.d3Force('center', d3.forceCenter(window.innerWidth / 2, window.innerHeight / 2))
                    .d3Force('charge').strength(-200)
                    .d3Force('link').distance(30);
            }, 500);
        }
    }

    function getNodeColor(node) {
        if (node === clickedNode) {
            return 'rgb(255,0,0,1)';
        } else if (highlightNodes.has(node)) {
            return node === hoverNode ? 'rgb(255,100,100,1)' : 'rgb(255,160,0,1)';
        } else if (node.isSearchMatch) {
            return 'purple';
        } else if (node.JLPT) {
            return `hsl(${node.JLPT * 60}, 100%, 50%)`;
        } else {
            return 'rgba(200,200,200,0.8)';
        }
    }

    function getLinkColor(link) {
        if (clickedNode && (link.source === clickedNode || link.target === clickedNode)) {
            return 'rgba(255,255,255,1)';
        } else if (hoverNode && (link.source === hoverNode || link.target === hoverNode)) {
            return 'rgba(255,100,100,1)';
        } else {
            return 'rgba(200,200,200,0.5)';
        }
    }

    function getLinkWidth(link) {
        return (clickedNode && (link.source === clickedNode || link.target === clickedNode)) ||
               (hoverNode && (link.source === hoverNode || link.target === hoverNode)) ? 3 : 1;
    }

    function handleNodeClick(node) {
        if (!node) return;
        
        // Normalize node reference
        const nodeId = node.id || node;
        const graphData = Graph.graphData();
        const actualNode = graphData.nodes.find(n => n.id === nodeId);
        
        if (!actualNode) return;
        
        if (focusCheckbox.checked) {
            if (is3D) {
                const distance = 100;
                const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
                
                Graph.cameraPosition(
                    {
                        x: node.x * distRatio,
                        y: node.y * distRatio,
                        z: node.z * distRatio
                    },
                    node,   // lookAt ({ x, y, z })
                    1000   // ms transition duration
                );
            } else {
                Graph.centerAt(node.x, node.y, 1000);
                Graph.zoom(3, 1000);
            }
        }

        // Update node highlighting
        if (clickedNode === node) {
            clickedNode = null;
            highlightNodes.clear();
            highlightLinks.clear();
        } else {
            clickedNode = node;
            highlightNodeAndNeighbors(node);
        }

        displayNodeInfo(actualNode);
        updateSelectedNodeCardColor(actualNode);
        updateHighlight();
    }

    function updateSelectedNodeCardColor(node) {
        const nodeInfoCard = document.getElementById('node-info');
        const backgroundColor = getNodeColor(node);
        
        // Convert the backgroundColor to rgba format with 0.3 alpha
        let rgba;
        if (backgroundColor.startsWith('rgb')) {
            const rgb = backgroundColor.match(/\d+/g);
            rgba = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 0.3)`;
        } else if (backgroundColor.startsWith('hsl')) {
            const hsl = backgroundColor.match(/\d+/g);
            rgba = `hsla(${hsl[0]}, ${hsl[1]}%, ${hsl[2]}%, 0.3)`;
        } else {
            rgba = backgroundColor; // Fallback to original color if format is unknown
        }
        
        nodeInfoCard.style.backgroundColor = rgba;
        
        // Adjust text color based on background brightness
        const brightness = (parseInt(rgb[0]) * 299 + parseInt(rgb[1]) * 587 + parseInt(rgb[2]) * 114) / 1000;
        nodeInfoCard.style.color = brightness > 125 ? 'black' : 'white';
    }

    function handleNodeHover(node) {
        hoverNode = node;
        if (!node) {
            if (!clickedNode) {
                highlightNodes.clear();
                highlightLinks.clear();
            }
        } else if (node !== clickedNode) {
            highlightNodeAndNeighbors(node);
        }
        updateHighlight();
    }

    function handleLinkHover(link) {
        if (!link) {
            if (!clickedNode && !hoverNode) {
                highlightNodes.clear();
                highlightLinks.clear();
            }
        } else {
            highlightLinks.add(link);
            highlightNodes.add(link.source);
            highlightNodes.add(link.target);
        }
        updateHighlight();
    }

    function highlightNodeAndNeighbors(node) {
        highlightNodes.clear();
        highlightLinks.clear();
        if (node) {
            // Normalize node reference
            const nodeId = node.id || node;
            const graphData = Graph.graphData();
            const actualNode = graphData.nodes.find(n => n.id === nodeId);
            
            if (!actualNode) return;
            
            highlightNodes.add(actualNode);
            Graph.graphData().links.forEach(link => {
                const sourceId = link.source.id || link.source;
                const targetId = link.target.id || link.target;
                if (sourceId === nodeId || targetId === nodeId) {
                    highlightLinks.add(link);
                    highlightNodes.add(graphData.nodes.find(n => n.id === sourceId));
                    highlightNodes.add(graphData.nodes.find(n => n.id === targetId));
                }
            });
        }
    }

    function updateHighlight() {
        Graph
            .nodeColor(Graph.nodeColor())
            .linkColor(Graph.linkColor())
            .linkWidth(Graph.linkWidth());
    }

    function displayNodeInfo(node) {
        const neighbors = getNeighbors(node);
        
        const nodeInfoContent = document.getElementById('node-info-content');
        nodeInfoContent.innerHTML = `
            <ul>
                <li>
                    <strong>Kanji:</strong> <span><a href="#" class="node-link" data-id="${node.id}">${node.id}</a></span><br>
                    <strong>Hiragana:</strong> <span>${node.hiragana || 'N/A'}</span><br>
                    <strong>Translation:</strong> <span>${node.translation || 'N/A'}</span><br>
                    <strong>POS:</strong> <span>${node.POS || 'N/A'}</span><br>
                    <strong>JLPT:</strong> <span>${node.JLPT || 'N/A'}</span>
                </li>
            </ul>
        `;

        const neighborsList = document.getElementById('neighbors-list');
        neighborsList.innerHTML = neighbors.map(neighbor => `
            <li>
                <strong>Kanji:</strong> <span><a href="#" class="node-link" data-id="${neighbor.node.id}">${neighbor.node.id}</a></span><br>
                <strong>Hiragana:</strong> <span>${neighbor.node.hiragana || 'N/A'}</span><br>
                <strong>Translation:</strong> <span>${neighbor.node.translation || 'N/A'}</span><br>
                <strong>Relation Strength:</strong> <span class="relation-strength">${neighbor.strength || 'N/A'}</span>
            </li>
        `).join('');

        document.querySelectorAll('.node-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const nodeId = e.target.dataset.id;
                searchInput.value = nodeId;
                document.getElementById('search-attribute').value = 'kanji';
                fetchGraphData(nodeId, 'kanji');
            });
        });
    }

    function getNeighbors(node) {
        const neighbors = [];
        Graph.graphData().links.forEach(link => {
            if (link.source.id === node.id) {
                neighbors.push({node: link.target, strength: link.synonym_strength});
            } else if (link.target.id === node.id) {
                neighbors.push({node: link.source, strength: link.synonym_strength});
            }
        });

        // Sort neighbors by relation strength in descending order
        neighbors.sort((a, b) => b.strength - a.strength);

        return neighbors;
    }

    searchButton.addEventListener('click', () => {
        searchTerm = searchInput.value;
        searchAttribute = document.getElementById('search-attribute').value;
        const exactSearch = exactSearchCheckbox.checked;
        fetchGraphData(searchTerm, searchAttribute, exactSearch);
    });

    // Update the dimension change handler
    dimensionSelect.addEventListener('change', (e) => {
        is3D = e.target.value === '3d';
        if (Graph) {
            Graph.pauseAnimation();
            Graph = null;
        }
        const graphElement = document.getElementById('3d-graph');
        graphElement.innerHTML = '';
        setTimeout(() => {
            if (graphData) {
                initializeGraph(graphData);
                if (clickedNode) {
                    highlightNodeAndNeighbors(clickedNode);
                    updateHighlight();
                }
            }
        }, 100);
    });

    fetchGraphData('');
});

function getNodeDegree(node, links) {
    if (!node || !links) return 0;
    return links.filter(link => 
        link.source.id === node.id || link.target.id === node.id
    ).length;
}
