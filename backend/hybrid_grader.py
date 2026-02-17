from typing import List, Dict, Optional, Tuple
import logging

from math_grader import MathGrader, Step as MathStep, StepEvaluation, StepStatus as MathStepStatus
from grading.scoring_engine import ScoringEngine
from grading.matching_engine import MatchingEngine
from grading.step import Step as GradingStep, GradedStep, StepStatus as GradingStepStatus

logger = logging.getLogger(__name__)


class HybridGrader:
    def __init__(self, 
                 gold_steps: List[MathStep],
                 use_ml: bool = True,
                 use_symbolic: bool = True,
                 question_context: Optional[Dict] = None):
        self.gold_steps = gold_steps
        self.use_ml = use_ml
        self.use_symbolic = use_symbolic
        self.question_context = question_context or {}
        
        if self.use_symbolic:
            self.math_grader = MathGrader(gold_steps)
        else:
            self.math_grader = None
        
        if self.use_ml:
            grading_steps = self._convert_to_grading_steps(gold_steps)
            matching_engine = MatchingEngine(
                use_symbolic=self.use_symbolic,
                use_ml=True,
                similarity_threshold=0.6
            )
            self.scoring_engine = ScoringEngine(matching_engine=matching_engine)
            self.grading_steps = grading_steps
        else:
            self.scoring_engine = None
            self.grading_steps = None
    
    def _convert_to_grading_steps(self, math_steps: List[MathStep]) -> List[GradingStep]:
        return [
            GradingStep(
                text=step.content,
                points=int(step.points),
                required=step.required,
                step_number=i + 1
            )
            for i, step in enumerate(math_steps)
        ]
    
    def grade(self, student_steps: List[str]) -> Dict:
        results = {
            'evaluations': [],
            'total_score': 0.0,
            'max_score': sum(step.points for step in self.gold_steps),
            'percentage': 0.0,
            'strategies_used': []
        }
        
        math_result = None
        ml_result = None
        
        if self.math_grader:
            try:
                math_result = self.math_grader.grade(student_steps)
                logger.debug(f"MathGrader: {math_result['total_score']}/{math_result['max_score']}")
            except Exception as e:
                logger.warning(f"MathGrader failed: {e}")
        
        if self.scoring_engine:
            try:
                ml_graded_steps, ml_summary = self.scoring_engine.grade_submission(
                    student_steps,
                    self.grading_steps
                )
                ml_result = {
                    'graded_steps': ml_graded_steps,
                    'summary': ml_summary,
                    'total_score': ml_summary['total_points_earned'],
                    'max_score': ml_summary['total_points_possible']
                }
                logger.debug(f"ML Grader: {ml_result['total_score']}/{ml_result['max_score']}")
            except Exception as e:
                logger.warning(f"ML Grader failed: {e}")
        
        if math_result and ml_result:
            results = self._combine_results(student_steps, math_result, ml_result)
        elif math_result:
            results = self._convert_math_result(math_result)
        elif ml_result:
            results = self._convert_ml_result(ml_result)
        else:
            logger.error("Both grading systems failed")
            results['evaluations'] = [
                StepEvaluation(
                    status=MathStepStatus.INCORRECT,
                    points_earned=0.0,
                    feedback="Grading system error"
                )
                for _ in student_steps
            ]
        
        results['percentage'] = (
            (results['total_score'] / results['max_score'] * 100) 
            if results['max_score'] > 0 else 0.0
        )
        
        return results
    
    def _combine_results(self, 
                        student_steps: List[str],
                        math_result: Dict,
                        ml_result: Dict) -> Dict:
        combined_evaluations = []
        strategies_used = []
        
        math_evals = math_result['evaluations']
        ml_graded_steps = ml_result['graded_steps']
        
        max_len = max(len(math_evals), len(ml_graded_steps), len(student_steps))
        
        for i in range(max_len):
            math_eval = math_evals[i] if i < len(math_evals) else None
            ml_step = ml_graded_steps[i] if i < len(ml_graded_steps) else None
            
            math_score = math_eval.points_earned if math_eval else 0.0
            ml_score = ml_step.points_earned if ml_step else 0.0
            
            if math_score >= ml_score:
                combined_eval = math_eval
                strategy = "symbolic"
                if math_eval and hasattr(math_eval, 'feedback'):
                    combined_eval.feedback = math_eval.feedback
            else:
                combined_eval = self._convert_ml_step_to_math_eval(ml_step, i)
                strategy = "semantic"
            
            combined_evaluations.append(combined_eval)
            strategies_used.append(strategy)
        
        total_score = sum(eval_obj.points_earned for eval_obj in combined_evaluations)
        
        return {
            'evaluations': combined_evaluations,
            'total_score': total_score,
            'max_score': math_result['max_score'],
            'strategies_used': strategies_used
        }
    
    def _convert_ml_step_to_math_eval(self, ml_step: GradedStep, index: int) -> StepEvaluation:
        status_map = {
            GradingStepStatus.CORRECT: MathStepStatus.CORRECT,
            GradingStepStatus.PARTIALLY_CORRECT: MathStepStatus.PARTIALLY_CORRECT,
            GradingStepStatus.INCORRECT: MathStepStatus.INCORRECT
        }
        
        matched_gold_index = None
        if ml_step.matched_gold_step:
            for i, gold_step in enumerate(self.gold_steps):
                if gold_step.content == ml_step.matched_gold_step.text:
                    matched_gold_index = i
                    break
        
        return StepEvaluation(
            status=status_map.get(ml_step.status, MathStepStatus.INCORRECT),
            points_earned=ml_step.points_earned,
            feedback=ml_step.feedback,
            matched_gold_step=matched_gold_index
        )
    
    def _convert_math_result(self, math_result: Dict) -> Dict:
        return {
            'evaluations': math_result['evaluations'],
            'total_score': math_result['total_score'],
            'max_score': math_result['max_score'],
            'strategies_used': ['symbolic'] * len(math_result['evaluations'])
        }
    
    def _convert_ml_result(self, ml_result: Dict) -> Dict:
        evaluations = []
        for i, ml_step in enumerate(ml_result['graded_steps']):
            eval_obj = self._convert_ml_step_to_math_eval(ml_step, i)
            evaluations.append(eval_obj)
        
        return {
            'evaluations': evaluations,
            'total_score': ml_result['total_score'],
            'max_score': ml_result['max_score'],
            'strategies_used': ['semantic'] * len(evaluations)
        }
