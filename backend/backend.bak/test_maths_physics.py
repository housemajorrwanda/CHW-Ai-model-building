"""
Test maths and physics specific paraphrases
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from grading.matching_engine import MatchingEngine


MATHS_TESTS = [
    ("x = 4", ["x = 4", "x equals 4", "x is 4"]),
    ("2x + 5 = 13", ["2x + 5 = 13", "2 * x + 5 = 13", "5 + 2x = 13"]),
    ("Area = πr²", ["Area = πr²", "A = pi * r^2", "Area equals pi times radius squared"]),
    ("Divide both sides by 2", ["Divide both sides by 2", "Split by 2", "Halve both sides"]),
    ("90 degrees", ["90 degrees", "90°", "ninety degrees", "right angle"]),
]

PHYSICS_TESTS = [
    ("F = ma", ["F = ma", "Force equals mass times acceleration", "F = m * a"]),
    ("v = u + at", ["v = u + at", "final velocity = initial velocity + acceleration × time"]),
    ("KE = ½mv²", ["KE = ½mv²", "Kinetic energy = 0.5 * m * v^2", "KE equals half mass times velocity squared"]),
    ("10 m/s", ["10 m/s", "10 meters per second", "10m/s"]),
    ("Newton's first law", ["Newton's first law", "Law of inertia", "First law of motion"]),
]


def test_subject(tests, subject_name, ml_engine, baseline_engine):
    print(f"\n{subject_name}")
    print("=" * 60)
    
    ml_total = 0
    baseline_total = 0
    all_tests = 0
    
    for gold, variations in tests:
        for var in variations:
            ml_score, _ = ml_engine.match(var, gold)
            base_score, _ = baseline_engine.match(var, gold)
            
            if ml_score >= 0.7:
                ml_total += 1
            if base_score >= 0.7:
                baseline_total += 1
            all_tests += 1
    
    print(f"Total test cases: {all_tests}")
    print(f"ML Model:     {ml_total}/{all_tests} ({ml_total/all_tests*100:.1f}%)")
    print(f"Baseline:     {baseline_total}/{all_tests} ({baseline_total/all_tests*100:.1f}%)")
    print(f"Improvement:  +{ml_total - baseline_total} matches")
    
    return ml_total, baseline_total, all_tests


def main():
    ml_engine = MatchingEngine(use_ml=True, use_symbolic=True)
    baseline_engine = MatchingEngine(use_ml=False, use_symbolic=True)
    
    print("\nTesting Model on Maths and Physics Paraphrases")
    print("=" * 60)
    
    ml_m, base_m, total_m = test_subject(MATHS_TESTS, "MATHS", ml_engine, baseline_engine)
    ml_p, base_p, total_p = test_subject(PHYSICS_TESTS, "PHYSICS", ml_engine, baseline_engine)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Overall: {ml_m + ml_p}/{total_m + total_p} ML vs {base_m + base_p}/{total_m + total_p} Baseline")
    print(f"ML Model: {(ml_m + ml_p)/(total_m + total_p)*100:.1f}%")
    print(f"Baseline: {(base_m + base_p)/(total_m + total_p)*100:.1f}%")
    

if __name__ == '__main__':
    main()
