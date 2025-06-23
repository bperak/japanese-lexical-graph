"""
Unit tests for readability_helper module.

Tests the functionality of Japanese text readability analysis
using the jreadability library integration.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from readability_helper import (
    ReadabilityAnalyzer,
    analyze_text_readability,
    get_readability_score,
    is_readability_available
)

class TestReadabilityAnalyzer:
    """Test cases for ReadabilityAnalyzer class."""
    
    def test_initialization(self):
        """Test ReadabilityAnalyzer initialization."""
        analyzer = ReadabilityAnalyzer()
        assert hasattr(analyzer, '_tagger')
        assert hasattr(analyzer, '_jreadability_available')
    
    def test_extract_japanese_text_hiragana(self):
        """Test extraction of hiragana text."""
        analyzer = ReadabilityAnalyzer()
        text = "Hello こんにちは World"
        result = analyzer.extract_japanese_text(text)
        assert result == "こんにちは"
    
    def test_extract_japanese_text_katakana(self):
        """Test extraction of katakana text."""
        analyzer = ReadabilityAnalyzer()
        text = "Test テスト ABC"
        result = analyzer.extract_japanese_text(text)
        assert result == "テスト"
    
    def test_extract_japanese_text_kanji(self):
        """Test extraction of kanji text."""
        analyzer = ReadabilityAnalyzer()
        text = "English 日本語 123"
        result = analyzer.extract_japanese_text(text)
        assert result == "日本語"
    
    def test_extract_japanese_text_mixed(self):
        """Test extraction of mixed Japanese text."""
        analyzer = ReadabilityAnalyzer()
        text = "Hello こんにちは、テスト日本語です。World"
        result = analyzer.extract_japanese_text(text)
        assert result == "こんにちは、テスト日本語です。"
    
    def test_extract_japanese_text_empty(self):
        """Test extraction with no Japanese text."""
        analyzer = ReadabilityAnalyzer()
        text = "Hello World 123"
        result = analyzer.extract_japanese_text(text)
        assert result == ""
    
    def test_interpret_readability_score_upper_advanced(self):
        """Test interpretation of upper-advanced readability score."""
        analyzer = ReadabilityAnalyzer()
        result = analyzer.interpret_readability_score(1.0)
        assert result["level"] == "Upper-advanced"
        assert result["numeric_level"] == 6
        assert result["color"] == "#8B0000"
    
    def test_interpret_readability_score_lower_advanced(self):
        """Test interpretation of lower-advanced readability score."""
        analyzer = ReadabilityAnalyzer()
        result = analyzer.interpret_readability_score(2.0)
        assert result["level"] == "Lower-advanced"
        assert result["numeric_level"] == 5
        assert result["color"] == "#FF4500"
    
    def test_interpret_readability_score_upper_intermediate(self):
        """Test interpretation of upper-intermediate readability score."""
        analyzer = ReadabilityAnalyzer()
        result = analyzer.interpret_readability_score(3.0)
        assert result["level"] == "Upper-intermediate"
        assert result["numeric_level"] == 4
        assert result["color"] == "#FF8C00"
    
    def test_interpret_readability_score_lower_intermediate(self):
        """Test interpretation of lower-intermediate readability score."""
        analyzer = ReadabilityAnalyzer()
        result = analyzer.interpret_readability_score(4.0)
        assert result["level"] == "Lower-intermediate"
        assert result["numeric_level"] == 3
        assert result["color"] == "#FFD700"
    
    def test_interpret_readability_score_upper_elementary(self):
        """Test interpretation of upper-elementary readability score."""
        analyzer = ReadabilityAnalyzer()
        result = analyzer.interpret_readability_score(5.0)
        assert result["level"] == "Upper-elementary"
        assert result["numeric_level"] == 2
        assert result["color"] == "#9ACD32"
    
    def test_interpret_readability_score_lower_elementary(self):
        """Test interpretation of lower-elementary readability score."""
        analyzer = ReadabilityAnalyzer()
        result = analyzer.interpret_readability_score(6.0)
        assert result["level"] == "Lower-elementary"
        assert result["numeric_level"] == 1
        assert result["color"] == "#32CD32"
    
    def test_interpret_readability_score_out_of_range(self):
        """Test interpretation of out-of-range readability score."""
        analyzer = ReadabilityAnalyzer()
        result = analyzer.interpret_readability_score(7.5)
        assert result["level"] == "Out of range"
        assert result["numeric_level"] == 0
        assert result["color"] == "#808080"
    
    @patch('readability_helper.ReadabilityAnalyzer._check_jreadability_availability')
    def test_analyze_text_library_unavailable(self, mock_check):
        """Test analyze_text when jreadability is unavailable."""
        mock_check.return_value = False
        analyzer = ReadabilityAnalyzer()
        
        result = analyzer.analyze_text("こんにちは")
        assert result["available"] is False
        assert "jreadability library not available" in result["error"]
    
    def test_analyze_text_no_japanese_text(self):
        """Test analyze_text with no Japanese characters."""
        analyzer = ReadabilityAnalyzer()
        
        # Mock jreadability availability
        analyzer._jreadability_available = True
        
        result = analyzer.analyze_text("Hello World")
        assert result["available"] is True
        assert result["score"] is None
        assert "No Japanese text found" in result["error"]
    
    @pytest.mark.skipif(not is_readability_available(), reason="jreadability not available")
    def test_compute_readability_score_real(self):
        """Test actual readability score computation with real jreadability."""
        analyzer = ReadabilityAnalyzer()
        
        # Test with simple Japanese text
        score = analyzer.compute_readability_score("おはようございます")
        assert score is not None
        assert isinstance(score, float)
        assert score > 0
    
    @pytest.mark.skipif(not is_readability_available(), reason="jreadability not available")
    def test_analyze_text_real(self):
        """Test full text analysis with real jreadability."""
        analyzer = ReadabilityAnalyzer()
        
        # Test with simple Japanese greeting
        result = analyzer.analyze_text("おはようございます！今日は天気がいいですね。")
        
        assert result["available"] is True
        assert result["score"] is not None
        assert isinstance(result["score"], float)
        assert result["level"] is not None
        assert result["color"] is not None
        assert result["numeric_level"] is not None
        assert result["error"] is None
    
    def test_analyze_exercise_batch_empty(self):
        """Test batch analysis with empty exercises list."""
        analyzer = ReadabilityAnalyzer()
        analyzer._jreadability_available = True
        
        result = analyzer.analyze_exercise_batch([])
        assert result == []
    
    def test_analyze_exercise_batch_no_text(self):
        """Test batch analysis with exercises containing no text."""
        analyzer = ReadabilityAnalyzer()
        analyzer._jreadability_available = True
        
        exercises = [
            {"id": 1, "type": "fill_blank"},
            {"id": 2, "level": 3}
        ]
        
        result = analyzer.analyze_exercise_batch(exercises)
        assert len(result) == 2
        for exercise in result:
            assert "readability" in exercise
            assert exercise["readability"]["score"] is None
            assert "No text found" in exercise["readability"]["error"]
    
    @pytest.mark.skipif(not is_readability_available(), reason="jreadability not available")
    def test_analyze_exercise_batch_with_text(self):
        """Test batch analysis with exercises containing Japanese text."""
        analyzer = ReadabilityAnalyzer()
        
        exercises = [
            {"id": 1, "content": "おはようございます", "level": 1},
            {"id": 2, "text": "日本語を勉強します", "level": 2},
            {"id": 3, "question": "これは何ですか？", "level": 1}
        ]
        
        result = analyzer.analyze_exercise_batch(exercises)
        assert len(result) == 3
        
        for exercise in result:
            assert "readability" in exercise
            assert exercise["readability"]["available"] is True
            assert exercise["readability"]["score"] is not None
            assert exercise["readability"]["level"] is not None

class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    @pytest.mark.skipif(not is_readability_available(), reason="jreadability not available")
    def test_analyze_text_readability(self):
        """Test the analyze_text_readability convenience function."""
        result = analyze_text_readability("こんにちは")
        assert "available" in result
        assert "score" in result
    
    @pytest.mark.skipif(not is_readability_available(), reason="jreadability not available") 
    def test_get_readability_score(self):
        """Test the get_readability_score convenience function."""
        score = get_readability_score("こんにちは")
        assert score is None or isinstance(score, float)
    
    def test_is_readability_available(self):
        """Test the is_readability_available function."""
        result = is_readability_available()
        assert isinstance(result, bool)

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_string(self):
        """Test handling of empty string."""
        analyzer = ReadabilityAnalyzer()
        analyzer._jreadability_available = True
        
        result = analyzer.analyze_text("")
        assert result["available"] is True
        assert result["score"] is None
    
    def test_whitespace_only(self):
        """Test handling of whitespace-only string."""
        analyzer = ReadabilityAnalyzer()
        analyzer._jreadability_available = True
        
        result = analyzer.analyze_text("   \n\t   ")
        assert result["available"] is True
        assert result["score"] is None
    
    @pytest.mark.skipif(not is_readability_available(), reason="jreadability not available")
    def test_punctuation_only(self):
        """Test handling of Japanese punctuation only."""
        analyzer = ReadabilityAnalyzer()
        
        # Japanese punctuation marks
        result = analyzer.analyze_text("。、！？")
        # This should either return a score or handle gracefully
        assert result["available"] is True
    
    @pytest.mark.skipif(not is_readability_available(), reason="jreadability not available")
    def test_single_character(self):
        """Test handling of single Japanese character."""
        analyzer = ReadabilityAnalyzer()
        
        result = analyzer.analyze_text("猫")
        assert result["available"] is True
        # Single characters might have unusual scores
        if result["score"] is not None:
            assert isinstance(result["score"], float)

if __name__ == "__main__":
    pytest.main([__file__]) 