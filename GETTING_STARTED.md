# Getting Started Guide

This guide will help you set up and run the enhanced Japanese Lexical Graph application with all its new features.

## Step 1: Set Up Your Environment

### Install dependencies

First, make sure you have Python 3.8 or higher installed. Then install the required packages:

```bash
pip install -r requirements.txt
```

### Configure API keys

Create a `.env` file in the project root directory with the following contents:

```
GEMINI_API_KEY=your_gemini_api_key_here
REDIS_URL=redis://localhost:6379/0  # Optional, only if you have Redis
FLASK_ENV=development
FLASK_DEBUG=True
```

To get a Gemini API key:
1. Visit [Google AI Studio](https://ai.google.dev/)
2. Create an account or sign in
3. Navigate to the API keys section
4. Generate a new API key
5. Copy and paste it into your `.env` file

## Step 2: Run the Application

Start the Flask application:

```bash
python app.py
```

Then open your web browser and navigate to:

```
http://localhost:5000
```

## Step 3: Using the New Features

### Japanese Readability Analysis

The application now includes automatic readability analysis for Japanese text:

1. Navigate to any node in the graph and click on it
2. Open the side navigation panel and go to the "Exercises" tab
3. Generate a new exercise using the AI system
4. The readability level will be automatically displayed with a color-coded badge
5. The system shows 6 proficiency levels from Lower-elementary to Upper-advanced

### Interactive Learning Exercises

1. Select a node in the graph
2. Click on the "Exercises" tab in the side panel
3. Choose your learning level from the dropdown
4. Click "Start Lesson" to generate AI-powered exercises
5. The readability badge will show the actual difficulty of the generated content

### Wikidata Integration

1. Search for a Japanese term using the search box
2. Click on any node in the resulting graph
3. Open the side navigation panel by clicking the menu button in the top right
4. Click on the "Wikidata Information" accordion
5. View structured data, descriptions, and images from Wikidata about the selected term

### AI-Powered Analysis (Gemini)

1. Click on any node in the graph to select it
2. In the side navigation panel, click on the "AI Analysis (Gemini)" accordion
3. View AI-generated explanations of the term and its usage
4. See the "Relationship" tab for analysis of the connection between the selected term and its closest neighbor

### Term Comparison

1. Click on one node in the graph to select it (it will be highlighted in orange)
2. Click on another node to select it as well
3. In the side navigation panel, under "AI Analysis (Gemini)", click the "Analyze Selected Terms" button
4. View a detailed comparison of the two terms, including their semantic relationship, key differences, and a similarity score

## Troubleshooting

### Gemini API Issues

If you see an error in the AI Analysis panel stating "Gemini API is not available":
- Check that your API key is correctly entered in the `.env` file
- Verify that your API key is active in Google AI Studio
- Check that you haven't exceeded your API quota

### Wikidata Integration Issues

If Wikidata information isn't loading:
- Ensure you have an internet connection
- Try a more common Japanese term that is more likely to be in Wikidata
- Some terms might not have corresponding Wikidata entries

### Application Won't Start

If the application fails to start:
- Check that all dependencies are installed
- Verify that your Python version is 3.8 or higher
- Look for error messages in the console where you ran `python app.py`
- If referencing Redis issues, either set up Redis or remove the Redis URL from the `.env` file

### Readability Analysis Issues

If readability analysis is not working:
- The jreadability library requires additional Japanese language models that are installed automatically
- If you see "jreadability not available" messages, try reinstalling: `pip install --force-reinstall jreadability`
- The readability badge may not appear if the generated text is too short (requires substantial Japanese content)
- Clear your browser cache if the readability display is not updating (Ctrl+F5 or Cmd+Shift+R)

## Next Steps

- Try searching for various Japanese terms
- Experiment with comparing different pairs of words
- Explore the 3D visualization by dragging, zooming, and rotating
- Check out both the Wikidata and AI-generated information for different terms

## Getting Help

If you encounter any issues not covered in this guide, please refer to the README.md file or create an issue in the project repository. 