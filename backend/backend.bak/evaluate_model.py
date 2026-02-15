import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from grading.matching_engine import MatchingEngine


def load_test_data(dataset_path, num_samples=200):
    df = pd.read_csv(dataset_path)
    test_cases = []
    sample_df = df.sample(n=min(num_samples, len(df)), random_state=42)

    for idx, row in sample_df.iterrows():
        question = str(row.get('question', '')).strip()
        answer = str(row.get('answer', '')).strip()
        if not question or not answer:
            continue
        test_cases.append({
            'question': question,
            'student_answer': answer,
            'gold_answer': answer,
            'expected_match': True,
            'case_type': 'exact_match'
        })

    for i in range(min(len(sample_df) - 1, num_samples // 2)):
        row1 = sample_df.iloc[i]
        row2 = sample_df.iloc[i + 1]
        
        q1 = str(row1.get('question', '')).strip()
        a1 = str(row1.get('answer', '')).strip()
        a2 = str(row2.get('answer', '')).strip()
        
        if q1 and a1 and a2 and a1 != a2:
            test_cases.append({
                'question': q1,
                'student_answer': a2,
                'gold_answer': a1,
                'expected_match': False,
                'case_type': 'wrong_answer'
            })
    
    return test_cases


def evaluate_engine(engine, test_cases, threshold=0.7):
    results = {
        'correct': 0,
        'incorrect': 0,
        'true_positives': 0,
        'true_negatives': 0,
        'false_positives': 0,
        'false_negatives': 0
    }
    
    for test in test_cases:
        score, strategy = engine.match(
            test['student_answer'],
            test['gold_answer']
        )
        
        predicted_match = score >= threshold
        expected_match = test['expected_match']
        
        if predicted_match == expected_match:
            results['correct'] += 1
            if expected_match:
                results['true_positives'] += 1
            else:
                results['true_negatives'] += 1
        else:
            results['incorrect'] += 1
            if predicted_match and not expected_match:
                results['false_positives'] += 1
            else:
                results['false_negatives'] += 1
    
    return results


def calculate_metrics(results, total):
    tp = results['true_positives']
    tn = results['true_negatives']
    fp = results['false_positives']
    fn = results['false_negatives']
    
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1
    }


def main():
    dataset_path = Path(__file__).parent.parent / 'grading_dataset_enhanced.csv'
    
    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        return
    
    print("Loading test data...")
    test_cases = load_test_data(dataset_path, num_samples=200)
    print(f"Loaded {len(test_cases)} test cases")
    print(f"  - Positive cases (should match): {sum(1 for t in test_cases if t['expected_match'])}")
    print(f"  - Negative cases (shouldn't match): {sum(1 for t in test_cases if not t['expected_match'])}")
    print()

    print("Evaluating ML-enhanced model...")
    ml_engine = MatchingEngine(use_ml=True, use_symbolic=True)
    ml_results = evaluate_engine(ml_engine, test_cases)
    ml_metrics = calculate_metrics(ml_results, len(test_cases))

    print("Evaluating baseline model...")
    baseline_engine = MatchingEngine(use_ml=False, use_symbolic=True)
    baseline_results = evaluate_engine(baseline_engine, test_cases)
    baseline_metrics = calculate_metrics(baseline_results, len(test_cases))

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print()
    
    print("ML-Enhanced Model:")
    print(f"  Accuracy:  {ml_metrics['accuracy']:.1%}")
    print(f"  Precision: {ml_metrics['precision']:.1%}")
    print(f"  Recall:    {ml_metrics['recall']:.1%}")
    print(f"  F1-Score:  {ml_metrics['f1_score']:.3f}")
    print()
    
    print("Baseline Model:")
    print(f"  Accuracy:  {baseline_metrics['accuracy']:.1%}")
    print(f"  Precision: {baseline_metrics['precision']:.1%}")
    print(f"  Recall:    {baseline_metrics['recall']:.1%}")
    print(f"  F1-Score:  {baseline_metrics['f1_score']:.3f}")
    print()

    print("Confusion Matrix (ML Model):")
    print(f"  True Positives:  {ml_results['true_positives']}")
    print(f"  True Negatives:  {ml_results['true_negatives']}")
    print(f"  False Positives: {ml_results['false_positives']}")
    print(f"  False Negatives: {ml_results['false_negatives']}")
    print()
    
    print("=" * 70)

    results_file = Path(__file__).parent / 'evaluation_results.txt'
    with open(results_file, 'w') as f:
        f.write("Model Evaluation Results\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Test cases: {len(test_cases)}\n\n")
        f.write("ML Model:\n")
        f.write(f"  Accuracy: {ml_metrics['accuracy']:.1%}\n")
        f.write(f"  Precision: {ml_metrics['precision']:.1%}\n")
        f.write(f"  Recall: {ml_metrics['recall']:.1%}\n")
        f.write(f"  F1-Score: {ml_metrics['f1_score']:.3f}\n\n")
        f.write("Baseline Model:\n")
        f.write(f"  Accuracy: {baseline_metrics['accuracy']:.1%}\n")
        f.write(f"  Precision: {baseline_metrics['precision']:.1%}\n")
        f.write(f"  Recall: {baseline_metrics['recall']:.1%}\n")
        f.write(f"  F1-Score: {baseline_metrics['f1_score']:.3f}\n")
    
    print(f"Results saved to: {results_file}")


if __name__ == '__main__':
    main()
