"""
Mathematical Problem Step-by-Step Grading Model

This module provides a grading system that evaluates student solutions
step-by-step against a gold standard solution.
"""

from typing import List, Dict, Optional, Tuple
from enum import Enum
import re
from sympy import sympify, simplify, Symbol, symbols, Eq, parse_expr
from sympy.parsing.sympy_parser import parse_expr as parse_expr_safe


class StepStatus(Enum):
    """Status of a step evaluation"""
    CORRECT = "Correct"
    PARTIALLY_CORRECT = "Partially correct"
    INCORRECT = "Incorrect"


class Step:
    """Represents a single step in a solution"""
    
    def __init__(self, content: str, points: float = 1.0, required: bool = True):
        """
        Args:
            content: The mathematical expression or explanation
            points: Points awarded for this step
            required: Whether this step is required for later steps to be valid
        """
        self.content = content.strip()
        self.points = points
        self.required = required
    
    def __repr__(self):
        return f"Step('{self.content}', points={self.points}, required={self.required})"


class StepEvaluation:
    """Result of evaluating a student step"""
    
    def __init__(self, status: StepStatus, points_earned: float, 
                 feedback: str = "", matched_gold_step: Optional[int] = None):
        self.status = status
        self.points_earned = points_earned
        self.feedback = feedback
        self.matched_gold_step = matched_gold_step  # Index of matched gold step
    
    def __repr__(self):
        return f"StepEvaluation(status={self.status.value}, points={self.points_earned}, feedback='{self.feedback}')"


