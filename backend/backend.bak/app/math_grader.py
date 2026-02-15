from typing import List, Dict, Optional, Tuple
from enum import Enum
import re
import sys
from pathlib import Path
from sympy import simplify, Eq, parse_expr
from sympy.parsing.sympy_parser import parse_expr as parse_expr_safe

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from grading.matching_engine import MatchingEngine as MLMatchingEngine
    ML_MATCHING_AVAILABLE = True
except ImportError:
    ML_MATCHING_AVAILABLE = False
    MLMatchingEngine = None


class StepStatus(Enum):
    CORRECT = "Correct"
    PARTIALLY_CORRECT = "Partially correct"
    INCORRECT = "Incorrect"


class Step:
    def __init__(self, content: str, points: float = 1.0, required: bool = True):
        self.content = content.strip()
        self.points = points
        self.required = required
    
    def __repr__(self):
        return f"Step('{self.content}', points={self.points}, required={self.required})"


class StepEvaluation:
    def __init__(self, status: StepStatus, points_earned: float, 
                 feedback: str = "", matched_gold_step: Optional[int] = None):
        self.status = status
        self.points_earned = points_earned
        self.feedback = feedback
        self.matched_gold_step = matched_gold_step

    def __repr__(self):
        return f"StepEvaluation(status={self.status.value}, points={self.points_earned}, feedback='{self.feedback}')"


