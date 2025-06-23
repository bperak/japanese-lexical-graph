# PLANNING.md

## Project: Japanese Lexical Graph

### 1. Project Goals
- **Primary Goal**: To create an interactive visualization and exploration tool for Japanese language lexical networks.
- **Secondary Goals**:
    - Integrate AI-powered analysis (term explanations, comparisons, search suggestions) using Google's Gemini API.
    - Provide an interactive AI-driven language learning module (exercises, conversation practice).
    - Incorporate external data from Wikidata for richer term information.
    - Add Japanese text readability analysis to support educational applications.
    - Add spatial understanding capabilities for 3D visualization of cultural concepts (if feasible and aligned with core goals).
    - Improve the user interface for better accessibility, information display, and overall user experience.
    - Demonstrate AI-based methods for extracting and analyzing lexical semantic networks within cultural heritage contexts.

### 2. Technical Architecture

#### Backend Architecture
- **Framework**: Flask (Python)
- **Core Programming Language**: Python 3.x
- **Graph Management**: NetworkX
    - **Data Storage**: `G_synonyms_2024_09_18.pickle` (Serialized NetworkX graph object).
- **Key Libraries/Components**:
    - **SPARQLWrapper**: For querying Wikidata.
    - **Google Generative AI Library**: For integrating with Gemini API.
      - Configurable to use different Gemini models via `.env` and `config.py`.
        - **Current supported IDs** (May 2025):
            - `gemini-2.5-pro-preview-05-06` (state-of-the-art "Pro" reasoning model)
            - `gemini-2.5-flash-preview-04-17` (price/performance "Flash")
            - `gemini-2.0-flash` (GA work-horse)
            - `gemini-2.0-flash-lite` (cost-optimised)
            - `gemini-2.0-pro-exp-02-05` (experimental Pro with 2 M tokens)
            - Vision / streaming variants as published (e.g., `gemini-2.0-flash-preview-image-generation`, `gemini-2.0-flash-live-001`).
        - Set the default with `GEMINI_DEFAULT_MODEL` in `.env`; individual requests can override with the `model_name` query parameter.
    - **PIL/Pillow**: For image processing (if image analysis features are pursued with Gemini Vision API).
    - **jreadability**: For Japanese text readability analysis and educational content assessment.
    - **Caching**: Werkzeug (built-in with Flask, for in-memory) or Flask-Caching for more advanced strategies including Redis (optional).
- **API Structure Considerations**:
    - **Core Graph API**:
        - `/graph-data`: Endpoint for retrieving graph data for visualization.
        - `/search`: Enhanced search functionality, potentially incorporating AI suggestions.
        - `/node-details`: Unified endpoint for fetching comprehensive details about a node from various sources (graph data, Wikidata, AI analysis).
    - **Wikidata Integration API**:
        - `/wikidata-info`: Endpoint for retrieving Wikidata information for specific terms.
        - `/wikidata-related`: Endpoint for finding related terms in Wikidata.
    - **Gemini AI API Endpoints (examples)**:
        - `/gemini/explain-term`: For linguistic information and explanations. (Accepts `model_name` parameter)
        - `/gemini/compare-terms` (renamed from `/gemini-analyze` for clarity): For semantic comparison. (Accepts `model_name` parameter)
        - `/gemini/generate-exercise`: For the learning module. (Can be updated to accept `model_name`)
        - (Potentially) `/gemini/image-analysis`: If image-based features are implemented. (Can be updated to accept `model_name`)
        - (Potentially) `/gemini/search-suggestions`: To augment search. (Can be updated to accept `model_name`)
        - `/enhanced-node`: Provides comprehensive AI-enhanced details for a node. (Accepts `model_name` parameter for underlying Gemini calls)
    - **Japanese Readability API Endpoints**:
        - `/analyze-readability`: General-purpose Japanese text readability analysis
        - `/analyze-exercise-readability`: Exercise-specific readability analysis with educational context

#### Frontend Architecture
- **Core Technologies**: HTML, CSS, JavaScript.
- **3D Visualization**: Three.js (potentially with libraries like 3D-Force-Graph or custom implementations).
- **UI Framework**: Consider Vue.js or React for component-based UI development if complexity grows, otherwise, vanilla JavaScript or a lighter library like Alpine.js might suffice.
- **Styling**: Modern CSS, potentially with a framework like Bootstrap or Tailwind CSS for responsive design.
- **Key UI Components**:
    - Main 2D/3D graph visualization area with controls.
    - Enhanced, responsive sidebar with accordion-style panels and tabs for:
        - Node Information (from graph)
        - Wikidata Information
        - AI-Generated Explanations/Analysis
        - Interactive Learning Module (Exercises/Conversation)
        - (Potentially) Image Analysis Panel
        - (Potentially) 3D Cultural Object Viewer

