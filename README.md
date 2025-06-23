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
- **Japanese Readability Analysis**: Automatic readability assessment of Japanese text using the jreadability library
- **Interactive Learning Exercises**: AI-generated exercises with difficulty level validation
- **Caching System**: Optimized performance with in-memory and Redis-based caching

## Setup and Installation

### Prerequisites
- Python 3.8 or higher
- Pip package manager
- Redis (optional, for enhanced caching)
- Japanese text analysis dependencies (installed automatically with jreadability)

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
   # (Optional) choose default Gemini model – e.g. gemini-2.5-pro-preview-05-06, gemini-2.0-flash, etc.
   GEMINI_DEFAULT_MODEL=gemini-2.0-flash
   REDIS_URL=redis://localhost:6379/0  # Optional
   FLASK_ENV=development
   FLASK_DEBUG=True
   ```

4. Obtain a Google Gemini API key:
   - Visit [Google AI Studio](https://ai.google.dev/) and create an account
   - Generate an API key and add it to your `.env` file

### Running the Application

#### Development Mode
1. Start the Flask development server:
   ```
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

#### Production Deployment

For production environments, use the included Gunicorn-based deployment scripts:

1. **Quick Production Start**:
   ```bash
   # Install production dependencies (includes Gunicorn)
   pip install -r requirements.txt
   
   # Start production server on port 5000
   ./start_production.sh
   ```

2. **Check Server Status**:
   ```bash
   ./production_status.sh
   ```

3. **Stop Production Server**:
   ```bash
   ./stop_production.sh
   ```

4. **System Service (Auto-start on boot)**:
   ```bash
   # Install as systemd service
   sudo cp japanese-lexical-graph.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable japanese-lexical-graph.service
   sudo systemctl start japanese-lexical-graph.service
   ```

The production setup includes:
- **Gunicorn WSGI server** for better performance and stability
- **4 worker processes** for concurrent request handling
- **Automatic restart** on failure
- **Comprehensive logging** (access and error logs)
- **PID file management** for process control
- **Background daemon mode** - runs independently of terminal sessions

**Production URLs**: The application will be accessible at `http://your-server-ip:5000`

For comprehensive production deployment documentation, see the dedicated [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md).

### Linux-Specific Installation

For detailed instructions on setting up and running the application on Linux, please refer to the dedicated [Linux Installation Guide](LINUX_INSTALLATION.md). This guide includes:

- Distribution-specific system prerequisites (Debian/Ubuntu, Red Hat/Fedora, Arch Linux)
- Setting up as a systemd service
- Configuring Nginx as a reverse proxy
- Troubleshooting common Linux issues
- Production deployment tips and security considerations

## User Guide

### Graph Navigation
- **Search**: Enter a Japanese term, English word, or part of speech in the search box
- **View Controls**: Adjust display options in the control panel
- **Node Selection**: Click on nodes to view details and access Wikidata/AI information
- **Term Comparison**: Select two nodes and click "Analyze Selected Terms" to compare them

### Sidebar Features
- **Wikidata Information**: View structured data about the selected term
- **AI Analysis**: Access Gemini-powered explanations and relationship analysis
- **Interactive Exercises**: Generate AI-powered learning exercises with automatic readability analysis
- **Graph Controls**: Adjust visualization parameters

### Readability Analysis
- **Automatic Assessment**: Japanese text is automatically analyzed for readability level
- **6-Level Scale**: From Lower-elementary to Upper-advanced proficiency levels
- **Visual Indicators**: Color-coded badges show difficulty levels for generated exercises
- **Educational Alignment**: Helps learners choose appropriate difficulty content

### Selecting the Gemini Model

There are **two** ways to control which Google Gemini model powers AI features:

1. **Global default (set once in `.env`)** – add or change `GEMINI_DEFAULT_MODEL` to the desired model ID. 
   ```
   # examples
   GEMINI_DEFAULT_MODEL=gemini-2.5-pro-preview-05-06   # state-of-the-art reasoning
   GEMINI_DEFAULT_MODEL=gemini-2.5-flash-preview-04-17 # price/performance flash
   GEMINI_DEFAULT_MODEL=gemini-2.0-flash               # GA work-horse (the project default)
   ```
   Restart the Flask server for the change to take effect.

2. **Per-request override** – pass a `model_name` query parameter to any Gemini-based endpoint:
   ```
   # Get an explanation with 2.5 Pro
   GET /gemini-explanation?term=花&model_name=gemini-2.5-pro-preview-05-06

   # Compare two terms with 2.0 Flash-Lite
   GET /gemini-analyze?term1=愛&term2=恋&model_name=gemini-2.0-flash-lite

   # Fetch a fully enhanced node using the 2.5 Flash preview
   GET /enhanced-node?id=雪&model_name=gemini-2.5-flash-preview-04-17
   ```

Supported model IDs (May 2025) include `gemini-2.5-pro-preview-05-06`, `gemini-2.5-flash-preview-04-17`, `gemini-2.0-flash`, `gemini-2.0-flash-lite`, and experimental/vision variants. Refer to Google AI docs for the most up-to-date list.

## Technical Architecture

### Backend Components
- **Flask**: Web server and API endpoints
- **Gunicorn**: Production WSGI server for deployment
- **NetworkX**: Graph data structure and operations
- **SPARQLWrapper**: Integration with Wikidata's SPARQL endpoint
- **Google Generative AI**: Integration with Gemini API for AI features
- **jreadability**: Japanese text readability analysis library
- **Redis/In-memory Cache**: Performance optimization

### Frontend Components
- **Three.js**: 3D visualization
- **Force-Directed Graph**: Layout algorithm for network visualization
- **Modern CSS**: Responsive design with accordion panels and tabs

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

MIT License 