class MathGrader:
    """
    Grades mathematical problems step-by-step.
    
    Compares student solutions against gold standard solutions,
    evaluating each step for correctness, partial correctness, or incorrectness.
    """
    
    def __init__(self, gold_steps: List[Step], tolerance: float = 1e-6):
        """
        Args:
            gold_steps: List of gold standard steps with their point values
            tolerance: Numerical tolerance for floating point comparisons
        """
        self.gold_steps = gold_steps
        self.tolerance = tolerance
        self.total_points = sum(step.points for step in gold_steps)
    
    def grade(self, student_steps: List[str]) -> Dict:
        """
        Grade a student solution step-by-step.
        
        Args:
            student_steps: List of student step strings
        
        Returns:
            Dictionary with:
                - evaluations: List of StepEvaluation objects
                - total_score: Total points earned
                - max_score: Maximum possible points
                - percentage: Score as percentage
        """
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
        """
        Evaluate a single student step against gold steps.
        
        Args:
            student_step: The student's step content
            student_index: Index of this step in student solution
            used_gold_indices: Set of gold step indices already matched
            previous_evaluations: Previous step evaluations
        
        Returns:
            StepEvaluation object
        """
        best_match = None
        best_score = 0.0
        best_gold_index = None
        
        # Check if earlier required steps were missed
        missing_required = self._check_missing_required_steps(
            student_index, previous_evaluations
        )
        
        # Try to match against each gold step
        for gold_idx, gold_step in enumerate(self.gold_steps):
            if gold_idx in used_gold_indices:
                continue
            
            match_score, match_type = self._compare_steps(student_step, gold_step.content)
            
            if match_score > best_score:
                best_score = match_score
                best_match = match_type
                best_gold_index = gold_idx
        
        # Determine status and points
        if best_score >= 1.0:  # Exact or equivalent match
            status = StepStatus.CORRECT
            points = self.gold_steps[best_gold_index].points
            feedback = f"Correct: matches step {best_gold_index + 1}"
            used_gold_indices.add(best_gold_index)
        elif best_score >= 0.5:  # Partial match
            status = StepStatus.PARTIALLY_CORRECT
            points = self.gold_steps[best_gold_index].points * best_score
            feedback = f"Partially correct: {best_match}"
            used_gold_indices.add(best_gold_index)
        else:
            status = StepStatus.INCORRECT
            points = 0.0
            feedback = "Incorrect or not matching any expected step"
        
        # Penalize if required earlier steps were missed
        if missing_required and status != StepStatus.INCORRECT:
            # Reduce points if earlier required steps were skipped
            points *= 0.5
            feedback += " (reduced due to missing earlier required steps)"
        
        return StepEvaluation(status, points, feedback, best_gold_index)
    
    def _check_missing_required_steps(self, current_index: int, 
                                     previous_evaluations: List[StepEvaluation]) -> bool:
        """
        Check if required steps before current step were missed.
        
        Returns:
            True if required steps were missed
        """
        if current_index == 0:
            return False
        
        # Check if any required gold steps before current position were not matched
        for i in range(min(current_index, len(self.gold_steps))):
            if self.gold_steps[i].required:
                # Check if this step was matched in previous evaluations
                matched = any(
                    eval_obj.matched_gold_step == i 
                    for eval_obj in previous_evaluations
                )
                if not matched:
                    return True
        return False
    
    def _compare_steps(self, student_step: str, gold_step: str) -> Tuple[float, str]:
        """
        Compare a student step with a gold step.
        
        Returns:
            Tuple of (score 0-1, match_type description)
        """
        # Normalize whitespace
        student_step = student_step.strip()
        gold_step = gold_step.strip()
        
        # 1. Exact match
        if student_step == gold_step:
            return (1.0, "exact match")
        
        # 2. Try mathematical equivalence
        math_score = self._check_mathematical_equivalence(student_step, gold_step)
        if math_score > 0:
            return (math_score, "mathematically equivalent")
        
        # 3. Check if it's a valid intermediate derivation
        derivation_score = self._check_derivation(student_step, gold_step)
        if derivation_score > 0:
            return (derivation_score, "valid intermediate derivation")
        
        # 4. Partial text similarity (for explanations)
        text_similarity = self._text_similarity(student_step, gold_step)
        if text_similarity > 0.7:
            return (text_similarity * 0.8, "similar explanation")
        
        return (0.0, "no match")
    
    def _check_mathematical_equivalence(self, student: str, gold: str) -> float:
        """
        Check if two mathematical expressions are equivalent.
        
        Returns:
            Score between 0 and 1
        """
        try:
            # Try to parse as mathematical expressions
            student_expr = self._parse_expression(student)
            gold_expr = self._parse_expression(gold)
            
            if student_expr is None or gold_expr is None:
                return 0.0
            
            # Check if they simplify to the same expression
            diff = simplify(student_expr - gold_expr)
            
            # If difference is zero (or very close), they're equivalent
            if diff == 0:
                return 1.0
            
            # Check if it's a constant close to zero (for numerical expressions)
            try:
                if abs(float(diff)) < self.tolerance:
                    return 1.0
            except:
                pass
            
            # Check if they're equal as equations
            if isinstance(student_expr, Eq) and isinstance(gold_expr, Eq):
                if simplify(student_expr.lhs - gold_expr.lhs) == 0 and \
                   simplify(student_expr.rhs - gold_expr.rhs) == 0:
                    return 1.0
            
        except Exception as e:
            # If parsing fails, they're not equivalent expressions
            return 0.0
        
        return 0.0
    
    def _check_derivation(self, student: str, gold: str) -> float:
        """
        Check if student step is a valid intermediate derivation leading to gold step.
        
        This is a heuristic check - it looks for common patterns like:
        - Student has part of the gold expression
        - Student shows work that would lead to gold step
        
        Returns:
            Score between 0 and 1
        """
        try:
            student_expr = self._parse_expression(student)
            gold_expr = self._parse_expression(gold)
            
            if student_expr is None or gold_expr is None:
                return 0.0
            
            # Check if student expression appears in gold expression's structure
            # This is a simplified heuristic
            student_str = str(student_expr)
            gold_str = str(gold_expr)
            
            # If student expression is a sub-expression of gold
            if student_str in gold_str or gold_str in student_str:
                return 0.6
            
            # Check if they share significant common terms
            student_terms = set(str(student_expr).replace(' ', '').split('+'))
            gold_terms = set(str(gold_expr).replace(' ', '').split('+'))
            common = student_terms.intersection(gold_terms)
            if len(common) > 0 and len(common) / max(len(student_terms), len(gold_terms)) > 0.5:
                return 0.5
            
        except:
            pass
        
        return 0.0
    
    def _parse_expression(self, text: str):
        """
        Try to parse a text string as a mathematical expression.
        
        Returns:
            SymPy expression or None if parsing fails
        """
        # Remove common prefixes like "=", "Step:", etc.
        text = re.sub(r'^(step\s*\d*:?\s*|=)', '', text, flags=re.IGNORECASE)
        text = text.strip()
        
        # Try to extract mathematical expressions
        # Look for equations (contains =)
        if '=' in text:
            parts = text.split('=', 1)
            try:
                lhs = parse_expr_safe(parts[0].strip(), transformations='all')
                rhs = parse_expr_safe(parts[1].strip(), transformations='all')
                return Eq(lhs, rhs)
            except:
                pass
        
        # Try as single expression
        try:
            return parse_expr_safe(text, transformations='all')
        except:
            pass
        
        return None
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Simple text similarity metric (for non-mathematical explanations).
        
        Returns:
            Similarity score between 0 and 1
        """
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
    """
    Helper function to create a grader from a list of tuples.
    
    Args:
        gold_steps: List of (content, points, required) tuples
    
    Returns:
        MathGrader instance
    """
    steps = [Step(content, points, required) for content, points, required in gold_steps]
    return MathGrader(steps)

