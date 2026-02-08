"""
Test script for ML-enhanced grading system
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grading.matching_engine import MatchingEngine
from grading.ml_matcher import MLMatcher

def test_ml_matcher():
    """Test the ML matcher directly"""
    print("=" * 70)
    print("Testing ML Matcher")
    print("=" * 70)
    
    try:
        matcher = MLMatcher(use_embeddings=True, similarity_threshold=0.6)
        
        # Test cases from Rwanda dataset
        test_cases = [
            {
                "student": "Mitochondrion is the powerhouse of the cell",
                "gold": "The mitochondrion is known as the powerhouse of the cell",
                "context": {"keywords": "cell, organelle", "topic": "Cell Biology"}
            },
            {
                "student": "Photosynthesis needs chlorophyll, CO2, water and sunlight",
                "gold": "Requirements for Photosynthesis: photosynthesis requires chlorophyll, carbon dioxide, water and sunlight",
                "context": {"keywords": "photosynthesis, chlorophyll", "topic": "Plant Biology"}
            },
            {
                "student": "AIDS is transmitted through sexual contact",
                "gold": "HIV/AIDS is transmitted mainly through sexual intercourse",
                "context": {"keywords": "disease, transmission", "topic": "Health"}
            }
        ]
        
        print("\nTesting semantic similarity matching...\n")
        for i, test in enumerate(test_cases, 1):
            score, strategy = matcher.match(
                test["student"],
                test["gold"],
                test.get("context")
            )
            print(f"Test {i}:")
            print(f"  Student: {test['student'][:60]}...")
            print(f"  Gold:    {test['gold'][:60]}...")
            print(f"  Score:   {score:.3f} ({strategy})")
            print()
        
        print("✓ ML Matcher test completed")
        return True
        
    except Exception as e:
        print(f"✗ ML Matcher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_matching_engine():
    """Test the enhanced matching engine"""
    print("=" * 70)
    print("Testing Enhanced Matching Engine")
    print("=" * 70)
    
    try:
        engine = MatchingEngine(use_ml=True, similarity_threshold=0.6)
        
        # Test cases
        test_cases = [
            {
                "student": "Mitochondrion",
                "gold": "The mitochondrion is known as the powerhouse of the cell"
            },
            {
                "student": "x = 5",
                "gold": "x = 5"
            },
            {
                "student": "2x + 3 = 7",
                "gold": "2*x + 3 = 7"
            }
        ]
        
        print("\nTesting enhanced matching...\n")
        for i, test in enumerate(test_cases, 1):
            score, strategy = engine.match(test["student"], test["gold"])
            print(f"Test {i}:")
            print(f"  Student: {test['student']}")
            print(f"  Gold:    {test['gold'][:60]}...")
            print(f"  Score:   {score:.3f} ({strategy})")
            print()
        
        print("✓ Enhanced Matching Engine test completed")
        return True
        
    except Exception as e:
        print(f"✗ Enhanced Matching Engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("ML-Enhanced Grading System Tests")
    print("=" * 70 + "\n")
    
    results = []
    
    # Test ML matcher
    results.append(("ML Matcher", test_ml_matcher()))
    
    print("\n")
    
    # Test enhanced matching engine
    results.append(("Enhanced Matching Engine", test_enhanced_matching_engine()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + "=" * 70)
    if all_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed. Please check the output above.")
    print("=" * 70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