#### Data Flow
- **User Interaction**: User actions (search, node selection, exercise interaction, image upload) trigger frontend requests to backend APIs.
- **Backend Processing**: Flask backend processes requests, interacts with the NetworkX graph, queries external APIs (Wikidata, Gemini), utilizes helper modules (e.g., `exercises_script.py`), and returns structured data (typically JSON).
- **Frontend Rendering**: Frontend JavaScript receives data and dynamically updates the DOM, graph visualization, and information panels.
- **Caching**: API responses (Wikidata, Gemini) and computationally intensive results are cached on the backend to improve performance and manage API rate limits.
- **Data Transformation**: Data from various sources is processed and structured on the backend before being sent to the frontend. Simple transformations might occur on the frontend for display purposes.

#### Key Modules/Scripts (Existing & Planned)
- `app.py`: Main Flask application, API endpoints, request handling.
- `gemini_helper.py`: Interface for Google Gemini API.
- `wikidata_helper.py`: Interface for Wikidata SPARQL endpoint.
- `exercises_script.py`: Logic for the interactive learning module.
- `ai_generation_single.py`: Script for AI-driven enrichment of graph data.
- `readability_helper.py`: Japanese text readability analysis functionality.
- `cache_helper.py`: Caching functionalities.
- `graph_analysis.py`: Advanced graph algorithms and operations.
- `graph_visualize.py`: Helpers for graph visualization.
- `static/` & `templates/`: Frontend assets and HTML structure.

### 3. Development Style & Conventions
- **Language**: Python (PEP8 compliant, type hints).
- **Formatting**: `black`.
- **Data Validation**: `pydantic` (recommended for API request/response models and complex data structures).
- **API Design**: Aim for clear, well-defined RESTful endpoints.
- **ORM**: SQLAlchemy or SQLModel (consider if relational database needs arise for user data, sessions, etc.).
- **Modularity**:
    - Separate concerns into distinct Python modules/scripts.
    - Target file length under 500 lines; refactor if larger.
- **Imports**: Prefer relative imports within packages/modules where appropriate. Consistent import style.
- **Docstrings**: Google style for all functions, classes, and modules.
    ```python
    def example_function(param1: str) -> bool:
        """Brief summary of the function.

        Args:
            param1 (str): Description of the parameter.

        Returns:
            bool: Description of the return value.
        """
        # Reason: Explain non-obvious logic here if necessary
        return True
    ```
- **Comments**: Comment non-obvious code. Use `# Reason:` for complex logic explanations.

### 4. Testing Strategy

#### Automated Testing
- **Framework**: Pytest.
- **Location**: Tests in a `/tests` folder, mirroring the main app structure (e.g., `tests/unit/backend`, `tests/unit/frontend_helpers`, `tests/integration/api`).
- **Unit Tests**:
    - **Backend**: Test individual functions, classes, API endpoint logic (mocking external services).
        - Test SPARQL query construction and Wikidata response parsing.
        - Test Gemini API prompt generation and response parsing.
        - Test `exercises_script.py` logic.
        - Test caching mechanisms.
    - **Frontend (Helper Functions/Logic)**: Test UI logic components or utility functions if not using a heavy frontend framework with its own testing tools.
- **Integration Tests**:
    - **API Integration**: Test interactions between internal API endpoints and modules.
    - **Full Flow (Backend)**: Test common user flows from API request to response, including interaction with the graph and helper scripts (mocking external APIs like Gemini/Wikidata).
    - **Frontend-Backend (if feasible with tools like Selenium or Playwright for critical paths)**: Test key interactions ensuring data is fetched and displayed correctly.

#### Manual Testing
- **UI/UX Testing**:
    - **Usability Testing**: Test with target users (language learners, researchers) to assess navigation, information discovery, and overall experience.
    - **Cross-Browser/Device Testing**: Ensure compatibility on major desktop browsers (Chrome, Firefox, Safari, Edge) and responsive design on mobile/tablet devices.
- **Data Quality Testing**:
    - **Wikidata Integration**: Verify accuracy, completeness, and relevance of displayed Wikidata.
    - **Gemini AI Responses**: Assess accuracy, relevance, and formatting of AI-generated explanations, comparisons, exercises, and suggestions.
- **Exploratory Testing**: Unscripted testing to find unexpected bugs or usability issues.

### 5. Dependencies & Setup
- Managed via `requirements.txt`.
- Environment variables (e.g., API keys, `GEMINI_DEFAULT_MODEL`) managed via a `.env` file and loaded using `python-dotenv` through `config.py`.
- Key dependencies include: Flask, NetworkX, google-generativeai, SPARQLWrapper, python-dotenv, Werkzeug (for caching, or Flask-Caching), requests, jreadability (for Japanese text analysis). (Add others as identified).

### 6. Deployment Plan

#### Development Environment
- Local setup with all dependencies.
- `.env` file for API keys and local configurations.
- Use of feature branches in Git for development.

