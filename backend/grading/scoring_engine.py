"""
Scoring Engine - Calculates points with penalties for missing required steps
"""
from typing import List, Dict, Tuple
from .step import Step, GradedStep, StepStatus
from .matching_engine import MatchingEngine
import logging

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Engine for scoring student submissions with penalties for missing required steps.
    """
    
    def __init__(self, 
                 matching_engine: MatchingEngine = None,
                 penalty_factor: float = 0.5):
        """
        Initialize scoring engine.
        
        Args:
            matching_engine: Engine for matching steps
            penalty_factor: Factor to multiply points by when required step is missing
        """
        self.matching_engine = matching_engine or MatchingEngine()
        self.penalty_factor = penalty_factor
    
    def grade_submission(self,
                        student_steps: List[str],
                        gold_solution: List[Step]) -> Tuple[List[GradedStep], Dict]:
        """
        Grade a student submission against the gold solution.
        
        Args:
            student_steps: List of student's step texts
            gold_solution: List of gold Step objects
            
        Returns:
            (graded_steps, summary) where summary contains total points, percentage, etc.
        """
        graded_steps = []
        matched_gold_indices = set()
        missing_required_steps = []
        
        # Track which required steps are missing
        for i, gold_step in enumerate(gold_solution):
            if gold_step.required:
                missing_required_steps.append(i)
        
        # Grade each student step
        for student_text in student_steps:
            if not student_text.strip():
                continue
            
            # Find best matching gold step
            best_index, match_score, strategy = self.matching_engine.find_best_match(
                student_text,
                [gold_solution[i] for i in range(len(gold_solution)) if i not in matched_gold_indices]
            )
            
            # Adjust index to account for already matched steps
            if best_index is not None:
                available_indices = [i for i in range(len(gold_solution)) if i not in matched_gold_indices]
                actual_index = available_indices[best_index]
                best_index = actual_index
            
            if best_index is not None:
                gold_step = gold_solution[best_index]
                matched_gold_indices.add(best_index)
                
                # Remove from missing required if matched
                if gold_step.required and best_index in missing_required_steps:
                    missing_required_steps.remove(best_index)
                
                # Calculate points
                base_points = gold_step.points * match_score
                
                # Apply penalty if required earlier steps are missing
                penalty_applied = False
                earlier_required_missing = [idx for idx in missing_required_steps if idx < best_index]
                
                if earlier_required_missing:
                    base_points *= self.penalty_factor
                    penalty_applied = True
                
                # Determine status
                if match_score >= 0.95:
                    status = StepStatus.CORRECT
                elif match_score >= 0.5:
                    status = StepStatus.PARTIALLY_CORRECT
                else:
                    status = StepStatus.INCORRECT
                
                graded_step = GradedStep(
                    student_text=student_text,
                    matched_gold_step=gold_step,
                    status=status,
                    points_earned=round(base_points, 2),
                    points_possible=gold_step.points,
                    match_score=match_score,
                    feedback=self._generate_step_feedback(status, match_score, strategy, penalty_applied),
                    penalty_applied=penalty_applied
                )
            else:
                # No match found
                graded_step = GradedStep(
                    student_text=student_text,
                    matched_gold_step=None,
                    status=StepStatus.INCORRECT,
                    points_earned=0.0,
                    points_possible=0,
                    match_score=0.0,
                    feedback="No matching step found in gold solution",
                    penalty_applied=False
                )
            
            graded_steps.append(graded_step)
        
        # Check for missing required steps
        for gold_index in missing_required_steps:
            gold_step = gold_solution[gold_index]
            logger.info(f"Required step missing: {gold_step.text}")
        
        # Calculate summary
        summary = self._calculate_summary(graded_steps, gold_solution, missing_required_steps)
        
        return graded_steps, summary
    
    def _generate_step_feedback(self,
                                status: StepStatus,
                                match_score: float,
                                strategy: str,
                                penalty_applied: bool) -> str:
        """Generate feedback message for a graded step"""
        feedback_parts = []
        
        if status == StepStatus.CORRECT:
            feedback_parts.append("✓ Correct!")
            if strategy == "symbolic_equivalent":
                feedback_parts.append("(Mathematically equivalent)")
            elif strategy == "exact_match":
                feedback_parts.append("(Perfect match)")
        elif status == StepStatus.PARTIALLY_CORRECT:
            feedback_parts.append(f"~ Partially correct ({match_score*100:.0f}% match)")
            if strategy == "valid_derivation_substring":
                feedback_parts.append("(Valid but incomplete)")
            elif strategy == "text_similarity":
                feedback_parts.append("(Similar but not exact)")
        else:
            feedback_parts.append("✗ Incorrect")
        
        if penalty_applied:
            feedback_parts.append(f"\n⚠️ Half credit: required earlier step(s) missing")
        
        return " ".join(feedback_parts)
    
    def _calculate_summary(self,
                          graded_steps: List[GradedStep],
                          gold_solution: List[Step],
                          missing_required_steps: List[int]) -> Dict:
        """Calculate summary statistics"""
        total_earned = sum(step.points_earned for step in graded_steps)
        total_possible = sum(step.points for step in gold_solution)
        
        correct_count = sum(1 for step in graded_steps if step.status == StepStatus.CORRECT)
        partial_count = sum(1 for step in graded_steps if step.status == StepStatus.PARTIALLY_CORRECT)
        incorrect_count = sum(1 for step in graded_steps if step.status == StepStatus.INCORRECT)
        
        percentage = (total_earned / total_possible * 100) if total_possible > 0 else 0
        
        return {
            'total_points_earned': round(total_earned, 2),
            'total_points_possible': total_possible,
            'percentage': round(percentage, 2),
            'correct_steps': correct_count,
            'partial_steps': partial_count,
            'incorrect_steps': incorrect_count,
            'total_steps_graded': len(graded_steps),
            'total_steps_expected': len(gold_solution),
            'missing_required_steps': len(missing_required_steps),
            'missing_step_indices': missing_required_steps
        }

