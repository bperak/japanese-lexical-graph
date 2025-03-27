# Japanese Lexical Graph

Interactive visualization of Japanese synonym relationships using 3D and 2D force-directed graphs.

## Overview

This application visualizes Japanese lexical relationships in an interactive graph format. Users can search for Japanese words by kanji, hiragana, part of speech, translation, or JLPT level, and explore their synonym relationships in either 2D or 3D visualization.

![Japanese Lexical Graph Screenshot](https://vasturiano.github.io/3d-force-graph/example/preview.png)
*Example visualization (actual appearance may differ)*

## Features

- Search Japanese words by multiple criteria (kanji, hiragana, POS, translation, JLPT level)
- Switch between 2D and 3D graph visualizations
- Adjustable search depth for exploring relationships
- Interactive node selection with detailed information display
- Color-coding by JLPT level
- Customizable label sizes
- Focus mode to highlight specific nodes and their connections
- Automatic graph fitting to canvas

## Technology Stack

- **Backend**: Flask (Python)
- **Data Storage**: NetworkX graph stored in pickle format
- **Frontend**: HTML, CSS, JavaScript
- **Visualization**: 3D-Force-Graph, ForceGraph libraries

## Setup and Installation

### Prerequisites
- Python 3.8+
- Node.js (for development only)

### Installation

1. Clone the repository
   ```
   git clone https://github.com/yourusername/japanese-lexical-graph.git
   cd japanese-lexical-graph
   ```

2. Create a virtual environment and install dependencies
   ```
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the application
   ```
   python app.py
   ```

4. Open a web browser and navigate to the address shown in the console (typically http://localhost:8003)

## Usage

1. Type a Japanese word, character, or English translation in the search box
2. Select the search attribute (kanji, hiragana, POS, etc.)
3. Choose the search depth (1-3) to control how many related words to display
4. Toggle between 2D and 3D visualization as preferred
5. Click on nodes to view detailed information
6. Use the "Focus on Node" checkbox to highlight connections
7. Use "Fit to Canvas" to optimize the view

## Data

The application uses a NetworkX graph stored in pickle format (`G_synonyms_2024_09_18.pickle`), containing Japanese words with attributes such as:
- Kanji representation
- Hiragana reading
- Part of speech
- English translation
- JLPT level

## Developers

- Benedikt Perak, University of Rijeka
- Dragana Špica, University of Pula

## Publications

- 2024-10: Špica, D., & Perak, B. (2024). Enhancing Japanese Lexical Networks Using Large Language Models. Euralex 21.
- 2024-12: Špica, D., & Perak, B. (2024). Automating Lexical Graph Construction with Large Language Models: A Scalable Approach to Japanese Multi-relation Lexical Networks. (Submitted for review.)

## License

This project is licensed under the terms included in the LICENSE file. 