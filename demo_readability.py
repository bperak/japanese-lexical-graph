#!/usr/bin/env python3
"""
Demo script for jreadability integration in Japanese Lexical Graph

This script demonstrates the key features of the readability analysis integration:
1. Text readability analysis
2. Exercise-specific analysis
3. API endpoint testing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from readability_helper import analyze_text_readability, get_readability_score, is_readability_available

def print_banner(title):
    """Print a formatted banner for demo sections."""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print(f"{'='*60}")

def demo_basic_analysis():
    """Demonstrate basic readability analysis."""
    print_banner("Basic Readability Analysis")
    
    sample_texts = [
        ("こんにちは", "Simple greeting"),
        ("私は学生です。", "Basic self-introduction"),
        ("昨日、友達と映画を見に行きました。", "Past tense narrative"),
        ("経済の発展に伴い、環境問題が深刻化している。", "Academic text"),
        ("Hello これは日本語 test です。", "Mixed language text"),
    ]
    
    for text, description in sample_texts:
        print(f"\n📝 {description}")
        print(f"   Text: {text}")
        
        analysis = analyze_text_readability(text)
        
        if analysis['available'] and not analysis['error']:
            print(f"   📊 Score: {analysis['score']:.2f}")
            print(f"   📈 Level: {analysis['level']}")
            print(f"   🎨 Color: {analysis['color']}")
            print(f"   🔤 Japanese chars: {analysis['japanese_char_count']}")
        else:
            print(f"   ❌ Error: {analysis.get('error', 'Unknown error')}")

def demo_level_comparison():
    """Demonstrate readability levels with examples."""
    print_banner("Readability Level Examples")
    
    level_examples = [
        ("これは本です。", "Beginner level"),
        ("今日は学校に行きます。", "Elementary level"),
        ("私は毎日日本語を勉強しています。", "Intermediate level"),
        ("この研究は言語学の分野で重要な成果を上げた。", "Advanced level"),
        ("経済理論における構造的変化の分析手法について", "Academic level"),
    ]
    
    for text, expected_level in level_examples:
        score = get_readability_score(text)
        analysis = analyze_text_readability(text)
        
        print(f"\n📚 {expected_level}")
        print(f"   Text: {text}")
        if score:
            print(f"   Score: {score:.2f} → {analysis['level']}")
            level_class = analysis['level'].lower().replace(' ', '-').replace('-', '')
            print(f"   CSS Class: readability-level {level_class}")

def demo_exercise_simulation():
    """Simulate exercise readability analysis."""
    print_banner("Exercise Integration Simulation")
    
    exercises = [
        {
            "level": 1,
            "content": "これは何ですか？",
            "type": "Question"
        },
        {
            "level": 3,
            "content": "昨日、友達と一緒に新しいレストランに行きました。料理はとても美味しかったです。",
            "type": "Story"
        },
        {
            "level": 5,
            "content": "この問題について、様々な観点から検討する必要があります。特に経済的な影響を考慮すべきです。",
            "type": "Discussion"
        }
    ]
    
    for exercise in exercises:
        print(f"\n🎓 Exercise Level {exercise['level']} ({exercise['type']})")
        print(f"   Content: {exercise['content']}")
        
        analysis = analyze_text_readability(exercise['content'])
        
        if analysis['available'] and not analysis['error']:
            match_indicator = "✅" if abs(analysis['score'] - exercise['level']) < 1.5 else "⚠️"
            print(f"   Expected Level: {exercise['level']}")
            print(f"   Actual Score: {analysis['score']:.2f}")
            print(f"   Readability: {analysis['level']}")
            print(f"   Match: {match_indicator}")

def demo_api_format():
    """Show API response format."""
    print_banner("API Response Format")
    
    sample_text = "今日は良い天気ですね。散歩しませんか？"
    analysis = analyze_text_readability(sample_text)
    
    print(f"📡 Sample API Response for: '{sample_text}'")
    print("\n🔧 JSON Structure:")
    
    import json
    print(json.dumps(analysis, indent=2, ensure_ascii=False))

def main():
    """Run the complete demo."""
    print("🚀 jreadability Integration Demo")
    print("Japanese Lexical Graph - Readability Analysis")
    
    # Check if jreadability is available
    if not is_readability_available():
        print("\n❌ jreadability is not available!")
        print("   Please install with: pip install jreadability")
        return
    
    print(f"✅ jreadability is available and ready!")
    
    # Run all demos
    demo_basic_analysis()
    demo_level_comparison()
    demo_exercise_simulation()
    demo_api_format()
    
    print_banner("Demo Complete")
    print("🎉 The jreadability integration is ready for use!")
    print("\n📋 Key Features:")
    print("   • Automatic Japanese text extraction")
    print("   • Real-time readability scoring (0.5-6.5 scale)")
    print("   • Color-coded difficulty levels")
    print("   • Exercise integration")
    print("   • API endpoints for web interface")
    print("\n🔗 Usage in the web app:")
    print("   1. Start a lexical exercise")
    print("   2. Watch the readability score appear automatically")
    print("   3. Compare exercise difficulty with your learning level")

if __name__ == "__main__":
    main() 