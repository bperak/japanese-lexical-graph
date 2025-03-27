# Japanese Lexical Graph

An interactive visualization and exploration tool for Japanese language lexical networks with enhanced features including Wikidata integration and AI-powered analysis.

## Features

### Core Features
- Interactive 3D graph visualization of Japanese lexical relationships
- Search by Japanese terms, English meanings, or parts of speech
- Detailed node information with translations and relationship strengths
- Customizable graph display options

### Enhanced Features
- **Wikidata Integration**: Access structured data about Japanese terms from Wikidata
- **AI-Powered Analysis**: Get AI-generated explanations and relationship analysis using Google's Gemini API
- **Term Comparison**: Compare two Japanese terms to understand semantic differences and similarities
- **Caching System**: Optimized performance with in-memory and Redis-based caching

## Setup and Installation

### Prerequisites
- Python 3.8 or higher
- Pip package manager
- Redis (optional, for enhanced caching)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/japanese-lexical-graph.git
   cd japanese-lexical-graph
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables by creating a `.env` file in the project root:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   REDIS_URL=redis://localhost:6379/0  # Optional
   FLASK_ENV=development
   FLASK_DEBUG=True
   ```

4. Obtain a Google Gemini API key:
   - Visit [Google AI Studio](https://ai.google.dev/) and create an account
   - Generate an API key and add it to your `.env` file

### Running the Application

1. Start the Flask server:
   ```
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage Guide

### Graph Navigation
- **Search**: Enter a Japanese term, English word, or part of speech in the search box
- **View Controls**: Adjust display options in the control panel
- **Node Selection**: Click on nodes to view details and access Wikidata/AI information
- **Term Comparison**: Select two nodes and click "Analyze Selected Terms" to compare them

### Sidebar Features
- **Wikidata Information**: View structured data about the selected term
- **AI Analysis**: Access Gemini-powered explanations and relationship analysis
- **Graph Controls**: Adjust visualization parameters

## Technical Architecture

### Backend Components
- **Flask**: Web server and API endpoints
- **NetworkX**: Graph data structure and operations
- **SPARQLWrapper**: Integration with Wikidata's SPARQL endpoint
- **Google Generative AI**: Integration with Gemini API for AI features
- **Redis/In-memory Cache**: Performance optimization

### Frontend Components
- **Three.js**: 3D visualization
- **Force-Directed Graph**: Layout algorithm for network visualization
- **Modern CSS**: Responsive design with accordion panels and tabs

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

MIT License 