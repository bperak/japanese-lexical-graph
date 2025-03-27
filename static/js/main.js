// static/js/main.js

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

document.addEventListener('DOMContentLoaded', () => {
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
    
    let Graph;
    let graphData = { nodes: [], links: [] };  // Initialize with empty arrays
    let searchTerm = '';
    let searchAttribute = 'kanji';
    let highlightNodes = new Set();
    let highlightLinks = new Set();
    let hoverNode = null;
    let clickedNode = null;
    let is3D = false;
    let labelSizeMultiplier = 1.5;  // Default size multiplier
    let wikidataCache = {};  // Cache for Wikidata results
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

    // Add slider event listener
    labelSizeSlider.addEventListener('input', (e) => {
        labelSizeMultiplier = parseFloat(e.target.value);
        labelSizeValue.textContent = `${labelSizeMultiplier}x`;
        if (graphData) {
            initializeGraph(graphData);
        }
    });

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
            matches.slice(0, 10).forEach(match => {
                matchesHtml += `<li><a class="node-link" data-id="${match.id}">${match.id}</a></li>`;
            });
            if (matches.length > 10) {
                matchesHtml += `<li>...and ${matches.length - 10} more</li>`;
            }
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
            matchesContainer.innerHTML = '<p>No exact matches found.</p>';
        }
    }

    // New function to fetch Wikidata information
    function fetchWikidataInfo(term) {
        console.log('Fetching Wikidata info for:', term);
        
        // Check cache first
        if (wikidataCache[term]) {
            console.log('Using cached Wikidata info for', term);
            updateWikidataPanel(wikidataCache[term]);
            
            // Open the Wikidata sidebar
            const wikidataSidebar = document.getElementById('wikidata-sidebar');
            if (!wikidataSidebar.classList.contains('open')) {
                console.log('Opening Wikidata sidebar');
                toggleWikidataSidebar();
            } else {
                console.log('Wikidata sidebar is already open');
            }
            
            return;
        }

        // Show loading state
        document.getElementById('wikidata-details').innerHTML = '<div class="loading">Loading Wikidata information...</div>';
        
        // Open the Wikidata sidebar if it's not already open
        const wikidataSidebar = document.getElementById('wikidata-sidebar');
        if (!wikidataSidebar.classList.contains('open')) {
            console.log('Opening Wikidata sidebar');
            toggleWikidataSidebar();
        } else {
            console.log('Wikidata sidebar is already open');
        }
        
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
            container.innerHTML = '<div class="no-data">No matching entries found in Wikidata for this term</div>';
            return;
        }

        try {
            let html = '';
            
            // Process each entity
            for (const [itemUrl, details] of Object.entries(data)) {
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
        
        // Open the bottom sidebar if it's not already open
        const geminiSidebar = document.getElementById('gemini-sidebar');
        if (!geminiSidebar.classList.contains('open')) {
            console.log('Opening Gemini sidebar');
            geminiSidebar.classList.add('open');
                } else {
            console.log('Gemini sidebar is already open');
        }
        
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
            
            // Always show raw response for debugging if available
            if (explanation.raw_response) {
                html += `
                    <div class="raw-response" style="margin-top: 15px; font-size: 0.8rem;">
                        <details>
                            <summary>Show Raw API Response</summary>
                            <pre>${explanation.raw_response}</pre>
                        </details>
                    </div>
                `;
            }
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
        console.log('Initializing graph with data:', data);
        
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
                .onNodeClick(handleNodeClick)
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
                .onNodeClick(handleNodeClick)
                .onNodeHover(handleNodeHover)
                .onLinkHover(handleLinkHover);
            }
            
            console.log('Graph initialized successfully');
            
            // Store the graph instance globally
            Graph = graph;
            window.currentGraph = graph;
            
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
        
        // Color based on link type
        const strength = parseFloat(link.synonym_strength) || 0.5;
        
        // Use a brighter color scheme for the dark background
        // From light blue (weak) to bright magenta (strong) with higher luminosity
        const hue = 240 - (strength * 180); // Blue (240) to magenta (300+)
        return `hsl(${hue}, 80%, 70%)`; // Higher lightness (70%) for visibility on dark background
    }

    function getLinkWidth(link) {
        return highlightLinks.has(link) ? 3 : 1.5; // Slightly thicker lines by default
    }

    function handleNodeClick(node) {
        console.log('Node clicked:', node);
        
        // Open the side nav if it's not already open
        const sideNav = document.getElementById('side-nav');
        if (!sideNav.classList.contains('open')) {
            console.log('Opening side navigation from handleNodeClick');
            toggleNav();
        }
        
        // Update node info panel
        const nodeInfo = document.getElementById('node-info');
        if (nodeInfo) {
            let info = `<h4>${node.japanese || node.id || 'Unknown'}</h4>`;
            
            if (node.pos) info += `<p>POS: ${node.pos}</p>`;
            if (node.english && node.english.length) {
                info += `<p>English: ${Array.isArray(node.english) ? node.english.join(', ') : node.english}</p>`;
            }
            
            nodeInfo.innerHTML = info;
        }
        
        // Update neighbors panel
        updateNeighborsPanel(node);
        
        // Try to fetch Wikidata info if available
        // First try with Japanese property, then fall back to ID
        const term = node.japanese || node.id;
        if (term && typeof fetchWikidataInfo === 'function') {
            console.log('Attempting to fetch Wikidata info for term:', term);
            try {
                fetchWikidataInfo(term);
            } catch (e) {
                console.error('Error fetching Wikidata info:', e);
            }
        } else {
            console.warn('No suitable term found for Wikidata lookup');
        }
        
        // Try to fetch Gemini info if available
        if (node.id && typeof fetchGeminiInfo === 'function') {
            console.log('Attempting to fetch Gemini info for node ID:', node.id);
            try {
                fetchGeminiInfo(node.id);
            } catch (e) {
                console.error('Error fetching Gemini info:', e);
            }
        } else {
            console.warn('No node ID for Gemini lookup');
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
                            ${neighbor.pos ? `<span class="pos">${neighbor.pos}</span>` : ''}
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
        // When hovering a node, update the hoverNode
        hoverNode = node || null;
        
        // Update the cursor
        document.getElementById('3d-graph').style.cursor = node ? 'pointer' : null;
        
        // Update the visualization
        updateHighlight();
        
        return true;
    }

    function handleLinkHover(link) {
        // When hovering a link, clear and set highlightLinks
                highlightLinks.clear();
        if (link) highlightLinks.add(link);
        
        // Update the visualization
        updateHighlight();
        
        return true;
    }

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
        // Update the node color
        Graph.nodeColor(getNodeColor);
        // Update the link color and width
        Graph.linkColor(getLinkColor);
        Graph.linkWidth(getLinkWidth);
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
                <p><strong>Translation:</strong> <span>${node.translation || 'N/A'}</span></p>
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
                            ${neighbor.translation ? `<span class="translation">${neighbor.translation}</span>` : ''}
                            ${neighbor.POS ? `<span class="pos">${neighbor.POS}</span>` : ''}
                        </div>
                    </div>
                `;
            }).join('')
            : '<p>No neighbors found.</p>';
        
        // Add event listeners for the neighbor links
        document.querySelectorAll('#neighbors-list .node-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const nodeId = e.target.dataset.id;
                const clickedNeighbor = graphData.nodes.find(n => n.id === nodeId);
                if (clickedNeighbor) {
                    handleNodeClick(clickedNeighbor);
                }
            });
        });
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
});

