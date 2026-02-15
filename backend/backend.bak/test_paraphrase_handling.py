"""
Test paraphrase handling - where ML model really shines
Compares how well each model handles alternative phrasings
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from grading.matching_engine import MatchingEngine


# Test cases specifically designed to test paraphrase understanding
PARAPHRASE_TESTS = [
    {
        'name': 'Mathematical operations',
        'gold': 'Subtract 5 from both sides',
        'variations': [
            'Subtract 5 from both sides',  # Exact
            'Move 5 to the right side',    # Paraphrase
            'Take away 5 from each side',  # Alternative phrasing
            'Minus 5 on both sides',       # Casual
        ]
    },
    {
        'name': 'Division steps',
        'gold': 'Divide both sides by 2',
        'variations': [
            'Divide both sides by 2',      # Exact
            'Divide each side by 2',       # Similar
            'Split both sides by 2',       # Paraphrase
            'Halve both sides',            # Alternative
        ]
    },
    {
        'name': 'Final answer',
        'gold': 'x = 4',
        'variations': [
            'x = 4',                       # Exact
            'x equals 4',                  # Word form
            'The answer is x = 4',        # Verbose
            'Therefore, x = 4',           # Formal
            'x is 4',                     # Simple
        ]
    },
    {
        'name': 'Equation simplification',
        'gold': '2x + 5 = 13',
        'variations': [
            '2x + 5 = 13',                # Exact
            '2 * x + 5 = 13',            # Explicit multiplication
            '5 + 2x = 13',               # Reordered
            'Two x plus five equals thirteen',  # Word form
        ]
    },
    {
        'name': 'Algebraic manipulation',
        'gold': 'Combine like terms',
        'variations': [
            'Combine like terms',         # Exact
            'Add similar terms together', # Paraphrase
            'Group like terms',           # Alternative
            'Simplify by combining terms', # Verbose
        ]
    },
]


def run_paraphrase_test(test_case, ml_engine, baseline_engine, threshold=0.7):
    """Test a set of paraphrases"""
    gold = test_case['gold']
    variations = test_case['variations']
    
    print(f"\nTest: {test_case['name']}")
    print(f"Gold answer: '{gold}'")
    print("-" * 70)
    
    ml_matches = 0
    baseline_matches = 0
    
    for var in variations:
        ml_score, ml_strat = ml_engine.match(var, gold)
        baseline_score, baseline_strat = baseline_engine.match(var, gold)
        
        ml_match = ml_score >= threshold
        baseline_match = baseline_score >= threshold
        
        if ml_match:
            ml_matches += 1
        if baseline_match:
            baseline_matches += 1
        
        # Show results
        ml_symbol = "✓" if ml_match else "✗"
        baseline_symbol = "✓" if baseline_match else "✗"
        
        print(f"  '{var}'")
        print(f"    ML:       {ml_symbol} {ml_score:.3f} ({ml_strat})")
        print(f"    Baseline: {baseline_symbol} {baseline_score:.3f} ({baseline_strat})")
    
    print(f"\n  ML matched: {ml_matches}/{len(variations)}")
    print(f"  Baseline matched: {baseline_matches}/{len(variations)}")
    
    return ml_matches, baseline_matches, len(variations)


def main():
    print("=" * 70)
    print("PARAPHRASE HANDLING TEST")
    print("Testing how well each model handles alternative phrasings")
    print("=" * 70)
    
    # Initialize engines
    ml_engine = MatchingEngine(use_ml=True, use_symbolic=True)
    baseline_engine = MatchingEngine(use_ml=False, use_symbolic=True)
    
    # Check ML status
    print(f"\nML Engine Status:")
    print(f"  ML enabled: {ml_engine.use_ml}")
    print(f"  ML matcher: {'Loaded' if ml_engine.ml_matcher else 'Not available'}")
    print(f"  Symbolic: {ml_engine.sympy_available}")
    
    # Run tests
    total_ml = 0
    total_baseline = 0
    total_variations = 0
    
    for test in PARAPHRASE_TESTS:
        ml_m, base_m, total = run_paraphrase_test(test, ml_engine, baseline_engine)
        total_ml += ml_m
        total_baseline += base_m
        total_variations += total
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total test cases: {total_variations}")
    print()
    print(f"ML Model:")
    print(f"  Matched: {total_ml}/{total_variations} ({total_ml/total_variations*100:.1f}%)")
    print()
    print(f"Baseline Model:")
    print(f"  Matched: {total_baseline}/{total_variations} ({total_baseline/total_variations*100:.1f}%)")
    print()
    
    improvement = total_ml - total_baseline
    print(f"Improvement: +{improvement} matches ({improvement/total_variations*100:.1f}% better)")
    print()
    
    if improvement > 0:
        print("✓ ML model successfully handles more paraphrases than baseline")
    elif improvement == 0:
        print("= Both models perform equally on paraphrases")
    else:
        print("! Baseline outperformed ML (unexpected)")
    
    print("=" * 70)


if __name__ == '__main__':
    main()
