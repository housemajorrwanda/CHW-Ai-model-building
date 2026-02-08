"""
Evaluate ML grading model accuracy and performance
"""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict
import logging

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grading.ml_matcher import MLMatcher
from grading.matching_engine import MatchingEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_dataset(dataset_path: str) -> pd.DataFrame:
    """Load the Rwanda exam dataset"""
    try:
        df = pd.read_csv(dataset_path)
        logger.info(f"Loaded dataset with {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        raise


def prepare_test_cases(df: pd.DataFrame, sample_size: int = 100) -> List[Dict]:
    """
    Prepare test cases from the dataset.
    Creates positive pairs (correct matches) and negative pairs (incorrect matches).
    """
    test_cases = []
    
    # Get valid question-answer pairs
    valid_pairs = []
    for _, row in df.iterrows():
        question = str(row.get('question', '')).strip()
        answer = str(row.get('answer', '')).strip()
        
        if question and answer and len(question) > 10 and len(answer) > 5:
            valid_pairs.append({
                'question': question,
                'answer': answer,
                'marks': row.get('marks', 0),
                'difficulty': row.get('estimated_difficulty', 'Medium'),
                'question_type': row.get('question_type', ''),
                'keywords': str(row.get('keywords', '')),
                'topic': str(row.get('topic', '')),
                'subject': str(row.get('subject', '')),
                'question_clarity': row.get('question_clarity', 0.7)
            })
    
    logger.info(f"Prepared {len(valid_pairs)} valid question-answer pairs")
    
    # Sample for testing
    if len(valid_pairs) > sample_size:
        valid_pairs = np.random.choice(valid_pairs, size=sample_size, replace=False).tolist()
    
    # Create positive pairs (correct matches)
    for pair in valid_pairs:
        test_cases.append({
            'student_text': pair['answer'],
            'gold_text': pair['answer'],  # Perfect match
            'expected_score': 1.0,
            'is_match': True,
            'context': {
                'difficulty': pair['difficulty'],
                'question_type': pair['question_type'],
                'keywords': pair['keywords'],
                'topic': pair['topic'],
                'subject': pair['subject']
            }
        })
    
    # Create negative pairs (incorrect matches) - mix answers with different questions
    for i, pair1 in enumerate(valid_pairs[:len(valid_pairs)//2]):
        # Pair with a different answer
        pair2 = valid_pairs[(i + len(valid_pairs)//2) % len(valid_pairs)]
        if pair1['answer'] != pair2['answer']:
            test_cases.append({
                'student_text': pair1['answer'],
                'gold_text': pair2['answer'],  # Different answer
                'expected_score': 0.0,
                'is_match': False,
                'context': {
                    'difficulty': pair1['difficulty'],
                    'question_type': pair1['question_type'],
                    'keywords': pair1['keywords'],
                    'topic': pair1['topic'],
                    'subject': pair1['subject']
                }
            })
    
    # Create paraphrased positive pairs (similar but not exact)
    for pair in valid_pairs[:min(20, len(valid_pairs))]:
        # Create a simple paraphrase by adding/removing words
        answer = pair['answer']
        if len(answer) > 20:
            # Simple paraphrase: add "The" or "A" at the beginning
            paraphrased = f"The {answer}" if not answer.startswith(('The ', 'A ', 'An ')) else answer
            if paraphrased != answer:
                test_cases.append({
                    'student_text': paraphrased,
                    'gold_text': answer,
                    'expected_score': 0.7,  # Should be high but not perfect
                    'is_match': True,
                    'context': {
                        'difficulty': pair['difficulty'],
                        'question_type': pair['question_type'],
                        'keywords': pair['keywords'],
                        'topic': pair['topic'],
                        'subject': pair['subject']
                    }
                })
    
    logger.info(f"Created {len(test_cases)} test cases")
    return test_cases


def evaluate_model(matcher: MLMatcher, test_cases: List[Dict]) -> Dict:
    """Evaluate the model on test cases"""
    results = {
        'total': len(test_cases),
        'correct_matches': 0,
        'incorrect_matches': 0,
        'false_positives': 0,
        'false_negatives': 0,
        'scores': [],
        'predictions': []
    }
    
    threshold = 0.6  # Similarity threshold for match/no-match
    
    for i, test_case in enumerate(test_cases):
        student_text = test_case['student_text']
        gold_text = test_case['gold_text']
        expected_match = test_case['is_match']
        context = test_case.get('context')
        
        # Get prediction
        score, strategy = matcher.match(student_text, gold_text, context)
        predicted_match = score >= threshold
        
        # Store results
        results['scores'].append(score)
        results['predictions'].append({
            'student': student_text[:60] + '...' if len(student_text) > 60 else student_text,
            'gold': gold_text[:60] + '...' if len(gold_text) > 60 else gold_text,
            'expected': expected_match,
            'predicted': predicted_match,
            'score': score,
            'strategy': strategy,
            'correct': expected_match == predicted_match
        })
        
        # Count metrics
        if expected_match == predicted_match:
            if expected_match:
                results['correct_matches'] += 1
            else:
                results['incorrect_matches'] += 1
        else:
            if predicted_match and not expected_match:
                results['false_positives'] += 1
            else:
                results['false_negatives'] += 1
    
    return results


def calculate_metrics(results: Dict) -> Dict:
    """Calculate accuracy, precision, recall, F1"""
    total = results['total']
    tp = results['correct_matches']  # True positives (correctly identified matches)
    tn = results['incorrect_matches']  # True negatives (correctly identified non-matches)
    fp = results['false_positives']  # False positives (predicted match but wasn't)
    fn = results['false_negatives']  # False negatives (was match but predicted non-match)
    
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    avg_score = np.mean(results['scores']) if results['scores'] else 0
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'average_score': avg_score,
        'true_positives': tp,
        'true_negatives': tn,
        'false_positives': fp,
        'false_negatives': fn
    }


def print_results(results: Dict, metrics: Dict, show_examples: bool = True):
    """Print evaluation results"""
    print("\n" + "=" * 80)
    print("MODEL EVALUATION RESULTS")
    print("=" * 80)
    
    print(f"\n📊 OVERALL METRICS:")
    print(f"  Accuracy:  {metrics['accuracy']:.2%}")
    print(f"  Precision: {metrics['precision']:.2%}")
    print(f"  Recall:    {metrics['recall']:.2%}")
    print(f"  F1 Score:  {metrics['f1_score']:.2%}")
    print(f"  Avg Score: {metrics['average_score']:.3f}")
    
    print(f"\n📈 CONFUSION MATRIX:")
    print(f"  True Positives (correct matches):     {metrics['true_positives']:4d}")
    print(f"  True Negatives (correct non-matches): {metrics['true_negatives']:4d}")
    print(f"  False Positives (wrong matches):      {metrics['false_positives']:4d}")
    print(f"  False Negatives (missed matches):     {metrics['false_negatives']:4d}")
    
    print(f"\n📝 TEST SET:")
    print(f"  Total test cases: {results['total']}")
    print(f"  Correct predictions: {metrics['true_positives'] + metrics['true_negatives']}")
    print(f"  Incorrect predictions: {metrics['false_positives'] + metrics['false_negatives']}")
    
    if show_examples:
        print(f"\n🔍 EXAMPLE PREDICTIONS:")
        print("-" * 80)
        
        # Show some correct predictions
        correct = [p for p in results['predictions'] if p['correct']]
        incorrect = [p for p in results['predictions'] if not p['correct']]
        
        print(f"\n✓ Correct Predictions (showing {min(5, len(correct))}):")
        for i, pred in enumerate(correct[:5], 1):
            print(f"\n  Example {i}:")
            print(f"    Student: {pred['student']}")
            print(f"    Gold:    {pred['gold']}")
            print(f"    Score:   {pred['score']:.3f} ({pred['strategy']})")
            print(f"    Match:   {pred['predicted']} (expected: {pred['expected']})")
        
        if incorrect:
            print(f"\n✗ Incorrect Predictions (showing {min(5, len(incorrect))}):")
            for i, pred in enumerate(incorrect[:5], 1):
                print(f"\n  Example {i}:")
                print(f"    Student: {pred['student']}")
                print(f"    Gold:    {pred['gold']}")
                print(f"    Score:   {pred['score']:.3f} ({pred['strategy']})")
                print(f"    Match:   {pred['predicted']} (expected: {pred['expected']})")
                print(f"    Issue:   {'False Positive' if pred['predicted'] else 'False Negative'}")
    
    print("\n" + "=" * 80)


def compare_with_baseline(test_cases: List[Dict]):
    """Compare ML model with baseline (simple text similarity)"""
    from difflib import SequenceMatcher
    
    print("\n" + "=" * 80)
    print("BASELINE COMPARISON (Simple Text Similarity)")
    print("=" * 80)
    
    baseline_correct = 0
    ml_correct = 0
    threshold = 0.6
    
    matcher = MLMatcher(use_embeddings=True, similarity_threshold=threshold)
    
    for test_case in test_cases:
        student_text = test_case['student_text']
        gold_text = test_case['gold_text']
        expected_match = test_case['is_match']
        
        # Baseline: simple text similarity
        baseline_score = SequenceMatcher(None, student_text.lower(), gold_text.lower()).ratio()
        baseline_pred = baseline_score >= threshold
        
        # ML model
        ml_score, _ = matcher.match(student_text, gold_text, test_case.get('context'))
        ml_pred = ml_score >= threshold
        
        if baseline_pred == expected_match:
            baseline_correct += 1
        if ml_pred == expected_match:
            ml_correct += 1
    
    baseline_acc = baseline_correct / len(test_cases) if test_cases else 0
    ml_acc = ml_correct / len(test_cases) if test_cases else 0
    
    print(f"\nBaseline Accuracy: {baseline_acc:.2%}")
    print(f"ML Model Accuracy: {ml_acc:.2%}")
    print(f"Improvement:       {(ml_acc - baseline_acc):.2%} ({((ml_acc - baseline_acc) / baseline_acc * 100) if baseline_acc > 0 else 0:.1f}% relative)")
    print("=" * 80)


def main():
    """Main evaluation function"""
    print("\n" + "=" * 80)
    print("ML GRADING MODEL EVALUATION")
    print("=" * 80)
    
    # Paths
    script_dir = Path(__file__).parent
    dataset_path = script_dir.parent / "grading_dataset_enhanced.csv"
    
    if not dataset_path.exists():
        print(f"\n❌ Error: Dataset not found at {dataset_path}")
        print("Please ensure grading_dataset_enhanced.csv is in the project root")
        return 1
    
    try:
        # Load dataset
        print("\n📂 Loading dataset...")
        df = load_dataset(str(dataset_path))
        
        # Prepare test cases
        print("\n🔧 Preparing test cases...")
        test_cases = prepare_test_cases(df, sample_size=200)
        
        # Initialize and train matcher
        print("\n🤖 Training ML matcher...")
        matcher = MLMatcher(use_embeddings=True, similarity_threshold=0.6)
        matcher.train_on_dataset(str(dataset_path))
        
        # Evaluate
        print("\n📊 Evaluating model...")
        results = evaluate_model(matcher, test_cases)
        metrics = calculate_metrics(results)
        
        # Print results
        print_results(results, metrics, show_examples=True)
        
        # Compare with baseline
        compare_with_baseline(test_cases)
        
        print("\n✅ Evaluation completed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

