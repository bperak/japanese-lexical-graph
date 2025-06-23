"""
Readability Helper for Japanese Lexical Graph

This module provides functionality to analyze the readability of Japanese text
using the jreadability library. It integrates with the exercise system to provide
readability scores for generated exercises.
"""

import logging
import re
from typing import Dict, Optional, List
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

class ReadabilityAnalyzer:
    """
    Analyzes Japanese text readability using jreadability library.
    
    This class provides methods to compute readability scores and interpret
    them in the context of the Japanese language learning system.
    """
    
    def __init__(self):
        """Initialize the ReadabilityAnalyzer."""
        self._tagger = None
        self._jreadability_available = self._check_jreadability_availability()
    
    def _check_jreadability_availability(self) -> bool:
        """
        Check if jreadability library is available.
        
        Returns:
            bool: True if jreadability is available, False otherwise
        """
        try:
            from jreadability import compute_readability
            return True
        except ImportError:
            logger.warning("jreadability library not available. Install with: pip install jreadability")
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if readability analysis is available."""
        return self._jreadability_available
    
    def _get_tagger(self):
        """Get or create a fugashi tagger for batch processing."""
        if self._tagger is None:
            try:
                from fugashi import Tagger
                self._tagger = Tagger()
            except ImportError:
                logger.error("fugashi library not available")
                return None
        return self._tagger
    
    def extract_japanese_text(self, text: str) -> str:
        """
        Extract only Japanese characters from text.
        
        This removes romaji, English, and other non-Japanese characters,
        keeping only hiragana, katakana, kanji, and Japanese punctuation.
        
        Args:
            text (str): Input text that may contain mixed characters
            
        Returns:
            str: Text containing only Japanese characters and punctuation
        """
        # Japanese character ranges:
        # Hiragana: \u3040-\u309F
        # Katakana: \u30A0-\u30FF  
        # Kanji: \u4E00-\u9FAF
        # Japanese punctuation and symbols: \u3000-\u303F
        # Additional punctuation: \uFF01-\uFF60 (full-width punctuation)
        # Long vowel mark: \u30FC
        japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3000-\u303F\uFF01-\uFF60\u30FC]'
        
        # Extract all individual Japanese characters (including punctuation)
        japanese_chars = re.findall(japanese_pattern, text)
        return ''.join(japanese_chars)
    
    def compute_readability_score(self, text: str, japanese_only: bool = True) -> Optional[float]:
        """
        Compute readability score for Japanese text.
        
        Args:
            text (str): Text to analyze
            japanese_only (bool): If True, extract only Japanese characters before analysis
            
        Returns:
            Optional[float]: Readability score, or None if analysis fails
        """
        if not self._jreadability_available:
            logger.warning("jreadability not available")
            return None
        
        try:
            # Extract only Japanese characters if requested
            if japanese_only:
                text = self.extract_japanese_text(text)
            
            # Skip empty text
            if not text.strip():
                logger.warning("No Japanese text found to analyze")
                return None
            
            from jreadability import compute_readability
            
            # Use shared tagger if available for better performance
            tagger = self._get_tagger()
            if tagger:
                score = compute_readability(text, tagger)
            else:
                score = compute_readability(text)
            
            return float(score)
            
        except Exception as e:
            logger.error(f"Error computing readability score: {e}")
            return None
    
    @lru_cache(maxsize=128)
    def interpret_readability_score(self, score: float) -> Dict[str, str]:
        """
        Interpret jreadability score based on the official scale.
        
        Args:
            score (float): The readability score from jreadability
            
        Returns:
            dict: Level information including range, description, and numeric level
        """
        if 0.5 <= score < 1.5:
            return {
                "level": "Upper-advanced",
                "range": "[0.5, 1.5)",
                "description": "Very advanced Japanese text",
                "numeric_level": 6,
                "color": "#8B0000"  # Dark red
            }
        elif 1.5 <= score < 2.5:
            return {
                "level": "Lower-advanced", 
                "range": "[1.5, 2.5)",
                "description": "Advanced Japanese text",
                "numeric_level": 5,
                "color": "#FF4500"  # Orange red
            }
        elif 2.5 <= score < 3.5:
            return {
                "level": "Upper-intermediate",
                "range": "[2.5, 3.5)",
                "description": "Upper intermediate Japanese text",
                "numeric_level": 4,
                "color": "#FF8C00"  # Dark orange
            }
        elif 3.5 <= score < 4.5:
            return {
                "level": "Lower-intermediate",
                "range": "[3.5, 4.5)",
                "description": "Lower intermediate Japanese text",
                "numeric_level": 3,
                "color": "#FFD700"  # Gold
            }
        elif 4.5 <= score < 5.5:
            return {
                "level": "Upper-elementary",
                "range": "[4.5, 5.5)",
                "description": "Upper elementary Japanese text",
                "numeric_level": 2,
                "color": "#9ACD32"  # Yellow green
            }
        elif 5.5 <= score < 6.5:
            return {
                "level": "Lower-elementary",
                "range": "[5.5, 6.5)",
                "description": "Lower elementary Japanese text",
                "numeric_level": 1,
                "color": "#32CD32"  # Lime green
            }
        else:
            return {
                "level": "Out of range",
                "range": f"Score: {score:.3f}",
                "description": "Score outside expected range",
                "numeric_level": 0,
                "color": "#808080"  # Gray
            }
    
    def analyze_text(self, text: str, japanese_only: bool = True) -> Dict:
        """
        Perform comprehensive readability analysis of text.
        
        Args:
            text (str): Text to analyze
            japanese_only (bool): If True, extract only Japanese characters before analysis
            
        Returns:
            dict: Complete analysis including score, interpretation, and metadata
        """
        if not self._jreadability_available:
            return {
                "available": False,
                "error": "jreadability library not available"
            }
        
        # Extract Japanese text if requested
        japanese_text = self.extract_japanese_text(text) if japanese_only else text
        
        if not japanese_text.strip():
            return {
                "available": True,
                "score": None,
                "error": "No Japanese text found to analyze",
                "original_text": text,
                "japanese_text": japanese_text
            }
        
        # Compute readability score
        score = self.compute_readability_score(text, japanese_only)
        
        if score is None:
            return {
                "available": True,
                "score": None,
                "error": "Failed to compute readability score",
                "original_text": text,
                "japanese_text": japanese_text
            }
        
        # Interpret score
        interpretation = self.interpret_readability_score(score)
        
        return {
            "available": True,
            "score": score,
            "original_text": text,
            "japanese_text": japanese_text,
            "japanese_char_count": len(japanese_text),
            "level": interpretation["level"],
            "level_range": interpretation["range"],
            "level_description": interpretation["description"],
            "numeric_level": interpretation["numeric_level"],
            "color": interpretation["color"],
            "error": None
        }
    
    def analyze_exercise_batch(self, exercises: List[Dict]) -> List[Dict]:
        """
        Analyze readability for a batch of exercises.
        
        Args:
            exercises (list): List of exercise dictionaries containing text
            
        Returns:
            list: Exercises with added readability analysis
        """
        if not self._jreadability_available:
            logger.warning("jreadability not available for batch analysis")
            return exercises
        
        analyzed_exercises = []
        
        for exercise in exercises:
            exercise_copy = exercise.copy()
            
            # Extract text from exercise (could be in 'content', 'text', or 'question' field)
            text_to_analyze = ""
            for field in ['content', 'text', 'question', 'prompt']:
                if field in exercise and exercise[field]:
                    text_to_analyze = str(exercise[field])
                    break
            
            if text_to_analyze:
                analysis = self.analyze_text(text_to_analyze)
                exercise_copy['readability'] = analysis
            else:
                exercise_copy['readability'] = {
                    "available": True,
                    "score": None,
                    "error": "No text found to analyze"
                }
            
            analyzed_exercises.append(exercise_copy)
        
        return analyzed_exercises

# Global instance for easy access
readability_analyzer = ReadabilityAnalyzer()

def analyze_text_readability(text: str, japanese_only: bool = True) -> Dict:
    """
    Convenience function to analyze text readability.
    
    Args:
        text (str): Text to analyze
        japanese_only (bool): If True, extract only Japanese characters before analysis
        
    Returns:
        dict: Readability analysis results
    """
    return readability_analyzer.analyze_text(text, japanese_only)

def get_readability_score(text: str, japanese_only: bool = True) -> Optional[float]:
    """
    Convenience function to get just the readability score.
    
    Args:
        text (str): Text to analyze
        japanese_only (bool): If True, extract only Japanese characters before analysis
        
    Returns:
        Optional[float]: Readability score, or None if analysis fails
    """
    return readability_analyzer.compute_readability_score(text, japanese_only)

def is_readability_available() -> bool:
    """
    Check if readability analysis is available.
    
    Returns:
        bool: True if jreadability is available, False otherwise
    """
    return readability_analyzer.is_available 