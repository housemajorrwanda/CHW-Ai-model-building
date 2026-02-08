"""
Real-world evaluation of ML grading model with sentence-transformers
Tests model on realistic student answer variations
"""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grading.ml_matcher import MLMatcher
from grading.matching_engine import MatchingEngine
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_realistic_student_answers(gold_answer: str, question_type: str) -> List[Dict]:
    """
    Create realistic student answer variations based on question type.
    Simulates how students might actually answer questions.
    """
    variations = []
    
    gold_lower = gold_answer.lower()
    
    # 1. Perfect answer (exact match)
    variations.append({
        'text': gold_answer,
        'expected_score': 1.0,
        'type': 'perfect',
        'description': 'Exact match'
    })
    
    # 2. Minor spelling/grammar variations
    if len(gold_answer) > 20:
        # Add/remove "the", "a", "an"
        if gold_answer.startswith('The '):
            varied = gold_answer[4:]
        elif gold_answer.startswith('A '):
            varied = gold_answer[2:]
        else:
            varied = f"The {gold_answer}"
        
        if varied != gold_answer:
            variations.append({
                'text': varied,
                'expected_score': 0.9,
                'type': 'minor_variation',
                'description': 'Minor grammar variation'
            })
    
    # 3. Paraphrased but correct
    if question_type in ['explanation', 'recall']:
        # Common paraphrases
        paraphrases = {
            'is known as': ['is called', 'is referred to as', 'is'],
            'consists of': ['is made up of', 'contains', 'includes'],
            'is responsible for': ['controls', 'manages', 'handles'],
            'occurs when': ['happens when', 'takes place when'],
        }
        
        for original, alternatives in paraphrases.items():
            if original in gold_lower:
                for alt in alternatives[:1]:  # Just one alternative
                    paraphrased = gold_answer.replace(original, alt)
                    if paraphrased != gold_answer:
                        variations.append({
                            'text': paraphrased,
                            'expected_score': 0.85,
                            'type': 'paraphrase',
                            'description': f'Paraphrased: {original} → {alt}'
                        })
                        break
    
    # 4. Partial answer (correct but incomplete)
    if len(gold_answer) > 50:
        # Take first part
        partial = gold_answer[:len(gold_answer)//2].strip()
        if len(partial) > 20:
            variations.append({
                'text': partial + '...',
                'expected_score': 0.6,
                'type': 'partial',
                'description': 'Partial answer (incomplete)'
            })
    
    # 5. Wrong answer (different topic)
    wrong_answers = [
        "This is not the correct answer.",
        "I don't know the answer to this question.",
        "The answer is different from what was asked.",
    ]
    
    # Only add wrong answers if we have space
    if len(variations) < 8:
        variations.append({
            'text': wrong_answers[0],
            'expected_score': 0.0,
            'type': 'wrong',
            'description': 'Completely wrong answer'
        })
    
    return variations


def load_real_questions(dataset_path: str, num_questions: int = 30) -> List[Dict]:
    """Load real questions from dataset"""
    df = pd.read_csv(dataset_path)
    
    questions = []
    for _, row in df.iterrows():
        question = str(row.get('question', '')).strip()
        answer = str(row.get('answer', '')).strip()
        question_type = str(row.get('question_type', '')).strip()
        
        if question and answer and len(question) > 15 and len(answer) > 10:
            questions.append({
                'question': question,
                'gold_answer': answer,
                'question_type': question_type or 'explanation',
                'difficulty': row.get('estimated_difficulty', 'Medium'),
                'keywords': str(row.get('keywords', '')),
                'topic': str(row.get('topic', '')),
                'subject': str(row.get('subject', '')),
                'marks': row.get('marks', 0)
            })
            
            if len(questions) >= num_questions:
                break
    
    return questions


def evaluate_real_world(matcher: MLMatcher, questions: List[Dict]) -> Dict:
    """Evaluate model on realistic student answer variations"""
    results = {
        'total_tests': 0,
        'by_type': {},
        'scores': [],
        'predictions': [],
        'correct_predictions': 0,
        'incorrect_predictions': 0
    }
    
    threshold = 0.6  # Match threshold
    
    for q_idx, question_data in enumerate(questions, 1):
        gold_answer = question_data['gold_answer']
        question_type = question_data['question_type']
        
        # Create realistic student answer variations
        student_variations = create_realistic_student_answers(gold_answer, question_type)
        
        context = {
            'difficulty': question_data['difficulty'],
            'question_type': question_data['question_type'],
            'keywords': question_data['keywords'],
            'topic': question_data['topic'],
            'subject': question_data['subject']
        }
        
        for variation in student_variations:
            student_answer = variation['text']
            expected_score = variation['expected_score']
            var_type = variation['type']
            
            # Get model prediction
            score, strategy = matcher.match(student_answer, gold_answer, context)
            predicted_match = score >= threshold
            expected_match = expected_score >= threshold
            
            # Track by type
            if var_type not in results['by_type']:
                results['by_type'][var_type] = {
                    'count': 0,
                    'correct': 0,
                    'scores': [],
                    'expected_scores': []
                }
            
            results['by_type'][var_type]['count'] += 1
            results['by_type'][var_type]['scores'].append(score)
            results['by_type'][var_type]['expected_scores'].append(expected_score)
            
            if predicted_match == expected_match:
                results['by_type'][var_type]['correct'] += 1
                results['correct_predictions'] += 1
            else:
                results['incorrect_predictions'] += 1
            
            results['total_tests'] += 1
            results['scores'].append(score)
            
            # Store prediction details
            results['predictions'].append({
                'question_num': q_idx,
                'question': question_data['question'][:60] + '...' if len(question_data['question']) > 60 else question_data['question'],
                'student_answer': student_answer[:80] + '...' if len(student_answer) > 80 else student_answer,
                'gold_answer': gold_answer[:80] + '...' if len(gold_answer) > 80 else gold_answer,
                'expected_score': expected_score,
                'predicted_score': score,
                'expected_match': expected_match,
                'predicted_match': predicted_match,
                'correct': predicted_match == expected_match,
                'type': var_type,
                'strategy': strategy,
                'description': variation['description']
            })
    
    return results


def print_real_world_results(results: Dict):
    """Print detailed real-world evaluation results"""
    print("\n" + "=" * 90)
    print("REAL-WORLD MODEL PERFORMANCE EVALUATION")
    print("=" * 90)
    
    # Overall metrics
    total = results['total_tests']
    correct = results['correct_predictions']
    incorrect = results['incorrect_predictions']
    accuracy = correct / total if total > 0 else 0
    avg_score = np.mean(results['scores']) if results['scores'] else 0
    
    print(f"\n📊 OVERALL PERFORMANCE:")
    print(f"  Total Test Cases: {total}")
    print(f"  Correct Predictions: {correct} ({accuracy:.2%})")
    print(f"  Incorrect Predictions: {incorrect} ({1-accuracy:.2%})")
    print(f"  Average Similarity Score: {avg_score:.3f}")
    
    # Performance by answer type
    print(f"\n📈 PERFORMANCE BY ANSWER TYPE:")
    print("-" * 90)
    
    type_order = ['perfect', 'minor_variation', 'paraphrase', 'partial', 'wrong']
    for var_type in type_order:
        if var_type in results['by_type']:
            data = results['by_type'][var_type]
            type_accuracy = data['correct'] / data['count'] if data['count'] > 0 else 0
            avg_predicted = np.mean(data['scores']) if data['scores'] else 0
            avg_expected = np.mean(data['expected_scores']) if data['expected_scores'] else 0
            
            print(f"\n  {var_type.upper().replace('_', ' ')}:")
            print(f"    Count: {data['count']}")
            print(f"    Accuracy: {type_accuracy:.2%} ({data['correct']}/{data['count']})")
            print(f"    Avg Predicted Score: {avg_predicted:.3f}")
            print(f"    Avg Expected Score:  {avg_expected:.3f}")
            print(f"    Difference: {abs(avg_predicted - avg_expected):.3f}")
    
    # Detailed examples
    print(f"\n🔍 DETAILED EXAMPLES:")
    print("-" * 90)
    
    # Show examples of each type
    for var_type in type_order:
        type_examples = [p for p in results['predictions'] if p['type'] == var_type]
        if type_examples:
            print(f"\n{var_type.upper().replace('_', ' ')} Examples:")
            for i, ex in enumerate(type_examples[:3], 1):
                status = "✓" if ex['correct'] else "✗"
                print(f"\n  Example {i} {status}:")
                print(f"    Question: {ex['question']}")
                print(f"    Student:   {ex['student_answer']}")
                print(f"    Gold:      {ex['gold_answer']}")
                print(f"    Expected:  {ex['expected_score']:.3f} | Predicted: {ex['predicted_score']:.3f}")
                print(f"    Strategy:  {ex['strategy']}")
                print(f"    Match:     Expected={ex['expected_match']}, Predicted={ex['predicted_match']}")
                if not ex['correct']:
                    print(f"    ⚠️  Mismatch: {'False Positive' if ex['predicted_match'] else 'False Negative'}")
    
    # Show incorrect predictions
    incorrect = [p for p in results['predictions'] if not p['correct']]
    if incorrect:
        print(f"\n⚠️  INCORRECT PREDICTIONS ({len(incorrect)}):")
        print("-" * 90)
        for i, ex in enumerate(incorrect[:5], 1):
            print(f"\n  {i}. {ex['type'].upper()}:")
            print(f"     Question: {ex['question']}")
            print(f"     Student:  {ex['student_answer']}")
            print(f"     Gold:     {ex['gold_answer']}")
            print(f"     Expected: {ex['expected_score']:.3f} | Got: {ex['predicted_score']:.3f}")
            print(f"     Issue:    {'False Positive' if ex['predicted_match'] else 'False Negative'}")
    
    print("\n" + "=" * 90)


def compare_with_baseline(matcher: MLMatcher, questions: List[Dict]):
    """Compare ML model with baseline text similarity"""
    print("\n" + "=" * 90)
    print("COMPARISON WITH BASELINE (Simple Text Similarity)")
    print("=" * 90)
    
    baseline_correct = 0
    ml_correct = 0
    total = 0
    threshold = 0.6
    
    for question_data in questions:
        gold_answer = question_data['gold_answer']
        variations = create_realistic_student_answers(gold_answer, question_data['question_type'])
        
        for var in variations:
            student = var['text']
            expected_match = var['expected_score'] >= threshold
            
            # Baseline
            baseline_score = SequenceMatcher(None, student.lower(), gold_answer.lower()).ratio()
            baseline_pred = baseline_score >= threshold
            
            # ML model
            context = {
                'difficulty': question_data['difficulty'],
                'question_type': question_data['question_type'],
                'keywords': question_data['keywords'],
                'topic': question_data['topic'],
                'subject': question_data['subject']
            }
            ml_score, _ = matcher.match(student, gold_answer, context)
            ml_pred = ml_score >= threshold
            
            if baseline_pred == expected_match:
                baseline_correct += 1
            if ml_pred == expected_match:
                ml_correct += 1
            total += 1
    
    baseline_acc = baseline_correct / total if total > 0 else 0
    ml_acc = ml_correct / total if total > 0 else 0
    improvement = ml_acc - baseline_acc
    
    print(f"\nBaseline Accuracy: {baseline_acc:.2%} ({baseline_correct}/{total})")
    print(f"ML Model Accuracy: {ml_acc:.2%} ({ml_correct}/{total})")
    print(f"Improvement:       {improvement:+.2%} ({improvement/baseline_acc*100 if baseline_acc > 0 else 0:+.1f}% relative)")
    print("=" * 90)


def main():
    """Main evaluation function"""
    print("\n" + "=" * 90)
    print("REAL-WORLD ML GRADING MODEL EVALUATION")
    print("Using Sentence Transformers for Semantic Understanding")
    print("=" * 90)
    
    # Paths
    script_dir = Path(__file__).parent
    dataset_path = script_dir.parent / "grading_dataset_enhanced.csv"
    
    if not dataset_path.exists():
        print(f"\n❌ Error: Dataset not found at {dataset_path}")
        return 1
    
    try:
        # Check if sentence-transformers is available
        try:
            from sentence_transformers import SentenceTransformer
            print("\n✅ Sentence Transformers: Available")
            print("   Using semantic embeddings for better understanding")
        except ImportError:
            print("\n⚠️  Sentence Transformers: Not available")
            print("   Model will use TF-IDF only")
        
        # Load questions
        print("\n📂 Loading real questions from dataset...")
        questions = load_real_questions(str(dataset_path), num_questions=25)
        print(f"   Loaded {len(questions)} questions")
        
        # Initialize and train matcher
        print("\n🤖 Initializing ML matcher with sentence-transformers...")
        matcher = MLMatcher(use_embeddings=True, similarity_threshold=0.6)
        matcher.train_on_dataset(str(dataset_path))
        
        if matcher.use_embeddings and matcher.embedding_model:
            print("   ✅ Using semantic embeddings (sentence-transformers)")
        else:
            print("   ⚠️  Using TF-IDF only (sentence-transformers not loaded)")
        
        # Evaluate
        print("\n📊 Evaluating on realistic student answer variations...")
        results = evaluate_real_world(matcher, questions)
        
        # Print results
        print_real_world_results(results)
        
        # Compare with baseline
        compare_with_baseline(matcher, questions)
        
        print("\n✅ Real-world evaluation completed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