class MathGrader:
    def __init__(self, gold_steps: List[Step], tolerance: float = 1e-6, use_ml: bool = True):
        self.gold_steps = gold_steps
        self.tolerance = tolerance
        self.total_points = sum(step.points for step in gold_steps)
        self.use_ml = use_ml and ML_MATCHING_AVAILABLE

        if self.use_ml:
            try:
                self.ml_matcher = MLMatchingEngine(
                    use_symbolic=True,
                    similarity_threshold=0.6,
                    use_ml=True
                )
            except Exception as e:
                import logging
                logging.warning(f"Could not initialize ML matcher: {e}")
                self.use_ml = False
                self.ml_matcher = None
        else:
            self.ml_matcher = None
    
    def grade(self, student_steps: List[str]) -> Dict:
        evaluations = []
        used_gold_indices = set()
        
        for i, student_step in enumerate(student_steps):
            evaluation = self._evaluate_step(
                student_step, 
                i, 
                used_gold_indices,
                evaluations
            )
            evaluations.append(evaluation)
        
        total_score = sum(eval_obj.points_earned for eval_obj in evaluations)
        
        return {
            "evaluations": evaluations,
            "total_score": total_score,
            "max_score": self.total_points,
            "percentage": (total_score / self.total_points * 100) if self.total_points > 0 else 0
        }
    
    def _evaluate_step(self, student_step: str, student_index: int,
                      used_gold_indices: set, previous_evaluations: List[StepEvaluation]) -> StepEvaluation:
        best_match = None
        best_score = 0.0
        best_gold_index = None
        missing_required = self._check_missing_required_steps(
            student_index, previous_evaluations
        )
        for gold_idx, gold_step in enumerate(self.gold_steps):
            if gold_idx in used_gold_indices:
                continue
            
            match_score, match_type = self._compare_steps(student_step, gold_step.content)
            
            if match_score > best_score:
                best_score = match_score
                best_match = match_type
                best_gold_index = gold_idx

        if best_score >= 1.0:
            status = StepStatus.CORRECT
            points = self.gold_steps[best_gold_index].points
            feedback = f"Correct: matches step {best_gold_index + 1}"
            used_gold_indices.add(best_gold_index)
        elif best_score >= 0.5:
            status = StepStatus.PARTIALLY_CORRECT
            points = self.gold_steps[best_gold_index].points * best_score
            feedback = f"Partially correct: {best_match}"
            used_gold_indices.add(best_gold_index)
        else:
            status = StepStatus.INCORRECT
            points = 0.0
            feedback = "Incorrect or not matching any expected step"

        if missing_required and status != StepStatus.INCORRECT:
            points *= 0.5
            feedback += " (reduced due to missing earlier required steps)"
        
        return StepEvaluation(status, points, feedback, best_gold_index)
    
    def _check_missing_required_steps(self, current_index: int,
                                     previous_evaluations: List[StepEvaluation]) -> bool:
        if current_index == 0:
            return False
        for i in range(min(current_index, len(self.gold_steps))):
            if self.gold_steps[i].required:
                matched = any(
                    eval_obj.matched_gold_step == i 
                    for eval_obj in previous_evaluations
                )
                if not matched:
                    return True
        return False
    
    def _compare_steps(self, student_step: str, gold_step: str) -> Tuple[float, str]:
        if self.use_ml and self.ml_matcher:
            try:
                score, strategy = self.ml_matcher.match(student_step, gold_step, question_context=None)
                if score > 0:
                    return (score, strategy)
            except Exception as e:
                import logging
                logging.debug(f"ML matching failed, falling back to traditional: {e}")

        student_step = student_step.strip()
        gold_step = gold_step.strip()
        if student_step == gold_step:
            return (1.0, "exact match")
        math_score = self._check_mathematical_equivalence(student_step, gold_step)
        if math_score > 0:
            return (math_score, "mathematically equivalent")
        derivation_score = self._check_derivation(student_step, gold_step)
        if derivation_score > 0:
            return (derivation_score, "valid intermediate derivation")
        text_similarity = self._text_similarity(student_step, gold_step)
        if text_similarity > 0.7:
            return (text_similarity * 0.8, "similar explanation")
        
        return (0.0, "no match")
    
    def _check_mathematical_equivalence(self, student: str, gold: str) -> float:
        try:
            student_expr = self._parse_expression(student)
            gold_expr = self._parse_expression(gold)
            
            if student_expr is None or gold_expr is None:
                return 0.0
            diff = simplify(student_expr - gold_expr)
            if diff == 0:
                return 1.0
            try:
                if abs(float(diff)) < self.tolerance:
                    return 1.0
            except:
                pass
            if isinstance(student_expr, Eq) and isinstance(gold_expr, Eq):
                if simplify(student_expr.lhs - gold_expr.lhs) == 0 and \
                   simplify(student_expr.rhs - gold_expr.rhs) == 0:
                    return 1.0
            
        except Exception:
            return 0.0
        return 0.0

    def _check_derivation(self, student: str, gold: str) -> float:
        try:
            student_expr = self._parse_expression(student)
            gold_expr = self._parse_expression(gold)
            
            if student_expr is None or gold_expr is None:
                return 0.0
            student_str = str(student_expr)
            gold_str = str(gold_expr)
            if student_str in gold_str or gold_str in student_str:
                return 0.6
            student_terms = set(str(student_expr).replace(' ', '').split('+'))
            gold_terms = set(str(gold_expr).replace(' ', '').split('+'))
            common = student_terms.intersection(gold_terms)
            if len(common) > 0 and len(common) / max(len(student_terms), len(gold_terms)) > 0.5:
                return 0.5
            
        except:
            pass
        
        return 0.0
    
    def _parse_expression(self, text: str):
        text = re.sub(r'^(step\s*\d*:?\s*|=)', '', text, flags=re.IGNORECASE)
        text = text.strip()
        if '=' in text:
            parts = text.split('=', 1)
            try:
                lhs = parse_expr_safe(parts[0].strip(), transformations='all')
                rhs = parse_expr_safe(parts[1].strip(), transformations='all')
                return Eq(lhs, rhs)
            except:
                pass
        try:
            return parse_expr_safe(text, transformations='all')
        except:
            pass
        
        return None
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if len(words1) == 0 and len(words2) == 0:
            return 1.0
        if len(words1) == 0 or len(words2) == 0:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if len(union) > 0 else 0.0


def create_grader_from_rubric(gold_steps: List[Tuple[str, float, bool]]) -> MathGrader:
    steps = [Step(content, points, required) for content, points, required in gold_steps]
    return MathGrader(steps)

