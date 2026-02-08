"""
Quick evaluation script - shows model accuracy with and without sentence transformers
"""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grading.ml_matcher import MLMatcher
from difflib import SequenceMatcher

def quick_eval():
    """Quick evaluation showing model performance"""
    print("\n" + "=" * 80)
    print("QUICK MODEL ACCURACY EVALUATION")
    print("=" * 80)
    
    # Load dataset
    dataset_path = Path(__file__).parent.parent / "grading_dataset_enhanced.csv"
    df = pd.read_csv(dataset_path)
    
    # Get sample of question-answer pairs
    pairs = []
    for _, row in df.iterrows():
        q = str(row.get('question', '')).strip()
        a = str(row.get('answer', '')).strip()
        if q and a and len(q) > 15 and len(a) > 10:
            pairs.append({
                'question': q,
                'answer': a,
                'keywords': str(row.get('keywords', '')),
                'topic': str(row.get('topic', ''))
            })
    
    # Sample 50 pairs for testing
    np.random.seed(42)
    test_pairs = np.random.choice(pairs, size=min(50, len(pairs)), replace=False).tolist()
    
    print(f"\n📊 Testing on {len(test_pairs)} question-answer pairs")
    print(f"   Dataset size: {len(df)} rows")
    
    # Test cases
    test_cases = []
    
    # 1. Exact matches (should be 1.0)
    for pair in test_pairs[:20]:
        test_cases.append({
            'student': pair['answer'],
            'gold': pair['answer'],
            'expected': 1.0,
            'type': 'exact'
        })
    
    # 2. Similar answers (should be high)
    for pair in test_pairs[20:35]:
        # Create slight variation
        answer = pair['answer']
        if len(answer) > 20:
            # Add/remove "The"
            if answer.startswith('The '):
                varied = answer[4:]
            else:
                varied = f"The {answer}"
            test_cases.append({
                'student': varied,
                'gold': answer,
                'expected': 0.7,  # Should be high
                'type': 'similar'
            })
    
    # 3. Different answers (should be low)
    for i, pair1 in enumerate(test_pairs[35:45]):
        pair2 = test_pairs[(i + 10) % len(test_pairs)]
        if pair1['answer'] != pair2['answer']:
            test_cases.append({
                'student': pair1['answer'],
                'gold': pair2['answer'],
                'expected': 0.0,  # Should be low
                'type': 'different'
            })
    
    print(f"\n🔍 Test cases: {len(test_cases)}")
    print(f"   - Exact matches: {sum(1 for t in test_cases if t['type'] == 'exact')}")
    print(f"   - Similar answers: {sum(1 for t in test_cases if t['type'] == 'similar')}")
    print(f"   - Different answers: {sum(1 for t in test_cases if t['type'] == 'different')}")
    
    # Initialize matcher
    print("\n🤖 Initializing ML matcher...")
    matcher = MLMatcher(use_embeddings=True, similarity_threshold=0.6)
    matcher.train_on_dataset(str(dataset_path))
    
    # Check if embeddings are available
    has_embeddings = matcher.use_embeddings and matcher.embedding_model is not None
    print(f"   Using embeddings: {has_embeddings}")
    print(f"   Using TF-IDF: {matcher.tfidf_vectorizer is not None}")
    
    # Evaluate
    print("\n📈 Evaluating...")
    results = {
        'exact': {'scores': [], 'correct': 0, 'total': 0},
        'similar': {'scores': [], 'correct': 0, 'total': 0},
        'different': {'scores': [], 'correct': 0, 'total': 0}
    }
    
    baseline_scores = []
    ml_scores = []
    
    for test in test_cases:
        student = test['student']
        gold = test['gold']
        expected = test['expected']
        test_type = test['type']
        
        # ML model
        score, strategy = matcher.match(student, gold)
        ml_scores.append(score)
        
        # Baseline
        baseline_score = SequenceMatcher(None, student.lower(), gold.lower()).ratio()
        baseline_scores.append(baseline_score)
        
        # Check if prediction is correct
        threshold = 0.6
        ml_pred = score >= threshold
        baseline_pred = baseline_score >= threshold
        expected_pred = expected >= 0.6
        
        results[test_type]['scores'].append(score)
        results[test_type]['total'] += 1
        
        if ml_pred == expected_pred:
            results[test_type]['correct'] += 1
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS BY TEST TYPE")
    print("=" * 80)
    
    for test_type in ['exact', 'similar', 'different']:
        data = results[test_type]
        if data['total'] > 0:
            avg_score = np.mean(data['scores'])
            accuracy = data['correct'] / data['total']
            print(f"\n{test_type.upper()}:")
            print(f"  Accuracy: {accuracy:.2%} ({data['correct']}/{data['total']})")
            print(f"  Avg Score: {avg_score:.3f}")
            print(f"  Expected: {'High' if test_type != 'different' else 'Low'}")
    
    # Overall
    total_correct = sum(r['correct'] for r in results.values())
    total_tests = sum(r['total'] for r in results.values())
    overall_accuracy = total_correct / total_tests if total_tests > 0 else 0
    
    print("\n" + "=" * 80)
    print("OVERALL PERFORMANCE")
    print("=" * 80)
    print(f"\nML Model Accuracy: {overall_accuracy:.2%} ({total_correct}/{total_tests})")
    print(f"Average ML Score:  {np.mean(ml_scores):.3f}")
    print(f"Average Baseline:  {np.mean(baseline_scores):.3f}")
    
    # Show some examples
    print("\n" + "=" * 80)
    print("EXAMPLE PREDICTIONS")
    print("=" * 80)
    
    for i, test in enumerate(test_cases[:5], 1):
        student = test['student'][:50] + '...' if len(test['student']) > 50 else test['student']
        gold = test['gold'][:50] + '...' if len(test['gold']) > 50 else test['gold']
        score, strategy = matcher.match(test['student'], test['gold'])
        baseline = SequenceMatcher(None, test['student'].lower(), test['gold'].lower()).ratio()
        
        print(f"\nExample {i} ({test['type']}):")
        print(f"  Student: {student}")
        print(f"  Gold:    {gold}")
        print(f"  ML Score: {score:.3f} ({strategy})")
        print(f"  Baseline: {baseline:.3f}")
        print(f"  Expected: {'High' if test['expected'] >= 0.6 else 'Low'}")
    
    if not has_embeddings:
        print("\n" + "=" * 80)
        print("⚠️  NOTE: Sentence transformers not installed")
        print("=" * 80)
        print("For better accuracy, install: pip install sentence-transformers")
        print("Current results use TF-IDF only.")
    
    print("\n" + "=" * 80)
    print("✅ Evaluation complete!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    quick_eval()

