# About the Japanese Lexical Graph Application

The Japanese Lexical Graph is an advanced, interactive tool designed for the exploration and study of the Japanese language. It provides a unique visual interface to understand the intricate relationships between Japanese words, enhanced by powerful AI-driven analysis, learning modules, and integration with external knowledge bases like Wikidata.

## Core Mission

The primary goal of this application is to offer users an intuitive and engaging way to:
- Visualize the Japanese lexicon as a network of interconnected terms.
- Discover semantic relationships (synonyms, antonyms, related terms).
- Deepen understanding of word meanings, nuances, and usage.
- Engage in interactive learning exercises and conversation practice.

## Key Features

### 1. Interactive Lexical Graph Visualization
- **3D Graph Display**: Navigate a dynamic 3D representation of the Japanese lexical network, powered by technologies like Three.js.
- **Search Functionality**: Easily find words by searching in Japanese (Kanji, Hiragana, Katakana), English meanings, or by part of speech.
- **Detailed Node Information**: Clicking on a word (node) in the graph reveals comprehensive details, including:
    - Hiragana/Katakana readings.
    - Part of speech.
    - English translations.
    - Strength and type of relationships to connected words.
- **Customizable Display**: Tailor the graph's appearance and layout to suit your preferences and analytical needs.

### 2. Enhanced Data and Analysis
- **Wikidata Integration**: Access structured linguistic and encyclopedic data directly from Wikidata for selected Japanese terms, providing richer contextual information.
- **AI-Powered Term Explanations**: Leveraging Google's Gemini API, the application can generate detailed explanations for Japanese terms, covering:
    - Overview of meaning.
    - Cultural context and significance.
    - Practical usage examples.
    - Nuances in meaning and application.
- **AI-Driven Term Comparison**: Select two terms to receive an AI-generated analysis of their semantic similarities, differences, and relational dynamics.
- **AI-Enhanced Lexical Data**: The underlying graph data itself is enriched through AI. The system can:
    - Generate extensive lists of synonyms and antonyms for Japanese words.
    - Provide detailed attributes for these relationships, including hiragana readings, parts of speech, translations, strength of the relationship, mutual sense, and contextual domain. This ensures the graph is comprehensive and nuanced.

### 3. Interactive Language Learning Module
This is a significant component designed to facilitate active learning:
- **Lexical Exercises Tab**: A dedicated section where users can engage with AI-generated learning content.
- **Structured Exercises**:
    - Chatbot-style interactions focused on a selected Japanese word.
    - Exercises introduce the word in a conversational context, often incorporating related terms from the graph.
    - The AI acts as a language tutor, asking questions to encourage practice and providing helpful corrections.
- **Free-Form Conversation Practice**: A mode for more open-ended conversational practice with the AI, centered around the vocabulary and concepts from the graph.
- **Adaptive Learning Levels**:
    - Six distinct learning levels, from "Beginner 1" to "Advanced 2".
    - Content complexity, use of Kanji/Hiragana/Romaji, and inclusion of English translations are adjusted based on the selected level.
    - For example, beginner levels feature full Romaji support and simple sentence structures, while advanced levels focus on native-like expressions and cultural nuances.
- **Session Memory**: The learning module is designed to remember the context of the current session for more coherent and progressive interactions.

### 4. Performance and Technology
- **Caching System**: Utilizes both in-memory and Redis-based caching (if configured) to optimize performance and ensure a smooth user experience, especially for frequently accessed data and AI-generated content.
- **Technology Stack**:
    - **Backend**: Flask (web framework), NetworkX (for graph data structure and operations).
    - **Frontend**: Three.js (for 3D visualization), modern HTML/CSS/JavaScript.
    - **AI**: Google Gemini API.
    - **Data**: Integration with Wikidata via SPARQL.

## Who is this for?

This application is a valuable resource for:
- **Japanese language learners** at all levels seeking an engaging way to expand vocabulary and understand word connections.
- **Linguists and researchers** studying the Japanese lexicon and semantics.
- **Educators** looking for innovative tools to supplement Japanese language teaching.
- Anyone with an interest in the Japanese language and its intricate beauty.

The Japanese Lexical Graph aims to be more than just a dictionary; it's an immersive environment for discovery, learning, and deeper appreciation of the Japanese language. 

## File Structure and Logic Overview

This section provides a general guide to where the logic for the application's key features is located. Note that this is a simplified overview, and interactions between these components are common.

**Core Application & Web Serving:**
- `app.py`: The main Flask application. It handles web requests, defines API endpoints, serves HTML pages, and coordinates backend logic. It interacts with most other helper and script files.

**Graph Data & Visualization:**
- `G_synonyms_2024_09_18.pickle`: The primary data file containing the NetworkX graph (nodes and edges).
- `graph_visualize.py`: May contain helper functions to prepare graph data specifically for frontend visualization.
- `graph_analysis.py`: Likely holds functions for more complex graph analysis, metrics, or pre-processing tasks on the graph data.
- `templates/` (directory): Contains HTML templates for the web pages.
- `static/` (directory): Contains client-side JavaScript (including Three.js for 3D rendering, user interactions, display customization), CSS for styling, and other static assets.
    - Logic for search input, node detail display, and visualization controls resides largely in JavaScript files here.

**AI-Powered Features (Google Gemini API Integration):**
- `gemini_helper.py`: A central module for interacting with the Google Gemini API. It contains functions for:
    - `generate_explanation()`: Powering AI-powered term explanations.
    - `analyze_relationship()`: Powering AI-driven term comparisons.
    - Other utility functions for API communication.
- `ai_generation_single.py`: Script dedicated to enriching the lexical graph. It uses the Gemini API to generate detailed synonyms, antonyms, and their attributes for individual nodes. It can update the main `.pickle` graph file.
    - `instructions_for _creating_AI_generation.txt`: Contains the detailed prompt and output specifications for `ai_generation_single.py`.

**Interactive Language Learning Module:**
- `exercises_script.py`: The core script for the "Lexical Exercises" feature. It handles:
    - Generating prompts for structured exercises and free-form conversation practice.
    - Adapting content based on selected learning levels.
    - Interacting with the Gemini API (likely via `gemini_helper.py` or direct calls) to get AI responses.
    - Managing session context for the chatbot-like interaction.
- `excercises_instruction.txt` (typo in original filename): A text file outlining the initial design and requirements for this learning module.

**External Data Integration:**
- `wikidata_helper.py`: Contains functions for querying and retrieving data from Wikidata using SPARQL, providing richer context for Japanese terms.

**Performance:**
- `cache_helper.py`: Implements the caching logic (in-memory and potentially Redis). Functions in this module are called by other scripts (`gemini_helper.py`, `exercises_script.py`, etc.) to store and retrieve frequently accessed or computationally expensive data.

This structure separates concerns, with `app.py` acting as the orchestrator, dedicated scripts handling specific functionalities (like AI interactions or learning exercises), helper modules providing common utilities (like API access or caching), and frontend files managing user presentation and interaction. 