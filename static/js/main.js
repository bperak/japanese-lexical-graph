// static/js/main.js

// Global variables for access across functions
let graphData = { nodes: [], links: [] };  // Initialize with empty arrays
let Graph;
let clickedNode = null;
let highlightNodes = new Set();
let highlightLinks = new Set();
let hoverNode = null;
let wikidataCache = {};  // Cache for Wikidata results
const geminiCache = {};
const aiGenerationCache = {}; // Cache for AI Generation results
// Visibility toggles for relation types
let showSynonyms = true;
let showAntonyms = true;

document.addEventListener('DOMContentLoaded', function() {
    // Function to handle tab switching
    function setupTabs() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.dataset.tab;
                
                // Remove active class from all buttons and add to clicked button
                tabButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                // Hide all tab content and show the selected one
                tabContents.forEach(content => {
                    const targetId = `${tabName}-tab`;
                    // Add 'active' class only to the matching tab pane, remove from others
                    if (content.id === targetId) {
                        content.classList.add('active');
                    } else {
                        content.classList.remove('active');
                    }
                });
            });
        });
        
        // Activate the first tab by default
        if (tabButtons.length > 0) {
            tabButtons[0].click();
        }
    }
    
    // Initialize tab switching
    setupTabs();
    
// Function to toggle side navigation
function toggleNav() {
    const sideNav = document.getElementById('side-nav');
    if (sideNav.classList.contains('open')) {
        sideNav.style.width = '0';
        sideNav.classList.remove('open');
    } else {
        sideNav.style.width = '300px';
        sideNav.classList.add('open');
    }
}