#### Staging Environment (Recommended)
- A separate environment mirroring production as closely as possible.
- Used for integration testing, UAT, and validation with stakeholders before production release.
- Can be hosted on a simple PaaS or a dedicated server.

#### Production Deployment
- **Pre-Deployment Checklist**:
    - All tests (unit, integration) passing.
    - Code review completed and approved.
    - API keys and production configurations verified.
    - Caching strategies confirmed and effective.
    - Static assets (CSS, JS) minified/optimized.
    - Database migrations handled (if applicable).
    - Security review (check for common vulnerabilities like XSS, CSRF, proper input sanitization).
- **Deployment Steps (General Example for a Flask App)**:
    1. Announce maintenance window if downtime is expected.
    2. Back up critical data (e.g., graph pickle file if it's modified by users, user data if any).
    3. Pull latest code from the main/release branch.
    4. Install/update Python dependencies: `pip install -r requirements.txt`.
    5. Install/update JavaScript dependencies (if frontend build step exists): `npm install`.
    6. Build frontend assets (if applicable): `npm run build`.
    7. Apply database migrations (if applicable).
    8. Restart application server (e.g., Gunicorn, Waitress, or the development server if used for simple deployments).
    9. Perform smoke tests to verify core functionality.
    10. Announce completion of deployment.
- **Post-Deployment Monitoring**:
    - Monitor application logs for errors.
    - Check API response times and error rates (external and internal).
    - Monitor server resource usage (CPU, memory, network).
    - Gather user feedback.

#### Rollback Plan
- Maintain versioned releases (e.g., using Git tags).
- Have a documented procedure to quickly revert to a previous stable version.
- Test the rollback procedure periodically.

### 7. Timeline Considerations (High-Level)
*(This is a placeholder and should be refined with specific tasks and estimates in TASK.MD or a separate project tracking tool.)*

- **Phase 1**: Core Enhancements (Wikidata Integration, Basic Gemini Features - e.g., term explanation, comparison).
- **Phase 2**: Interactive Learning Module Development & Refinement.
- **Phase 3**: Advanced Features (e.g., Image Analysis, 3D Cultural Object Viewer - if pursued).
- **Phase 4**: UI/UX Polish, Comprehensive Testing, and Deployment Preparation.
- **Ongoing**: Bug fixing, performance optimization, documentation updates.

*(Detailed task breakdown and timelines should be managed in `TASK.MD`)*

### 8. Future Enhancements (Potential Ideas)
- **Advanced Search**: Semantic search using embeddings, natural language queries, cross-lingual search.
- **Enhanced Visualization**: Custom graph layouts, time-based visualizations, VR/AR integration.
- **Community Features**: User accounts, saved searches/graphs, annotations, contribution system, sharing/export options.
- **Advanced AI Integration**: Automatic graph expansion from AI, personalized learning paths, AI-generated educational content summaries.
- **Multi-Language Support**: Full UI localization, cross-language relationship exploration.
- **Graph Database**: Migration to a dedicated graph database (e.g., Neo4j, ArangoDB) for improved scalability and complex queries if the pickle file becomes a bottleneck.
- **Offline Mode**: For core graph exploration if feasible.

### 9. Constraints & Considerations
- **API Rate Limits**: Be mindful of external API (Gemini, Wikidata) rate limits. Implement robust error handling, retries (with backoff), and effective caching.
- **Performance**: Optimize graph loading, processing, and visualization. Caching is critical for external API calls and computationally intensive tasks.
- **Scalability**: The current `.pickle` file for graph data might become a bottleneck for very large graphs or high concurrency. Consider implications for future growth.
- **Security**: Sanitize all user inputs. Protect API keys and sensitive configuration. Follow best practices for web application security.
- **User Experience (UX)**: Strive for an intuitive, responsive, and accessible UI.
- **Data Quality & Accuracy**: Information from external APIs (Wikidata, Gemini) should be presented clearly, and users should be aware of potential inaccuracies or biases.
- **Cost Management**: Monitor usage of paid APIs (like Gemini) to stay within budget.
- **Windows Environment**:
    - Ensure all scripts and commands are compatible with Windows/PowerShell.
    - Use `;` for separating multiple commands in PowerShell, not `&&`.
- **File Size Limit**: Adhere to the 500-line limit for code files; refactor as needed.

### 10. Documentation Strategy
- **`ABOUT.md`**: High-level overview of the application, its features, and a file structure guide.
- **`README.md`**: Setup, installation, and basic usage instructions. Update for new features, dependency changes, or setup modifications.
- **`PLANNING.MD`** (this file): Project architecture, goals, style, constraints, testing, deployment, etc.
- **`TASK.MD`**: Detailed task tracking, progress, and backlog.
- **API Documentation (Internal/External)**: Consider generating API docs (e.g., using Swagger/OpenAPI via Flasgger) if the API surface grows complex or is intended for external use.
- **Inline Code Comments & Docstrings**: Essential for code clarity and maintainability. 