// Function to toggle accordion sections
function toggleAccordion(element) {
    // Toggle active class
    element.classList.toggle('active');
    
    // Toggle arrow direction
    const arrow = element.querySelector('.arrow');
    if (arrow) {
        arrow.style.transform = arrow.style.transform === 'rotate(180deg)' ? '' : 'rotate(180deg)';
    }
    
    // Toggle content visibility
    const content = element.nextElementSibling;
    if (content.style.maxHeight) {
        content.style.maxHeight = null;
        content.style.padding = '0 20px';
    } else {
        content.style.maxHeight = content.scrollHeight + 'px';
        content.style.padding = '10px 20px';
    }
}

    // Move these functions to the global scope outside the DOMContentLoaded event
    function highlightNodeAndNeighbors(node) {
        // Clear the previous highlight
        highlightNodes.clear();
        highlightLinks.clear();
        
        if (node) {
            // Add the node to the highlight
            highlightNodes.add(node);
            
            // Get the node's neighbors and add them to the highlight
            const neighbors = getNeighbors(node);
            neighbors.nodes.forEach(neighbor => highlightNodes.add(neighbor));
            neighbors.links.forEach(link => highlightLinks.add(link));
        }
    }

    function updateHighlight() {
        if (!Graph) {
            console.error('Graph is not initialized');
            return;
        }
        // Update the node color
        Graph.nodeColor(getNodeColor);
        // Update the link color and width
        Graph.linkColor(getLinkColor);
        Graph.linkWidth(getLinkWidth);
    }

    function getNeighbors(node) {
        // Find all connected nodes and links
        const neighbors = {
            nodes: [],
            links: []
        };
        
        if (!graphData || !graphData.links) return neighbors;
        
        // For each link, check if it connects to the given node
        graphData.links.forEach(link => {
            // Check if link connects to node
            const isConnected = link.source === node || link.target === node;
            
            if (isConnected) {
                // Add the link to neighbors
                neighbors.links.push(link);
                
                // Add the other end of the link to neighbors
                const otherNode = link.source === node ? link.target : link.source;
                if (!neighbors.nodes.includes(otherNode)) {
                    neighbors.nodes.push(otherNode);
                }
            }
        });

        return neighbors;
    }

    function getNodeColor(node) {
        if (node === clickedNode) return '#ff0000';
        if (node === hoverNode) return '#ff8080';
        if (highlightNodes.has(node)) return '#ffff00';
        if (node.isSearchMatch) return '#ff00ff';

        // Color by POS tag or default to white
        const posColors = {
            'noun': '#4CAF50',        // Green
            'verb': '#2196F3',        // Blue
            'adjective': '#FFC107',   // Amber
            'adverb': '#9C27B0',      // Purple
            'pronoun': '#00BCD4',     // Cyan
            'particle': '#FF5722',    // Deep orange
            'auxiliary verb': '#607D8B' // Blue gray
        };
        
        return posColors[node.POS] || '#ffffff';
    }

    function getLinkColor(link) {
        if (highlightLinks.has(link)) {
            return '#ffff00'; // Bright yellow for highlighted links
        }
        
        // First distinguish antonyms (render in bright red)
        if (link.relationship === 'antonym') {
            return '#ff4d4d';
        }
        
        // Synonyms / others – keep gradient based on strength for visual cue of closeness
        const strength = parseFloat(link.synonym_strength || link.weight || 0.5);
        
        // Gradient on dark background: light blue (weak) → magenta (strong)
        const hue = 240 - (strength * 180); // 240 (blue) down to ~60 (magenta-ish)
        return `hsl(${hue}, 80%, 70%)`; // high lightness for visibility
    }

    function getLinkWidth(link) {
        return highlightLinks.has(link) ? 3 : 1.5; // Slightly thicker lines by default
    }

    // Initialize all accordion buttons
    console.log('Initializing accordions');
    document.querySelectorAll('.accordion-header').forEach(header => {
        header.addEventListener('click', function() {
            toggleAccordion(this);
        });
        
        // Add ID if missing
        if (!header.id && header.querySelector('span')) {
            const title = header.querySelector('span').textContent.trim();
            const id = title.toLowerCase().replace(/\s+/g, '-') + '-btn';
            header.id = id;
            console.log(`Added ID to accordion header: ${id}`);
            
            // Add ID to content if missing
            const content = header.nextElementSibling;
            if (content && content.classList.contains('accordion-content') && !content.id) {
                content.id = title.toLowerCase().replace(/\s+/g, '-') + '-content';
                console.log(`Added ID to accordion content: ${content.id}`);
            }
        }
    });

    // Explicitly check for the global THREE instance
    if (typeof window.THREE !== 'undefined') {
        console.log('Using global THREE instance, version:', window.THREE.REVISION);
    } else if (typeof THREE !== 'undefined') {
        // If it exists but not on window, attach it to prevent duplicate loading
        window.THREE = THREE;
        console.log('Attached local THREE to window, version:', THREE.REVISION);
    } else {
        console.error('THREE is not defined. Three.js library may not be loaded correctly.');
        document.getElementById('graph-container').innerHTML = 
            '<div style="color: red; padding: 20px;">Error: Three.js library not loaded correctly. Check console for details.</div>';
    }
    
    let searchTerm = '';
    let searchAttribute = 'kanji';
    let labelSizeMultiplier = 1.5;  // Default size multiplier
    const geminiCache = {};
    let selectedNodes = [];

    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const focusCheckbox = document.getElementById('focus-checkbox');
    const fitToCanvasBtn = document.getElementById('fit-to-canvas-btn');
    const exactSearchCheckbox = document.getElementById('exact-search-checkbox');
    const dimensionSelect = document.getElementById('dimension-select');
    const labelSizeSlider = document.getElementById('label-size-slider');
    const labelSizeValue = document.getElementById('label-size-value');
    const toggleSynonymsChk = document.getElementById('toggle-synonyms');
    const toggleAntonymsChk = document.getElementById('toggle-antonyms');

    // Check WebGL availability
    try {
        let canvas = document.createElement('canvas');
        let gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) {
            console.error('WebGL not supported in this browser.');
            document.getElementById('graph-container').innerHTML = '<div style="color: red; padding: 20px;">Error: WebGL not supported in this browser. Try using Chrome or Firefox.</div>';
        }
    } catch (e) {
        console.error('Error during WebGL initialization:', e);
        document.getElementById('graph-container').innerHTML = '<div style="color: red; padding: 20px;">Error initializing WebGL. See console for details.</div>';
    }

    // Helper function to check if ForceGraph libraries are available
    function checkForForceGraphLibraries() {
        if (typeof ForceGraph3D !== 'function') {
            console.error('ForceGraph3D is not available');
            return false;
        }
        if (typeof ForceGraph !== 'function') {
            console.error('ForceGraph is not available');
            return false;
        }
        return true;
    }

    // Ensure libraries are available before continuing
    if (!checkForForceGraphLibraries()) {
        document.getElementById('graph-container').innerHTML = 
            '<div style="color: red; padding: 20px;">Error: Required libraries not loaded. Please check your internet connection and reload the page.</div>';
    }

    // Add slider event listener only if the slider exists
    if (labelSizeSlider && labelSizeValue) {
        labelSizeSlider.addEventListener('input', (e) => {
            labelSizeMultiplier = parseFloat(e.target.value);
            labelSizeValue.textContent = `${labelSizeMultiplier}x`;
            if (graphData) {
                initializeGraph(graphData);
            }
        });
    }

    // --- Relation visibility toggles ---
    if (toggleSynonymsChk) {
        toggleSynonymsChk.addEventListener('change', (e) => {
            showSynonyms = e.target.checked;
            applyLinkVisibility();
            if (clickedNode) updateNeighborsList(clickedNode);
        });
    }

    if (toggleAntonymsChk) {
        toggleAntonymsChk.addEventListener('change', (e) => {
            showAntonyms = e.target.checked;
            applyLinkVisibility();
            if (clickedNode) updateNeighborsList(clickedNode);
        });
    }

    function applyLinkVisibility() {
        if (!Graph) return;
        Graph.linkVisibility(link => {
            if (link.relationship === 'synonym' && !showSynonyms) return false;
            if (link.relationship === 'antonym' && !showAntonyms) return false;
            return true;
        });
        if (typeof Graph.refresh === 'function') {
            Graph.refresh();
        } else if (typeof Graph.forceEngine === 'function') {
            // For 3D graphs trigger reheat and render
            Graph.forceEngine().alpha(1).restart();
        }
    }

    function fetchGraphData(term, attribute = 'kanji', exact = true) {
        if (!term.trim()) {
            console.log('Empty search term, not fetching data');
            return;
        }
        
        const depth = document.getElementById('search-depth').value;
        console.log(`Fetching graph data: term=${term}, attribute=${attribute}, depth=${depth}, exact=${exact}`);
        
        // Show loading indicator
        const graphContainer = document.getElementById('graph-container');
        graphContainer.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;"><p>Loading graph data...</p></div>';
        
        // Prepare the URL with parameters
        const url = `/graph-data?term=${encodeURIComponent(term)}&attribute=${encodeURIComponent(attribute)}&depth=${depth}&exact=${exact}`;
        
        // Fetch data from API
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Received graph data:', data);
                
                // Check if we have valid data
                if (!data.nodes || data.nodes.length === 0) {
                    console.warn('No nodes found in the response');
                    graphContainer.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;"><p>No matching nodes found.</p></div>';
                    return;
                }
                
                // Process data for visualization - keep it simple
                const processedData = {
                    nodes: data.nodes.map(node => ({
                        ...node,
                        id: node.id || `node-${Math.random().toString(36).substr(2, 9)}`
                    })),
                    links: data.links.map(link => {
                        // Ensure links use string IDs
                        return {
                            ...link,
                            source: typeof link.source === 'object' ? link.source.id : link.source,
                            target: typeof link.target === 'object' ? link.target.id : link.target
                        };
                    })
                };
                
                // Store the data
                graphData = processedData;
                
                // Update search info
                updateSearchInfo(term, attribute);
                
                // Initialize the graph
                initializeGraph(processedData);
                
                // Update search matches
                updateSearchMatches(processedData.nodes, term, attribute);
            })
            .catch(error => {
                console.error('Error fetching graph data:', error);
                graphContainer.innerHTML = `<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
                    <p>Error loading graph data: ${error.message}</p>
                    <p>Please try again with a different search term.</p>
                </div>`;
            });
    }
    
    // Helper function to update search matches
    function updateSearchMatches(nodes, term, attribute) {
        const matchesContainer = document.getElementById('search-matches-content');
        if (!matchesContainer) return;
        
        const matches = nodes.filter(node => 
            (attribute === 'kanji' && node.id && node.id.includes(term)) ||
            (node[attribute] && (
                typeof node[attribute] === 'string' && node[attribute].includes(term) ||
                Array.isArray(node[attribute]) && node[attribute].some(val => val.includes(term))
            ))
        );
        
        if (matches.length > 0) {
            let matchesHtml = '<ul>';
            matches.forEach(match => {
                const hiragana = match.hiragana ? match.hiragana : '';
                const translation = formatTranslation(match.translation);
                matchesHtml += `
                    <li>
                        <div class="match-item">
                            <a class="node-link match-kanji" data-id="${match.id}">${match.id}</a>
                            ${hiragana ? `<span class="match-hiragana">${hiragana}</span>` : ''}
                            <span class="match-translation">${translation}</span>
                        </div>
                    </li>`;
            });
            matchesHtml += '</ul>';
            matchesContainer.innerHTML = matchesHtml;
            
            // Add event listeners to the node links
            document.querySelectorAll('#search-matches-content .node-link').forEach(link => {
                link.addEventListener('click', function() {
                    const nodeId = this.getAttribute('data-id');
                    const node = nodes.find(n => n.id === nodeId);
                    if (node) {
                        handleNodeClick(node);
                    }
                });
            });
                    } else {
            matchesContainer.innerHTML = '<p>No matches found.</p>';
        }
    }

    // New function to fetch Wikidata information
    function fetchWikidataInfo(term) {
        console.log('Fetching Wikidata info for:', term);
        
        // Check cache first
        if (wikidataCache[term]) {
            console.log('Using cached Wikidata info for', term);
            updateWikidataPanel(wikidataCache[term]);
            return;
        }

        // Show loading state
        document.getElementById('wikidata-details').innerHTML = '<div class="loading">Loading Wikidata information...</div>';
        
        // Make API request
        console.log('Sending Wikidata API request for:', term);
        fetch(`/wikidata-info?term=${encodeURIComponent(term)}`)
            .then(response => {
                console.log('Wikidata API response:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Fetched Wikidata data:', data);
                wikidataCache[term] = data;  // Cache the result
                updateWikidataPanel(data);
            })
            .catch(error => {
                console.error('Error fetching Wikidata info:', error);
                document.getElementById('wikidata-details').innerHTML = 
                    `<div class="error">Error loading Wikidata information: ${error.message}</div>`;
            });
    }
    // Make fetchWikidataInfo available in the global scope
    window.fetchWikidataInfo = fetchWikidataInfo;

    // New function to render Wikidata information in the panel
    function updateWikidataPanel(data) {
        console.log('Updating Wikidata panel with data:', data);
        const container = document.getElementById('wikidata-details');
        
        if (!container) {
            console.error('Wikidata details container not found');
            return;
        }
        
        // Handle empty or error cases
        if (!data) {
            container.innerHTML = '<div class="no-data">No Wikidata information available for this term</div>';
            return;
        }
        
        // Handle the case where we get an error object
        if (data.error) {
            container.innerHTML = `<div class="error">Error: ${data.error}</div>`;
            return;
        }
        
        // Handle the case where the data object is empty (no results)
        if (Object.keys(data).length === 0) {
            container.innerHTML = `
                <div class="no-data">
                    No matching entries found in Wikidata for this term. 
                    <p>This may be because:</p>
                    <ul>
                        <li>The term is not in Wikidata's database</li>
                        <li>The term is known by a different name in Wikidata</li>
                    </ul>
                </div>
            `;
            return;
        }

        try {
            let html = '';
            
            // Process each entity
            for (const [itemUrl, details] of Object.entries(data)) {
                // Check if this is from an English fallback search
                const isFallback = details.is_english_fallback;
                
                // Add a notice about the fallback if needed
                if (isFallback) {
                    html += `
                        <div class="wikidata-fallback-notice">
                            <i>No Wikidata results found for Japanese term. Showing results from English translation instead.</i>
                        </div>
                    `;
                }
                
                // Title section with name and definition
                html += `
                    <div class="wikidata-item">
                        <h4>${details.Naziv || 'Unnamed Entity'}</h4>
                        <div class="definition">${details.Definicija || 'No definition available'}</div>
                `;
                
                // Basic info section
                let hasBasicInfo = false;
                html += '<div class="wikidata-section">';
                html += '<div class="wikidata-section-title">Classification</div>';
                
                if (details["Instance of"] && details["Instance of"].length > 0) {
                    hasBasicInfo = true;
                    html += `<div class="wikidata-property">
                        <span class="wikidata-property-name">Instance of:</span> 
                        ${details["Instance of"].join(', ')}
                    </div>`;
                }
                
                if (details["Subclass of"] && details["Subclass of"].length > 0) {
                    hasBasicInfo = true;
                    html += `<div class="wikidata-property">
                        <span class="wikidata-property-name">Subclass of:</span> 
                        ${details["Subclass of"].join(', ')}
                    </div>`;
                }
                
                if (!hasBasicInfo) {
                    html += '<div class="no-data">No classification information available</div>';
                }
                html += '</div>'; // Close classification section
                
                // Relations section
                let hasRelations = false;
                html += '<div class="wikidata-section">';
                html += '<div class="wikidata-section-title">Relations</div>';
                
                if (details["Has part"] && details["Has part"].length > 0) {
                    hasRelations = true;
                    html += `<div class="wikidata-property">
                        <span class="wikidata-property-name">Has part:</span> 
                        ${details["Has part"].join(', ')}
                    </div>`;
                }
                
                if (details["Part of"] && details["Part of"].length > 0) {
                    hasRelations = true;
                    html += `<div class="wikidata-property">
                        <span class="wikidata-property-name">Part of:</span> 
                        ${details["Part of"].join(', ')}
                    </div>`;
                }
                
                if (!hasRelations) {
                    html += '<div class="no-data">No relation information available</div>';
                }
                html += '</div>'; // Close relations section
                
                // Linguistic properties section
                let hasLinguisticInfo = false;
                html += '<div class="wikidata-section">';
                html += '<div class="wikidata-section-title">Linguistic Information</div>';
                
                if (details["Synonyms"] && details["Synonyms"].length > 0) {
                    hasLinguisticInfo = true;
                    html += `<div class="wikidata-property">
                        <span class="wikidata-property-name">Synonyms:</span> 
                        ${details["Synonyms"].join(', ')}
                    </div>`;
                }
                
                if (details["Pronunciation"] && details["Pronunciation"].length > 0) {
                    hasLinguisticInfo = true;
                    html += `<div class="wikidata-property">
                        <span class="wikidata-property-name">Pronunciation:</span> 
                        ${details["Pronunciation"].join(', ')}
                    </div>`;
                }
                
                if (details["Etymology"] && details["Etymology"].length > 0) {
                    hasLinguisticInfo = true;
                    html += `<div class="wikidata-property">
                        <span class="wikidata-property-name">Etymology:</span> 
                        ${details["Etymology"].join(', ')}
                    </div>`;
                }
                
                if (details["Usage"] && details["Usage"].length > 0) {
                    hasLinguisticInfo = true;
                    html += `<div class="wikidata-property">
                        <span class="wikidata-property-name">Usage Examples:</span>
                        <ul>
                            ${details["Usage"].map(u => `<li>${u}</li>`).join('')}
                        </ul>
                    </div>`;
                }
                
                if (!hasLinguisticInfo) {
                    html += '<div class="no-data">No linguistic information available</div>';
                }
                html += '</div>'; // Close linguistic section
                
                // Image section
                if (details.Slika) {
                    html += `
                        <div class="wikidata-section">
                            <div class="wikidata-section-title">Images</div>
                            <div class="wikidata-image-container">
                                <img src="${details.Slika}" alt="${details.Naziv}" class="wikidata-image">
                                <div class="wikidata-image-caption">${details.Naziv}</div>
                            </div>
                        </div>`;
                }
                
                // Add link to Wikidata
                html += `
                    <div class="wikidata-section">
                        <div class="wikidata-property">
                            <span class="wikidata-property-name">Wikidata URL:</span>
                            <a href="${itemUrl}" target="_blank" rel="noopener noreferrer" class="external-link">${itemUrl}</a>
                        </div>
                    </div>`;
                
                html += '</div>'; // Close wikidata-item
            }
            
            container.innerHTML = html;
            console.log('Wikidata panel updated successfully');
        } catch (error) {
            console.error('Error rendering Wikidata panel:', error);
            container.innerHTML = `<div class="error">Error rendering Wikidata information: ${error.message}</div>`;
        }
    }

    function fetchGeminiInfo(nodeId) {
        console.log('Fetching Gemini info for node:', nodeId);
        
        // Show loading state in the new gemini-details element
        document.getElementById('gemini-details').innerHTML = '<div class="loading">Loading AI analysis...</div>';
        
        // Check cache first
        if (geminiCache[nodeId]) {
            console.log('Using cached Gemini info for node:', nodeId);
            updateGeminiPanel(geminiCache[nodeId]);
            return;
        }
        
        // Make API request
        console.log('Sending enhanced-node API request for:', nodeId);
        fetch(`/enhanced-node?id=${encodeURIComponent(nodeId)}`)
            .then(response => {
                console.log('Enhanced node API response:', response.status, response.statusText);
                // Always get the JSON even if not 200, since we have fallback content
                return response.json().catch(error => {
                    console.error('Error parsing JSON response:', error);
                    // If we can't parse JSON at all, create a minimal error object
                    return { 
                        error: `Failed to parse response: ${error.message}`,
                        status: response.status
                    };
                });
            })
            .then(data => {
                console.log('Received enhanced node data:', data);
                // Debug - print full data structure 
                console.log('DATA STRUCTURE:', JSON.stringify(data, null, 2));
                
                // Check if we have ai_enhanced (old structure) instead of direct explanation (new structure)
                if (!data.explanation && data.ai_enhanced) {
                    console.log('Found ai_enhanced in response, converting to new format');
                    // Convert old structure to new structure
                    data = {
                        id: data.id,
                        explanation: data.ai_enhanced.explanation || {},
                        // Keep other properties
                        ...data
                    };
                }
                
                // Cache the result
                geminiCache[nodeId] = data;
                updateGeminiPanel(data);
            })
            .catch(error => {
                console.error('Error fetching Gemini info:', error);
                // Display user-friendly error in the panel
                document.getElementById('gemini-details').innerHTML = `
                    <div class="error">
                        <p>Error loading AI analysis: ${error.message}</p>
                        <p>Basic information is still available in the node info panel.</p>
                    </div>`;
            });
    }
    // Make fetchGeminiInfo available in the global scope
    window.fetchGeminiInfo = fetchGeminiInfo;

    function updateGeminiPanel(data) {
        const geminiDetails = document.getElementById('gemini-details');
        
        if (!geminiDetails) {
            console.error('Gemini details element not found');
            return;
        }
        
        // Log the data we received for debugging
        console.log('Gemini data received:', data);
        
        if (data.error) {
            geminiDetails.innerHTML = `<div class="error-message">${data.error}</div>`;
            return;
        }
        
        // New structure directly provides explanation and relationships
        const explanation = data.explanation || {};
        
        // Check if we have any useful data
        if (!explanation || Object.keys(explanation).length === 0) {
            // If the response has raw_response, display it for debugging
            if (explanation && explanation.raw_response) {
                geminiDetails.innerHTML = `
                    <div class="no-data">Could not parse AI analysis, but here's the raw response:</div>
                    <div class="raw-response">${explanation.raw_response}</div>
                `;
                return;
            }
            
            geminiDetails.innerHTML = '<div class="no-ai-analysis">No AI analysis available for this term</div>';
            return;
        }
        
        let html = '<div class="gemini-content">';
        
        // Add the Japanese term and basic info
        if (data.id) {
            html += `<h4>${data.id}</h4>`;
        }
        
        // Add explanation section
        html += '<div class="gemini-section">';
        html += '<div class="gemini-section-title">AI Analysis</div>';
        
        if (explanation.error) {
            html += `<div class="error-message">${explanation.error}</div>`;
            
            // If we have a raw response, show it for debugging
            if (explanation.raw_response) {
                html += `
                    <div class="raw-response">
                        <strong>Raw API Response:</strong>
                        <pre>${explanation.raw_response}</pre>
                    </div>
                `;
            }
        } else {
            if (explanation.overview) {
                html += `<div class="gemini-item">${explanation.overview}</div>`;
            }
            
            if (explanation.cultural_context && explanation.cultural_context !== "N/A") {
                html += `
                    <div class="gemini-item">
                        <strong>Cultural Context:</strong>
                        <div>${explanation.cultural_context}</div>
                    </div>
                `;
            }
            
            if (explanation.usage_examples && explanation.usage_examples.length > 0) {
                html += `<div class="gemini-item"><strong>Usage Examples:</strong></div>`;
                
                explanation.usage_examples.forEach(example => {
                    html += `<div class="usage-example">${example}</div>`;
                });
            }
            
            if (explanation.nuances && explanation.nuances !== "N/A") {
                html += `
                    <div class="gemini-item">
                        <strong>Nuances:</strong>
                        <div>${explanation.nuances}</div>
                    </div>
                `;
            }
            
            // Add model info if available
            if (explanation._model_used) {
                html += `
                    <div class="gemini-item model-info">
                        <small>Generated using model: ${explanation._model_used}</small>
                    </div>
                `;
            }
            
            // Removed raw response accordion
            
        }
        
        html += '</div>'; // Close gemini-section
        
        // If we have relationship data, add it
        if (data.relationships && data.relationships.length > 0) {
            html += '<div class="gemini-section">';
            html += '<div class="gemini-section-title">Relationship Analysis</div>';
            
            // Get the first relationship
            const firstRelationship = data.relationships[0];
            const relationship = firstRelationship.analysis || {};
            const relatedTerm = firstRelationship.term2;
            
            if (relatedTerm) {
                html += `<div class="gemini-item"><strong>Related to:</strong> ${relatedTerm}</div>`;
            }
            
            if (relationship.relationship) {
                html += `<div class="gemini-item">${relationship.relationship}</div>`;
            }
            
            if (relationship.differences) {
                html += `
                    <div class="gemini-item">
                        <strong>Key Differences:</strong>
                        <div>${relationship.differences}</div>
                    </div>
                `;
            }
            
            if (relationship.similarity_score !== undefined) {
                html += `
                    <div class="gemini-item">
                        <strong>Similarity Score:</strong>
                        <div class="similarity-score">${relationship.similarity_score}/100</div>
                    </div>
                `;
            }
            
            html += '</div>'; // Close gemini-section
        }
        
        html += '</div>'; // Close gemini-content
        
        geminiDetails.innerHTML = html;
    }

    function analyzeSelectedNodes() {
        if (selectedNodes.length !== 2) {
            alert('Please select exactly 2 nodes to analyze');
            return;
        }
        
        const term1 = selectedNodes[0].japanese;
        const term2 = selectedNodes[1].japanese;
        
        if (!term1 || !term2) {
            alert('Both selected nodes must have Japanese terms');
            return;
        }
        
        // Show loading state
        document.getElementById('gemini-info').innerHTML = 
            '<div class="loading">Analyzing relationship between terms...</div>';
        
        // Expand the accordion if it's not already expanded
        const aiInfoContent = document.getElementById('ai-info-content');
        if (aiInfoContent.style.maxHeight !== aiInfoContent.scrollHeight + 'px') {
            document.getElementById('ai-info-btn').click();
        }
        
        // Make API request
        fetch(`/gemini-analyze?term1=${encodeURIComponent(term1)}&term2=${encodeURIComponent(term2)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                updateComparisonPanel(data, term1, term2);
            })
            .catch(error => {
                console.error('Error analyzing relationship:', error);
                document.getElementById('gemini-info').innerHTML = 
                    '<div class="error">Error analyzing relationship</div>';
            });
    }

    function updateComparisonPanel(data, term1, term2) {
        if (data.error) {
            document.getElementById('gemini-info').innerHTML = 
                `<div class="error">${data.error}</div>`;
            return;
        }
        
        const analysis = data.analysis || {};
        
        let html = `
            <h4>Comparison: ${term1} vs ${term2}</h4>
        `;
        
        if (analysis.error) {
            html += `<div class="error">${analysis.error}</div>`;
        } else {
            if (analysis.relationship) {
                html += `
                    <div class="property">
                        <strong>Relationship:</strong>
                        <div>${analysis.relationship}</div>
                    </div>
                `;
            }
            
            if (analysis.differences) {
                html += `
                    <div class="property">
                        <strong>Key Differences:</strong>
                        <div>${analysis.differences}</div>
                    </div>
                `;
            }
            
            if (analysis.usage_contexts) {
                html += `
                    <div class="property">
                        <strong>Usage Contexts:</strong>
                        <div>${analysis.usage_contexts}</div>
                    </div>
                `;
            }
            
            if (analysis.similarity_score !== undefined) {
                html += `
                    <div class="property">
                        <strong>Similarity Score:</strong>
                        <div class="similarity-score">${analysis.similarity_score}/100</div>
                        <div class="progress" style="height: 6px; margin-top: 5px;">
                            <div class="progress-bar bg-primary" role="progressbar" 
                                 style="width: ${analysis.similarity_score}%;" 
                                 aria-valuenow="${analysis.similarity_score}" aria-valuemin="0" aria-valuemax="100">
                            </div>
                        </div>
                    </div>
                `;
            }
        }
        
        document.getElementById('gemini-info').innerHTML = html;
    }

    function updateSearchInfo(term, attribute) {
        const searchInfoContainer = document.getElementById('search-info');
        if (!searchInfoContainer) return;
        
        // Update the search info header
        const searchInfoHeader = document.createElement('h4');
        searchInfoHeader.textContent = 'Search Information';
        
        const totalNodes = graphData.nodes.length;
        const totalLinks = graphData.links.length;
        
        const searchInfoContent = document.createElement('div');
        searchInfoContent.innerHTML = `
            <p><strong>Total Nodes:</strong> <span>${totalNodes}</span></p>
            <p><strong>Total Links:</strong> <span>${totalLinks}</span></p>
            <p><strong>Search Term:</strong> <span>${term}</span></p>
            <p><strong>Search Field:</strong> <span>${attribute}</span></p>
        `;
        
        // Clear previous content and append new content
        searchInfoContainer.innerHTML = '';
        searchInfoContainer.appendChild(searchInfoHeader);
        searchInfoContainer.appendChild(searchInfoContent);
    }

    function initializeGraph(data) {
        console.log('Initializing graph with data:', data);
        
        // Store data in global variable for consistent access
        // This is crucial for other functions that need access to the graph data
        window.graphData = data;
        console.log('Stored graph data in window.graphData');
        
        // Get the container
        const graphContainer = document.getElementById('graph-container');
        
        // Clear previous graph
        graphContainer.innerHTML = '';
        
        // Create a new element for the graph
        const graphEl = document.createElement('div');
        graphEl.id = '3d-graph';
        graphEl.style.width = '100%';
        graphEl.style.height = '100%';
        graphContainer.appendChild(graphEl);
        
        // Check if we have valid data
        if (!data || !data.nodes || !data.links) {
            console.error('Invalid graph data provided');
            graphContainer.innerHTML = '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;"><p>No data available</p></div>';
            return null;
        }
        
        // Determine if we're using 2D or 3D
        const is3D = document.getElementById('dimension-select').value === '3d';
        console.log(`Initializing ${is3D ? '3D' : '2D'} graph with ${data.nodes.length} nodes and ${data.links.length} links`);
        
        try {
            let graph;
            
            if (is3D) {
                // Simple 3D Force Graph initialization
                if (typeof ForceGraph3D !== 'function') {
                    throw new Error('3D Force Graph library not loaded');
                }
                
                graph = ForceGraph3D()
                    (graphEl)
                    .nodeId('id')
                .graphData(data)
                    .backgroundColor('#1a1a1a') // Set background color
                    .nodeLabel(node => {
                        let label = node.id || '';
                        if (node.english && node.english.length) {
                            label += ` (${Array.isArray(node.english) ? node.english[0] : node.english})`;
                        }
                        return label;
                })
                .nodeColor(getNodeColor)
                .linkColor(getLinkColor)
                .linkWidth(getLinkWidth)
                    .nodeRelSize(6)
                    .linkDirectionalParticles(2) // Add particles for better visibility
                    .linkDirectionalParticleWidth(1.5)
                    .nodeThreeObject(node => {
                        // Create a text sprite for better readability
                        const sprite = new SpriteText(node.id);
                        sprite.color = '#ffffff';
                        sprite.textHeight = 4 * labelSizeMultiplier;
                        sprite.backgroundColor = 'rgba(0,0,0,0.2)';
                        sprite.padding = 2;
                        return sprite;
                    })
                    .onNodeClick(node => {
                        console.log('Node clicked in 3D graph:', node.id);
                        handleNodeClick(node);
                    })
                .onNodeHover(handleNodeHover)
                .onLinkHover(handleLinkHover);

                // Set camera position
                graph.cameraPosition({ z: 300 });
        } else {
                // 2D Force Graph
                if (typeof ForceGraph !== 'function') {
                    throw new Error('2D Force Graph library not loaded');
                }
                
                graph = ForceGraph()
                    (graphEl)
                    .nodeId('id')
                .graphData(data)
                    .backgroundColor('#1a1a1a') // Set background color
                    .nodeLabel(node => {
                        let label = node.id || '';
                        if (node.english && node.english.length) {
                            label += ` (${Array.isArray(node.english) ? node.english[0] : node.english})`;
                        }
                        return label;
                    })
                    .nodeColor(getNodeColor)
                    .linkColor(getLinkColor)
                    .linkWidth(getLinkWidth)
                    .nodeRelSize(6)
                    .linkDirectionalParticles(2) // Add particles for better visibility
                    .linkDirectionalParticleWidth(1.5)
                .nodeCanvasObject((node, ctx, globalScale) => {
                        // Draw node
                    const label = node.id;
                        const fontSize = 12 * labelSizeMultiplier / globalScale;
                    ctx.font = `${fontSize}px Sans-Serif`;
                    const textWidth = ctx.measureText(label).width;
                        const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.4);
                        
                        // Node circle
                        ctx.fillStyle = getNodeColor(node);
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI);
                        ctx.fill();
                        
                        // Text background
                        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
                    ctx.fillRect(
                        node.x - bckgDimensions[0] / 2,
                            node.y - bckgDimensions[1] / 2 - 10,
                            bckgDimensions[0],
                            bckgDimensions[1]
                    );
                    
                        // Text
                        ctx.fillStyle = '#ffffff';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                        ctx.fillText(label, node.x, node.y - 10);
                    })
                    .onNodeClick(node => {
                        console.log('Node clicked in 2D graph:', node.id);
                        handleNodeClick(node);
                    })
                .onNodeHover(handleNodeHover)
                .onLinkHover(handleLinkHover);
            }
            
            console.log('Graph initialized successfully');
            
            // Store the graph instance globally for easier access
            window.graph = graph;
            Graph = graph; // Keep for backward compatibility
            window.currentGraph = graph; // Keep for backward compatibility
            
            console.log('Graph instance stored in window.graph');
            
            // Apply current visibility settings
            applyLinkVisibility();
            
            // Test if event handlers are properly attached
            console.log('Testing event handlers:');
            console.log('- onNodeClick handler:', typeof graph.onNodeClick);
            
            // Add fit-to-canvas functionality
            document.getElementById('fit-to-canvas-btn').addEventListener('click', () => {
                if (graph.zoomToFit) {
                    graph.zoomToFit(400, 50);
                } else if (is3D && graph.cameraPosition) {
                    graph.cameraPosition({ x: 0, y: 0, z: 300 }, { x: 0, y: 0, z: 0 }, 1000);
                }
            });
            
            // Fit graph to canvas after initialization
            setTimeout(() => {
                if (graph.zoomToFit) {
                    graph.zoomToFit(400, 50);
                }
            }, 500);
            
            return graph;
        } catch (error) {
            console.error('Error initializing graph:', error);
            graphContainer.innerHTML = `
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
                    <p>Error initializing graph visualization: ${error.message}</p>
                    <p>Please try refreshing the page or using a different browser.</p>
                </div>
            `;
            return null;
        }
    }

    function handleNodeClick(node) {
        console.log('Node clicked:', node);
        
        try {
            // Update node info panel
            console.log('Updating node info...');
            updateNodeInfo(node);
            
            // Get node links for the neighbors list
            console.log('Finding node links...');
            const nodeLinks = graphData.links.filter(link => {
                // Handle both object and string reference formats
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                return sourceId === node.id || targetId === node.id;
            });
            
            console.log(`Found ${nodeLinks.length} links for node ${node.id}`);
            
            // Update neighbors list
            console.log('Updating neighbors list...');
            updateNeighborsList(node, nodeLinks);
            
            // Highlight the selected node in the graph
            console.log('Highlighting node and neighbors...');
            highlightNodeAndNeighbors(node);
            updateHighlight();
            
            // Update current selected node
            clickedNode = node;
            
            // Open the combined sidebar if it's not already open
            console.log('Opening combined sidebar...');
            const combinedSidebar = document.getElementById('combined-sidebar');
            if (combinedSidebar) {
                if (!combinedSidebar.classList.contains('open')) {
                    combinedSidebar.classList.add('open');
                    // Also update the arrow
                    const arrow = combinedSidebar.querySelector('.arrow');
                    if (arrow) {
                        arrow.style.transform = 'rotate(180deg)';
                    }
                }
                
                // Fetch data for both tabs
                console.log('Fetching Gemini info for:', node.id);
                fetchGeminiInfo(node.id);
                
                console.log('Fetching Wikidata info for:', node.id);
                fetchWikidataInfo(node.id);
        } else {
                console.error('Combined sidebar element not found');
            }
            
            console.log('Node click handling completed successfully');
        } catch (error) {
            console.error('Error in handleNodeClick:', error);
        }
    }

    function updateNeighborsPanel(node) {
        const neighborsInfo = document.getElementById('neighbors-info');
        if (!neighborsInfo) return;
        
        let neighborsHtml = '<h4>Neighbors</h4>';
        
        // Get the current graph instance
        const graph = window.currentGraph;
        if (!graph) {
            neighborsInfo.innerHTML = '<p>Graph not initialized</p>';
            return;
        }
        
        try {
            // Get neighbors using the graph's API
            let neighbors = [];
            
            if (typeof graph.neighbors === 'function') {
                // For ForceGraph3D
                neighbors = [...graph.neighbors(node.index)]
                    .map(neighborIndex => {
                        const neighborId = graph.nodeId(neighborIndex);
                        const neighbor = graph.graphData().nodes.find(n => n.id === neighborId);
                        const link = graph.getLink(node.index, neighborIndex);
                        return { 
                            neighbor, 
                            weight: link ? (link.weight || link.synonym_strength || 1) : 1 
                        };
                    });
            } else if (graph.graphData) {
                // Fallback: manually find neighbors from links
                const links = graph.graphData().links || [];
                const nodes = graph.graphData().nodes || [];
                
                links.forEach(link => {
                    let neighborId, weight;
                    
                    if (link.source === node.id || link.source.id === node.id) {
                        neighborId = link.target.id || link.target;
                        weight = link.weight || link.synonym_strength || 1;
                    } else if (link.target === node.id || link.target.id === node.id) {
                        neighborId = link.source.id || link.source;
                        weight = link.weight || link.synonym_strength || 1;
                    }
                    
                    if (neighborId) {
                        const neighbor = nodes.find(n => n.id === neighborId);
                        if (neighbor) {
                            neighbors.push({ neighbor, weight });
                        }
                    }
                });
            }
            
            // Sort neighbors by weight
            neighbors.sort((a, b) => b.weight - a.weight);
            
            if (neighbors.length) {
                neighborsHtml += '<ul>';
                neighbors.forEach(({ neighbor, weight }) => {
                    const label = neighbor.japanese || neighbor.id || 'Unknown';
                    neighborsHtml += `
                        <li>
                            <a class="node-link" data-id="${neighbor.id}">${label}</a>
                            ${neighbor.english && neighbor.english.length ? 
                                `<span class="translation">(${Array.isArray(neighbor.english) ? neighbor.english[0] : neighbor.english})</span>` : ''}
                            ${neighbor.POS ? `<span class="pos">${neighbor.POS}</span>` : ''}
                            <span class="relation-strength">${typeof weight === 'number' ? weight.toFixed(2) : weight}</span>
                        </li>
                    `;
                });
                neighborsHtml += '</ul>';
        } else {
                neighborsHtml += '<p>No neighbors found</p>';
            }
        } catch (e) {
            console.error('Error getting neighbors:', e);
            neighborsHtml += `<p>Error: ${e.message}</p>`;
        }
        
        neighborsInfo.innerHTML = neighborsHtml;
        
        // Add event listeners to neighbor links
        document.querySelectorAll('.node-link').forEach(link => {
            link.addEventListener('click', function() {
                const neighborId = this.getAttribute('data-id');
                
                if (!graph || !graph.graphData) return;
                
                const neighborNode = graph.graphData().nodes.find(n => n.id === neighborId);
                if (neighborNode) {
                    // Center the graph on this node
                    if (graph.centerAt) {
                        graph.centerAt(
                            neighborNode.x,
                            neighborNode.y,
                            neighborNode.z || 0,
                            1000
                        );
                        
                        if (graph.zoom) {
                            graph.zoom(1.5, 1000);
                        }
                    }
                    
                    // Select the node
                    setTimeout(() => {
                        if (graph.emitParticle) {
                            graph.emitParticle(neighborNode);
                        }
                        handleNodeClick(neighborNode);
                    }, 1100);
                }
            });
        });
    }

    function handleNodeHover(node) {
        // Update highlight based on hovered node
        hoverNode = node || null;
        highlightNodes.clear();
        highlightLinks.clear();
        
        if (node) {
            // Create tooltip with all node attributes
            let tooltipContent = `<div class="node-tooltip">`;
            tooltipContent += `<h4>${node.id}</h4>`;
            
            // Iterate through all node attributes
            for (const [key, value] of Object.entries(node)) {
                // Skip id as it's already in the header, and skip internal properties
                if (key !== 'id' && key !== 'x' && key !== 'y' && key !== 'z' && key !== 'vx' && key !== 'vy' && key !== 'vz' && key !== 'index' && key !== 'fx' && key !== 'fy' && key !== 'fz') {
                    let displayValue = value;
                    
                    // Special handling for translation objects
                    if (key === 'translation') {
                        displayValue = formatTranslation(value);
                    }
                    
                    // Format arrays nicely
                    if (Array.isArray(value)) {
                        displayValue = value.join(', ');
                    }
                    
                    // Skip empty values or undefined
                    if (displayValue === undefined || displayValue === null || displayValue === '') {
                        continue;
                    }
                    
                    tooltipContent += `<p><strong>${key}:</strong> <span>${displayValue}</span></p>`;
                }
            }
            
            tooltipContent += `</div>`;
            
            // Create or update tooltip element
            let tooltip = document.getElementById('node-tooltip');
            if (!tooltip) {
                tooltip = document.createElement('div');
                tooltip.id = 'node-tooltip';
                document.body.appendChild(tooltip);
            }
            
            tooltip.innerHTML = tooltipContent;
            tooltip.style.display = 'block';
            
            // Position tooltip near mouse
            document.onmousemove = function(e) {
                tooltip.style.left = (e.pageX + 15) + 'px';
                tooltip.style.top = (e.pageY + 15) + 'px';
            };
            
            // Highlight the node and its links
            highlightNodeAndNeighbors(node);
        } else {
            // Hide tooltip when not hovering
            const tooltip = document.getElementById('node-tooltip');
            if (tooltip) {
                tooltip.style.display = 'none';
            }
            document.onmousemove = null;
        }
        
        updateHighlight();
    }

    function handleLinkHover(link) {
        // When hovering a link, clear and set highlightLinks
                highlightLinks.clear();
        if (link) highlightLinks.add(link);
        
        // Update the visualization
        updateHighlight();
        
        return true;
    }

    function displayNodeInfo(node) {
        if (!node) return;
        
        const nodeInfoContent = document.getElementById('node-info-content');
        const neighborsList = document.getElementById('neighbors-list');
        
        // Display basic node information
        nodeInfoContent.innerHTML = `
            <div class="node-info-section">
                <p><strong>Kanji:</strong> <span>${node.id}</span></p>
                <p><strong>Hiragana:</strong> <span>${node.hiragana || 'N/A'}</span></p>
                <p><strong>Translation:</strong> <span>${formatTranslation(node.translation)}</span></p>
                <p><strong>POS:</strong> <span>${node.POS || 'N/A'}</span></p>
                <p><strong>JLPT:</strong> <span>${node.JLPT || 'N/A'}</span></p>
            </div>
        `;
        
        // Get and display node's neighbors
        const neighbors = getNeighbors(node);
        
        // Sort neighbors by relationship strength and then by ID
        const sortedNeighbors = [...neighbors.nodes].sort((a, b) => {
            // First try to sort by synonym_strength (high to low)
            const linkA = graphData.links.find(l => 
                (l.source === node && l.target === a) || (l.source === a && l.target === node)
            );
            const linkB = graphData.links.find(l => 
                (l.source === node && l.target === b) || (l.source === b && l.target === node)
            );
            
            const strengthA = linkA && linkA.synonym_strength ? parseFloat(linkA.synonym_strength) : 0;
            const strengthB = linkB && linkB.synonym_strength ? parseFloat(linkB.synonym_strength) : 0;
            
            if (strengthA !== strengthB) {
                return strengthB - strengthA; // Descending order
            }
            
            // If strengths are equal, sort by id
            return a.id.localeCompare(b.id);
        });
        
        // Display neighbors
        neighborsList.innerHTML = sortedNeighbors.length > 0
            ? sortedNeighbors.map(neighbor => {
                // Find the link between node and neighbor
                const link = graphData.links.find(l => 
                    (l.source === node && l.target === neighbor) || (l.source === neighbor && l.target === node)
                );
                
                const strength = link && link.synonym_strength 
                    ? `<span class="synonym-strength">(${link.synonym_strength})</span>` 
                    : '';
                
                return `
                    <div class="neighbor-item">
                        <a href="#" class="node-link" data-id="${neighbor.id}">${neighbor.id}</a> 
                        ${strength}
                        <div class="neighbor-details">
                            ${neighbor.translation ? `<span class="translation">${formatTranslation(neighbor.translation)}</span>` : ''}
                            ${neighbor.POS ? `<span class="pos">${neighbor.POS}</span>` : ''}
                        </div>
                    </div>
                `;
            }).join('')
            : '<p>No neighbors found.</p>';
        
        // Add event listeners for the neighbor links
        document.querySelectorAll('#neighbors-list .node-link').forEach(link => {
            link.addEventListener('click', function() {
                e.preventDefault();
                const nodeId = e.target.dataset.id;
                const clickedNeighbor = graphData.nodes.find(n => n.id === nodeId);
                if (clickedNeighbor) {
                    handleNodeClick(clickedNeighbor);
                }
            });
        });
    }

    function getNodeDegree(node, links) {
        if (!links) return 0;
        
        // Count the number of links connected to the node
        return links.filter(link => 
            (link.source === node || (link.source.id === node.id)) || 
            (link.target === node || (link.target.id === node.id))
        ).length;
    }

    // Set up dimension switch
    dimensionSelect.addEventListener('change', (e) => {
        is3D = e.target.value === '3d';
        if (graphData) {
            initializeGraph(graphData);
        }
    });

    // Set initial value
    is3D = dimensionSelect.value === '3d';

    // Set up search functionality
    searchButton.addEventListener('click', () => {
        searchTerm = searchInput.value.trim();
        searchAttribute = document.getElementById('search-attribute').value;
        const exactSearch = exactSearchCheckbox.checked;
        
        if (searchTerm) {
        fetchGraphData(searchTerm, searchAttribute, exactSearch);
        }
    });

    // Allow pressing Enter to search
    searchInput.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            searchButton.click();
        }
    });

    // Initial empty graph
    initializeGraph({ nodes: [], links: [] });

    // Load initial data
    if (searchInput.value.trim()) {
        searchButton.click();
    }

    // Side navigation
    document.getElementById('open-nav-btn').addEventListener('click', function() {
        toggleNav();
    });
    
    document.querySelector('.close-btn').addEventListener('click', function() {
        closeNav();
    });
    
    // Set up accordions
    document.querySelectorAll('.accordion-header').forEach(function(header) {
        header.addEventListener('click', function() {
            toggleAccordion(this);
        });
    });
    
    // Add event listener for Analyze button
    document.getElementById('analyze-terms-btn').addEventListener('click', analyzeSelectedNodes);
    
    // Set up the AI info accordion
    document.getElementById('ai-info-btn').addEventListener('click', function() {
        this.classList.toggle('active');
        const panel = document.getElementById('ai-info-content');
        if (panel.style.maxHeight) {
            panel.style.maxHeight = null;
            this.querySelector('.arrow').textContent = '▼';
        } else {
            panel.style.maxHeight = panel.scrollHeight + 'px';
            this.querySelector('.arrow').textContent = '▲';
        }
    });

    // Add a fallback initialization function that uses basic rendering
    function fallbackInitGraph() {
        console.log('Attempting fallback graph initialization');
        const container = document.getElementById('graph-container');
        
        if (!container) {
            console.error('Graph container not found');
            return;
        }
        
        // Clear any existing content
        container.innerHTML = '';
        
        // Try to initialize a simple 2D force graph
        try {
            const Graph = ForceGraph()
                (container)
                .graphData({nodes: [], links: []})
                .nodeLabel('id')
                .nodeColor(() => '#1f77b4')
                .backgroundColor('#f9f9f9');
                
            console.log('Fallback graph initialized');
            
            // Try to fetch some data
            fetch('/graph-data?term=test&attribute=kanji&depth=1&exact=false')
                .then(res => res.json())
                .then(data => {
                    console.log('Test data loaded:', data);
                    if (data.nodes && data.nodes.length) {
                        Graph.graphData(data);
                        console.log('Fallback graph populated with data');
                    }
                })
                .catch(err => console.error('Failed to load test data:', err));
                
        } catch (e) {
            console.error('Fallback graph initialization failed:', e);
            container.innerHTML = '<div style="color: red; padding: 20px; text-align: center;">' +
                '<h2>Graph Visualization Failed</h2>' +
                '<p>There was an error initializing the graph visualization.</p>' +
                '<p>Error details: ' + e.message + '</p>' +
                '<p>Please try a different browser or check the console for more information.</p>' +
                '</div>';
        }
    }

    // Call the fallback after a short delay if the main graph hasn't initialized
        setTimeout(() => {
        const container = document.getElementById('graph-container');
        if (container && (!container.hasChildNodes() || container.children.length === 0)) {
            console.log('Main graph failed to initialize, attempting fallback');
            fallbackInitGraph();
        }
    }, 5000); // Wait 5 seconds before trying fallback

    // Initialize all accordion items at document load
    const accordionHeaders = document.querySelectorAll('.accordion-header');
    
    // Add click event listeners
    accordionHeaders.forEach(header => {
        // Set initial state for accordion items
        const content = header.nextElementSibling;
        if (content) {
            content.style.padding = '0 20px';
        }
    });
    
    // Setup AI info accordion separately
    const aiInfoBtn = document.getElementById('ai-info-btn');
    if (aiInfoBtn) {
        const aiInfoContent = document.getElementById('ai-info-content');
        aiInfoBtn.addEventListener('click', () => {
            // Toggle active class
            aiInfoBtn.classList.toggle('active');
            
            // Toggle arrow
            const arrow = aiInfoBtn.querySelector('.arrow');
            if (arrow) {
                arrow.style.transform = arrow.style.transform === 'rotate(180deg)' ? '' : 'rotate(180deg)';
            }
            
            // Toggle content
            if (aiInfoContent.style.maxHeight) {
                aiInfoContent.style.maxHeight = null;
                aiInfoContent.style.padding = '0 20px';
            } else {
                aiInfoContent.style.maxHeight = aiInfoContent.scrollHeight + 'px';
                aiInfoContent.style.padding = '10px 20px';
            }
        });
    }

    // Initialize event listeners and UI elements when DOM is loaded
    console.log('Initializing event listeners for UI elements');
    
    // Add event listener for the open-nav-btn if it exists
    const openNavBtn = document.getElementById('open-nav-btn');
    if (openNavBtn) {
        openNavBtn.addEventListener('click', function() {
            toggleNav();
        });
    }
    
    // Initialize tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            const tabContainer = this.closest('.wikidata-tabs').nextElementSibling;
            
            // Remove active class from all buttons and panes in this container
            const buttons = this.closest('.wikidata-tabs').querySelectorAll('.tab-button');
            buttons.forEach(btn => btn.classList.remove('active'));
            
            if (tabContainer) {
                tabContainer.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.classList.remove('active');
                });
                
                // Add active class to clicked button and corresponding pane
                this.classList.add('active');
                const pane = tabContainer.querySelector(`#${tabId}-tab`);
                if (pane) pane.classList.add('active');
            }
        });
    });
    
    // Initialize accordion headers
    document.querySelectorAll('.accordion-header').forEach(header => {
        header.addEventListener('click', function() {
            toggleAccordion(this);
        });
    });
    
    console.log('Event listeners initialized');

    // Initialize combined sidebar - ensure it starts closed
    const combinedSidebar = document.getElementById('combined-sidebar');
    if (combinedSidebar) {
        // Make sure it starts without the open class
        combinedSidebar.classList.remove('open');
        
        // Add click handler to the header to toggle the sidebar
        const sidebarHeader = combinedSidebar.querySelector('.sidebar-header');
        if (sidebarHeader) {
            sidebarHeader.addEventListener('click', toggleCombinedSidebar);
        }
    }

    // Add this function to handle AI Generation
    function fetchAIGeneration(nodeId) {
        // Clear any previous results
        document.getElementById('generation-status').innerHTML = '';
        document.getElementById('generation-results').innerHTML = '';
        
        // Set up the UI
        document.getElementById('ai-generation-details').innerHTML = `
            <div id="ai-generation-controls" style="margin-top: 15px;">
                <button id="generate-relations-btn" class="compact-button">Generate Relations</button>
                <button id="update-graph-btn" class="compact-button secondary-button" style="display: none;">Update Graph Visualization</button>
                <div id="generation-status"></div>
            </div>
            <div id="generation-results"></div>
        `;
        
        // Show the generate button
        const generateBtn = document.getElementById('generate-relations-btn');
        generateBtn.style.display = 'block';
        generateBtn.disabled = false;
        
        // Add click event listener
        generateBtn.onclick = function() {
            generateLexicalRelations(nodeId);
        };
    }

    function generateLexicalRelations(nodeId) {
        // First check if there are cached AI generation results
        const cachedResults = aiGenerationCache[nodeId];
        if (cachedResults) {
            updateAIGenerationResults(cachedResults);
            return;
        }

        // Show loading status and disable button
        const generateBtn = document.getElementById('generate-relations-btn');
        const updateGraphBtn = document.getElementById('update-graph-btn');
        const statusElement = document.getElementById('generation-status');
        
        // Hide update button until we get results
        if (updateGraphBtn) {
            updateGraphBtn.style.display = 'none';
            updateGraphBtn.disabled = true;
        }
        
        if (generateBtn) generateBtn.disabled = true;
        if (statusElement) statusElement.innerHTML = '<span class="loading">Generating relations... This may take a few seconds.</span>';
        
        // Get current search depth for graph data
        const depthSelect = document.getElementById('depth-select');
        const depth = depthSelect ? depthSelect.value : 1;
        
        // Fetch AI generation data
        fetch(`/ai-generate-relations?id=${encodeURIComponent(nodeId)}&depth=${depth}`)
            .then(response => {
                if (!response.ok) {
                    // Handle server errors with more specific messages
                    if (response.status === 500) {
                        // For 500 errors, try to get the error message from the response
                        return response.json().then(errorData => {
                            const errorMsg = errorData.error || errorData.message || 'Internal server error';
                            throw new Error(`Server responded with 500: ${errorMsg}`);
                        }).catch(err => {
                            // If we can't parse the error JSON, use a generic message
                            throw new Error(`Server responded with 500: INTERNAL SERVER ERROR`);
                        });
                    }
                    throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("AI generation fetch succeeded with data:", data);
                
                // Cache the results for future use
                aiGenerationCache[nodeId] = data;
                
                // Update the UI with results
                updateAIGenerationResults(data);
                
                // Re-enable the generate button
                if (generateBtn) generateBtn.disabled = false;
                
                // Force update button to display if we have graph data
                if (data.graph_data && updateGraphBtn) {
                    console.log("Explicitly forcing update button visibility");
                    updateGraphBtn.style.display = 'inline-block';
                    updateGraphBtn.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error generating lexical relations:', error);
                if (statusElement) {
                    statusElement.innerHTML = `<span class="error">Error: ${error.message}</span>`;
                    
                    // Add more user-friendly instructions when we get the specific error about nodes not in the graph
                    if (error.message.includes('not in the graph')) {
                        statusElement.innerHTML += `<p class="error">Some relations couldn't be added because they reference nodes that don't exist yet. 
                        This is normal - AI sometimes suggests terms that haven't been added to our database yet.</p>
                        <p>The available synonyms and antonyms have still been added to the database successfully.</p>`;
                    }
                }
                
                // Re-enable the generate button
                if (generateBtn) generateBtn.disabled = false;
            });
    }

    function updateAIGenerationResults(data) {
        const statusEl = document.getElementById('generation-status');
        const resultsEl = document.getElementById('generation-results');
        const generateBtn = document.getElementById('generate-relations-btn');
        const updateGraphBtn = document.getElementById('update-graph-btn');
        
        // Debug logging
        console.log("updateAIGenerationResults called with data:", data);
        console.log("update button element:", updateGraphBtn);
        
        // Update status
        if (data.status === 'success') {
            statusEl.innerHTML = `<div class="success">${data.message}</div>`;
        } else if (data.status === 'partial_success') {
            statusEl.innerHTML = `<div class="partial-success">${data.message}</div>`;
        } else {
            statusEl.innerHTML = `<div class="error">${data.message || 'Generation failed'}</div>`;
        }
        
        // Re-enable generate button
        generateBtn.disabled = false;
        
        // Store the graph data for potential later use with the update button
        if (data.graph_data && data.graph_data.nodes && data.graph_data.links) {
            console.log("Graph data is present - should show update button");
            console.log("graph_data nodes:", data.graph_data.nodes.length, "links:", data.graph_data.links.length);
            
            // Store the data in a global variable for reuse
            window.latestAIGeneratedGraphData = data.graph_data;
            
            // Show the update graph button
            updateGraphBtn.style.display = 'inline-block';
            updateGraphBtn.disabled = false;
            
            // Add click event listener if not already set
            if (!updateGraphBtn.hasClickListener) {
                console.log("Adding click listener to update button");
                updateGraphBtn.addEventListener('click', function() {
                    updateGraphVisualization();
                });
                updateGraphBtn.hasClickListener = true;
            }
        } else {
            console.log("No graph data in response - update button will not be shown");
            console.log("data.graph_data:", data.graph_data);
        }
        
        // Format and display results
        const generatedData = data.generated_data || {};
        
        let html = '<div class="ai-generation-content">';
        
        // Show update statistics if available
        if (data.update_stats) {
            html += `
                <h4>Graph Update Statistics</h4>
                <div class="generation-item stats-item">
                    <p><strong>New Nodes:</strong> ${data.update_stats.new_nodes}</p>
                    <p><strong>New Edges:</strong> ${data.update_stats.new_edges}</p>
                    <p><strong>Total Nodes:</strong> ${data.update_stats.nodes_before} → ${data.update_stats.nodes_after}</p>
                    <p><strong>Total Edges:</strong> ${data.update_stats.edges_before} → ${data.update_stats.edges_after}</p>
                </div>
            `;
        }
        
        // Source lexeme info
        const sourceLexeme = generatedData.source_lexeme || {};
        if (sourceLexeme.lemma) {
            html += `
                <h4>Source Lexeme</h4>
                <div class="generation-item source-lexeme">
                    <p><strong>Lemma:</strong> ${sourceLexeme.lemma}</p>
                    <p><strong>Hiragana:</strong> ${sourceLexeme.hiragana || 'N/A'}</p>
                    <p><strong>POS:</strong> ${sourceLexeme.POS || 'N/A'}</p>
                    <p><strong>Translation:</strong> ${formatTranslation(sourceLexeme.translation)}</p>
                </div>
            `;
        }
        
        // Generated synonyms
        const synonyms = generatedData.lexeme_synonyms || [];
        if (synonyms.length > 0) {
            html += `<h4>Generated Synonyms (${synonyms.length})</h4>`;
            html += '<div class="generation-synonyms">';
            
            synonyms.forEach(synonym => {
                const strength = parseFloat(synonym.synonym_strenght || 0).toFixed(2);
                html += `
                    <div class="generation-item synonym-item">
                        <p class="item-title">
                            <span class="item-lemma">${synonym.synonym_lemma || ''}</span>
                            <span class="item-hiragana">${synonym.synonym_hiragana || ''}</span>
                            <span class="item-strength">(${strength})</span>
                        </p>
                        <p><strong>Translation:</strong> ${formatTranslation(synonym.synonym_translation)}</p>
                        <p><strong>POS:</strong> ${synonym.POS || 'N/A'}</p>
                        <p><strong>Mutual Sense:</strong> ${synonym.mutual_sense || ''} (${synonym.mutual_sense_translation || ''})</p>
                        <p><strong>Domain:</strong> ${synonym.synonymy_domain || ''} (${synonym.synonymy_domain_translation || ''})</p>
                    </div>
                `;
            });
            
            html += '</div>';
        }
        
        // Generated antonyms
        const antonyms = generatedData.lexeme_antonyms || [];
        if (antonyms.length > 0) {
            html += `<h4>Generated Antonyms (${antonyms.length})</h4>`;
            html += '<div class="generation-antonyms">';
            
            antonyms.forEach(antonym => {
                const strength = parseFloat(antonym.antonym_strenght || 0).toFixed(2);
                html += `
                    <div class="generation-item antonym-item">
                        <p class="item-title">
                            <span class="item-lemma">${antonym.antonym_lemma || ''}</span>
                            <span class="item-hiragana">${antonym.antonym_hiragana || ''}</span>
                            <span class="item-strength">(${strength})</span>
                        </p>
                        <p><strong>Translation:</strong> ${formatTranslation(antonym.antonym_translation)}</p>
                        <p><strong>POS:</strong> ${antonym.POS || 'N/A'}</p>
                        <p><strong>Domain:</strong> ${antonym.antonymy_domain || ''} (${antonym.antonymy_domain_translation || ''})</p>
                    </div>
                `;
            });
            
            html += '</div>';
        }
        
        html += '</div>';
        
        resultsEl.innerHTML = html;
        
        // The automatic graph update is now handled by the dedicated button
        // We no longer automatically update the graph, but we store the data
        // for use with the "Update Graph Visualization" button
        /*
        if (data.graph_data && data.graph_data.nodes && data.graph_data.links) {
            console.log('Updating graph with new data from AI generation');
            
            // Store the new graph data
            graphData = data.graph_data;
            
            // Initialize the graph with the new data
            initializeGraph(data.graph_data);
            
            // Update search matches if we have a search term
            if (searchTerm) {
                updateSearchMatches(data.graph_data.nodes, searchTerm, searchAttribute);
            }
            
            // Update node info if a node is selected
            if (selectedNode) {
                const updatedNode = data.graph_data.nodes.find(n => n.id === selectedNode.id);
                if (updatedNode) {
                    updateNodeInfo(updatedNode);
                    updateNeighborsPanel(updatedNode);
                }
            }
        }
        */
    }
    
    function updateGraphVisualization() {
        // Get the update button
        const updateGraphBtn = document.getElementById('update-graph-btn');
        
        // Check if we have latest AI generated graph data
        if (!window.latestAIGeneratedGraphData) {
            console.error('No graph data available to update visualization');
            return;
        }
        
        // Show loading indicator on the button
        updateGraphBtn.disabled = true;
        updateGraphBtn.innerText = 'Updating...';
        
        try {
            console.log('Updating graph with new data from AI generation');
            
            // Store the new graph data
            graphData = window.latestAIGeneratedGraphData;
            
            // Initialize the graph with the new data
            initializeGraph(graphData);
            
            // Update search matches if we have a search term
            if (searchTerm) {
                updateSearchMatches(graphData.nodes, searchTerm, searchAttribute);
            }
            
            // Update node info if a node is selected
            if (window.selectedNode) {
                console.log('Selected node exists, updating node info for:', window.selectedNode.id);
                const updatedNode = graphData.nodes.find(n => n.id === window.selectedNode.id);
                if (updatedNode) {
                    updateNodeInfo(updatedNode);
                    // Use updateNeighborsList instead of updateNeighborsPanel for more reliable neighbor detection
                    updateNeighborsList(updatedNode);
                    // Highlight the updated node
                    highlightNodeAndNeighbors(updatedNode);
                }
            } else {
                console.log('No node is currently selected');
            }
            
            // Update button state
            updateGraphBtn.disabled = false;
            updateGraphBtn.innerText = 'Update Graph Visualization';
            
            // Show success message
            const statusEl = document.getElementById('generation-status');
            if (statusEl) {
                statusEl.innerHTML += `<div class="success">Graph visualization updated successfully!</div>`;
            }
        } catch (error) {
            console.error('Error updating graph visualization:', error);
            
            // Show error message
            const statusEl = document.getElementById('generation-status');
            if (statusEl) {
                statusEl.innerHTML += `<div class="error">Error updating graph: ${error.message}</div>`;
            }
            
            // Reset button state
            updateGraphBtn.disabled = false;
            updateGraphBtn.innerText = 'Update Graph Visualization';
        }
    }

    // Modify the updateNodeInfo function to add AI Generation tab handling
    function updateNodeInfo(node) {
        if (!node) {
            document.getElementById('node-info-content').innerHTML = '<p>No node selected. Click on a node in the graph to see its details.</p>';
            document.getElementById('neighbors-list').innerHTML = '<p>No node selected.</p>';
            document.getElementById('gemini-details').innerHTML = '<div class="no-data">Select a node to view AI-enhanced information</div>';
            document.getElementById('wikidata-details').innerHTML = '<div class="no-data">Select a node to view Wikidata information</div>';
            document.getElementById('ai-generation-details').innerHTML = '<div class="no-data">Select a node to generate new lexical relations</div>';
            document.getElementById('exercises-details').innerHTML = '<div class="no-data">Select a node to practice with interactive exercises</div>';
            
            // Update neighbors header
            const neighborsHeader = document.querySelector('#neighbors-info h4');
            if (neighborsHeader) {
                neighborsHeader.textContent = 'Neighbors';
            }
            return;
        }
        
        // Update node info panel
        const nodeInfoContent = document.getElementById('node-info-content');
        let html = '';
        
        // Add node title (kanji)
        html += `<h3 class="node-title">${node.id}</h3>`;
        
        // Show all node properties in the node info panel
        html += '<div class="node-properties">';
        
        for (const [key, value] of Object.entries(node)) {
            // Skip technical properties and null/undefined values
            if (key !== 'id' && key !== 'x' && key !== 'y' && key !== 'z' && 
                key !== 'vx' && key !== 'vy' && key !== 'vz' && 
                key !== 'isSearchMatch' && key !== 'index' && 
                value !== null && value !== undefined && value !== '') {
                html += `<div class="node-property">
                    <div class="property-name">${key}</div>
                    <div class="property-value">${key === 'translation' ? formatTranslation(value) : value}</div>
                </div>`;
            }
        }
        
        // Show degree and connectivity info
        const nodeLinks = graphData.links.filter(link => 
            link.source === node.id || link.target === node.id ||
            (typeof link.source === 'object' && link.source.id === node.id) ||
            (typeof link.target === 'object' && link.target.id === node.id)
        );
        
        html += `
            <div class="node-property">
                <div class="property-name">Connections</div>
                <div class="property-value">${nodeLinks.length}</div>
            </div>`;
        
        html += '</div>'; // Close node-properties
        
        nodeInfoContent.innerHTML = html;
        
        // Update Wikidata panel
        fetchWikidataInfo(node.id);
        
        // Update Gemini panel
        fetchGeminiInfo(node.id);
        
        // Update AI Generation panel
        fetchAIGeneration(node.id);
        
        // Update Lexical Exercises panel
        fetchLexicalExercise(node.id);
        
        // Update neighbors list
        updateNeighborsList(node, nodeLinks);
    }

    // Function to update the neighbors list
    function updateNeighborsList(node, nodeLinks) {
        const neighborsContainer = document.getElementById('neighbors-list');
        if (!neighborsContainer) return;
        
        // Update the header
        const neighborsHeader = document.querySelector('#neighbors-info h4');
        if (neighborsHeader) {
            neighborsHeader.textContent = `Neighbors of "${node.id}"`;
        }
        
        if (!nodeLinks) {
            // If nodeLinks wasn't provided, calculate it now
            nodeLinks = graphData.links.filter(link => 
                link.source === node.id || link.target === node.id ||
                (typeof link.source === 'object' && link.source.id === node.id) ||
                (typeof link.target === 'object' && link.target.id === node.id)
            );
        }
        
        if (!nodeLinks || nodeLinks.length === 0) {
            neighborsContainer.innerHTML = '<p>No connections found for this node.</p>';
            return;
        }
        
        let html = '';
        const neighbors = [];
        
        // Extract neighbors
        nodeLinks.forEach(link => {
            let neighborId;
            if (typeof link.source === 'object' && typeof link.target === 'object') {
                neighborId = link.source.id === node.id ? link.target.id : link.source.id;
            } else {
                neighborId = link.source === node.id ? link.target : link.source;
            }
            
            // Find the neighbor node object
            const neighborNode = graphData.nodes.find(n => n.id === neighborId);
            if (neighborNode) {
                // Determine relationship strength using available attributes
                const strengthVal = parseFloat(link.strength || link.weight || link.synonym_strength || 1);
                neighbors.push({
                    id: neighborId,
                    hiragana: neighborNode.hiragana || '',
                    translation: neighborNode.translation || 'No translation',
                    strength: isNaN(strengthVal) ? 1 : strengthVal,
                    relationship: link.relationship || 'connected'
                });
            }
        });
        
        // --- Classification & ordering with visibility filters ---
        const allowedByToggle = (rel) => {
            if (rel === 'synonym' && !showSynonyms) return false;
            if (rel === 'antonym' && !showAntonyms) return false;
            return true;
        };

        const visibleNeighbors = neighbors.filter(n => allowedByToggle(n.relationship));

        // classify
        const synonymsArr  = visibleNeighbors.filter(n => n.relationship === 'synonym');
        const antonymsArr  = visibleNeighbors.filter(n => n.relationship === 'antonym');
        const othersArr    = visibleNeighbors.filter(n => n.relationship !== 'synonym' && n.relationship !== 'antonym');

        const sortDesc = (a, b) => b.strength - a.strength;
        synonymsArr.sort(sortDesc);
        antonymsArr.sort(sortDesc);
        othersArr.sort(sortDesc);

        // helper html builder
        const renderGroup = (arr, heading=null) => {
            if (arr.length === 0) return '';
            let out = '';
            if (heading) {
                out += `<div class=\"neighbor-group-heading\">${heading}</div>`;
            }
            arr.forEach(neighbor => {
                out += `
                    <div class=\"neighbor-item\">
                        <a class=\"neighbor-kanji node-link\" data-id=\"${neighbor.id}\">${neighbor.id}</a>
                        ${neighbor.hiragana ? `<span class=\"neighbor-hiragana\">${neighbor.hiragana}</span>` : ''}
                        <span class=\"neighbor-translation\">${formatTranslation(neighbor.translation)}</span>
                        <span class=\"neighbor-relation\">${neighbor.relationship} (${neighbor.strength.toFixed(2)})</span>
                    </div>`;
            });
            return out;
        };

        html += renderGroup(synonymsArr, 'Synonyms');
        html += renderGroup(antonymsArr, 'Antonyms');
        html += renderGroup(othersArr);
         
        neighborsContainer.innerHTML = html;
        
        // Add event listeners to neighbor links
        document.querySelectorAll('#neighbors-list .node-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const nodeId = this.dataset.id;
                const neighborNode = graphData.nodes.find(n => n.id === nodeId);
                if (neighborNode) {
                    handleNodeClick(neighborNode);
                    // Highlight the clicked node
                    highlightNodeAndNeighbors(neighborNode);
                }
            });
        });
    }

    // Function to toggle the combined sidebar
    function toggleCombinedSidebar() {
        console.log('toggleCombinedSidebar called');
        const combinedSidebar = document.getElementById('combined-sidebar');
        combinedSidebar.classList.toggle('open');
        
        // Toggle the arrow direction
        const arrow = combinedSidebar.querySelector('.arrow');
        if (arrow) {
            if (combinedSidebar.classList.contains('open')) {
                arrow.style.transform = 'rotate(180deg)';
            } else {
                arrow.style.transform = 'rotate(0deg)';
            }
        }
        
        console.log('Combined sidebar toggled, open state:', combinedSidebar.classList.contains('open'));
    }

    // Function to handle the lexical exercises tab
    function fetchLexicalExercise(nodeId) {
        // Clear any previous exercises
        document.getElementById('exercise-content').innerHTML = '';
        document.getElementById('exercise-status').innerHTML = '';
        
        // Hide the input area until we have an exercise
        document.getElementById('exercise-input-container').style.display = 'none';
        
        // Show the Start Lesson button for learning subtab
        const exerciseBtn = document.getElementById('generate-exercise-btn');
        exerciseBtn.style.display = 'block';
        exerciseBtn.disabled = false;
        
        // Show the Start Conversation button for conversation subtab
        const conversationBtn = document.getElementById('start-conversation-btn');
        conversationBtn.style.display = 'block';
        conversationBtn.disabled = false;
        
        // Add click event listener to the Start Lesson button
        exerciseBtn.onclick = function() {
            generateLexicalExercise(nodeId);
        };
        
        // Add click event listener to the Start Conversation button
        conversationBtn.onclick = function() {
            generateConversation(nodeId);
        };
    }

    // Function to generate a new lexical exercise
    function generateLexicalExercise(nodeId) {
        // Get the selected learning level
        const level = document.getElementById('learning-level').value;
        
        // Show loading status and disable button
        const exerciseBtn = document.getElementById('generate-exercise-btn');
        const statusElement = document.getElementById('exercise-status');
        
        exerciseBtn.disabled = true;
        statusElement.innerHTML = '<span class="loading">Generating exercise... This may take a few seconds.</span>';
        
        // Fetch exercise data
        fetch(`/exercise-generate?id=${encodeURIComponent(nodeId)}&level=${level}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Exercise generation succeeded with data:", data);
                
                // Update the UI with the exercise
                updateExerciseContent(data);
                
                // Show the input area for user to interact
                document.getElementById('exercise-input-container').style.display = 'block';
                
                // Hide the generate button - we're in conversation mode now
                exerciseBtn.style.display = 'none';
                
                // Clear the status
                statusElement.innerHTML = '';
                
                // Set up the submit button event handler
                document.getElementById('exercise-submit-btn').onclick = function() {
                    submitExerciseResponse(nodeId, level);
                };
                
                // Allow pressing Enter to submit
                document.getElementById('exercise-user-input').addEventListener('keyup', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        submitExerciseResponse(nodeId, level);
                    }
                });
            })
            .catch(error => {
                console.error('Error generating lexical exercise:', error);
                statusElement.innerHTML = `<span class="error">Error: ${error.message}</span>`;
                exerciseBtn.disabled = false;
            });
    }
    
    // Function to generate a free conversation
    function generateConversation(nodeId) {
        // Use level 6 (most advanced) for free conversation
        const level = 6;
        
        // Show loading status and disable button
        const conversationBtn = document.getElementById('start-conversation-btn');
        const statusElement = document.getElementById('exercise-status');
        
        conversationBtn.disabled = true;
        statusElement.innerHTML = '<span class="loading">Starting conversation... This may take a few seconds.</span>';
        
        // Fetch conversation starter
        fetch(`/exercise-generate?id=${encodeURIComponent(nodeId)}&level=${level}&mode=conversation`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Conversation started with data:", data);
                
                // Update the UI with the conversation starter
                updateExerciseContent(data);
                
                // Show the input area for user to interact
                document.getElementById('exercise-input-container').style.display = 'block';
                
                // Hide the generate button - we're in conversation mode now
                conversationBtn.style.display = 'none';
                
                // Clear the status
                statusElement.innerHTML = '';
                
                // Set up the submit button event handler
                document.getElementById('exercise-submit-btn').onclick = function() {
                    submitExerciseResponse(nodeId, level, true);
                };
                
                // Allow pressing Enter to submit
                document.getElementById('exercise-user-input').addEventListener('keyup', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        submitExerciseResponse(nodeId, level, true);
                    }
                });
            })
            .catch(error => {
                console.error('Error starting conversation:', error);
                statusElement.innerHTML = `<span class="error">Error: ${error.message}</span>`;
                conversationBtn.disabled = false;
            });
    }

    // Function to update the exercise content in the UI
    function updateExerciseContent(data) {
        const container = document.getElementById('exercise-content');
        
        // Handle error case
        if (data.error) {
            container.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }
        
        // Create a tutor message div
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message tutor-message';
        messageDiv.innerHTML = formatExerciseContent(data.content);
        
        // Clear and add to container
        container.innerHTML = '';
        container.appendChild(messageDiv);
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
        
        // Store conversation history in a data attribute
        container.dataset.history = JSON.stringify([
            { user: '', tutor: data.content }
        ]);
    }

    // Function to format exercise content with proper styling
    function formatExerciseContent(content) {
        // Use the marked library to render markdown
        return marked.parse(content);
    }

    // Function to submit user's response to the exercise or conversation
    function submitExerciseResponse(nodeId, level, isConversation = false) {
        const inputElement = document.getElementById('exercise-user-input');
        const userMessage = inputElement.value.trim();
        
        if (!userMessage) {
            return; // Don't submit empty messages
        }
        
        // Get the container and existing history
        const container = document.getElementById('exercise-content');
        let history = [];
        try {
            history = JSON.parse(container.dataset.history || '[]');
        } catch (e) {
            console.error('Error parsing history:', e);
            history = [];
        }
        
        // Add user message to chat
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'chat-message user-message';
        userMessageDiv.textContent = userMessage;
        container.appendChild(userMessageDiv);
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
        
        // Clear input
        inputElement.value = '';
        
        // Disable submit button and show loading
        const submitBtn = document.getElementById('exercise-submit-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="exercise-loading"></span>';
        
        // Submit to server
        fetch('/exercise-continue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                node_id: nodeId,
                level: level,
                message: userMessage,
                history: history,
                mode: isConversation ? 'conversation' : 'exercise'
            }),
        })
        .then(response => response.json())
        .then(data => {
            // Add tutor response to chat
            const tutorMessageDiv = document.createElement('div');
            tutorMessageDiv.className = 'chat-message tutor-message';
            tutorMessageDiv.innerHTML = formatExerciseContent(data.content);
            container.appendChild(tutorMessageDiv);
            
            // Update history
            container.dataset.history = JSON.stringify(data.history || [
                ...history,
                { user: userMessage, tutor: data.content }
            ]);
            
            // Scroll to bottom
            container.scrollTop = container.scrollHeight;
            
            // Re-enable submit button
            submitBtn.disabled = false;
            submitBtn.textContent = 'Send';
        })
        .catch(error => {
            console.error('Error in exercise conversation:', error);
            
            // Add error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'chat-message tutor-message error';
            errorDiv.textContent = `Sorry, there was an error: ${error.message}`;
            container.appendChild(errorDiv);
            
            // Re-enable submit button
            submitBtn.disabled = false;
            submitBtn.textContent = 'Send';
        });
    }

    // ===== NEW UTILITY FUNCTION =====
    /**
     * Safely formats translation values that may be strings or complex objects.
     * If the value is an object produced by AI Generation (e.g. { target_lemma, target_POS, ... }),
     * we prioritise `target_lemma` and fall back to the first string value found.
     *
     * @param {any} translation - Raw translation value from node data.
     * @returns {string} - Human-readable translation or 'N/A' when unavailable.
     */
    function formatTranslation(translation) {
        if (!translation) return 'N/A';
        if (typeof translation === 'string') return translation;
        if (typeof translation === 'object') {
            if (translation.target_lemma) return translation.target_lemma;
            // Fallback: return first string property value if available
            for (const val of Object.values(translation)) {
                if (typeof val === 'string') return val;
            }
            // Last resort – stringify the object
            try {
                return JSON.stringify(translation);
            } catch (e) {
                return 'N/A';
            }
        }
        return String(translation);
    }
    // ===== END UTILITY FUNCTION =====
});

