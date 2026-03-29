from typing import List, Dict, Optional, Tuple
import logging
import re

from math_grader import MathGrader, Step as MathStep, StepEvaluation, StepStatus as MathStepStatus
from grading.scoring_engine import ScoringEngine
from grading.matching_engine import MatchingEngine
from grading.step import Step as GradingStep, GradedStep, StepStatus as GradingStepStatus

logger = logging.getLogger(__name__)


def _prose_match_candidate_segments(full_text: str) -> List[str]:
    """
    Build overlapping shards (full answer, sentences, lines, windows) so rubric
    lines can match prose extracted from PDFs even when the student did not
    break work into numbered steps.
    """
    full_text = (full_text or "").strip()
    if not full_text:
        return []
    seen: set = set()
    out: List[str] = []

    def add_fragment(s: str) -> None:
        s = (s or "").strip()
        if len(s) < 10:
            return
        key = s[:160].lower()
        if key in seen:
            return
        seen.add(key)
        out.append(s)

    add_fragment(full_text)
    for piece in re.split(r"(?<=[.!?])\s+", full_text):
        add_fragment(piece)
    for line in full_text.splitlines():
        add_fragment(line.strip())
    if len(full_text) > 200 and len(out) < 5:
        window = 200
        step = max(60, window // 2)
        for i in range(0, max(1, len(full_text) - 50), step):
            add_fragment(full_text[i : i + window])
    return out if out else [full_text]


def _try_prose_rubric_grade(full_text: str, gold_steps: List[MathStep]) -> Optional[Dict]:
    """
    Match each rubric item to the best passage in the full answer (greedy, no
    segment reuse). Used when step-by-step math/ML grading returns zero points
    but the answer is long-form text (common for PDF uploads).
    """
    full_text = (full_text or "").strip()
    if len(full_text) < 30 or not gold_steps:
        return None

    segs = _prose_match_candidate_segments(full_text)
    matcher = MatchingEngine(use_symbolic=True, use_ml=True, similarity_threshold=0.42)
    used_seg: set = set()
    evaluations: List[StepEvaluation] = []
    display_steps: List[str] = []
    total = 0.0
    max_score = sum(float(gs.points) for gs in gold_steps)

    for gi, gold in enumerate(gold_steps):
        gtext = (gold.content or "").strip()
        if not gtext:
            evaluations.append(
                StepEvaluation(
                    MathStepStatus.INCORRECT,
                    0.0,
                    "Empty rubric item",
                    matched_gold_step=None,
                )
            )
            display_steps.append("—")
            continue

        best_j: Optional[int] = None
        best_score = 0.0
        best_strat = ""
        for j, seg in enumerate(segs):
            if j in used_seg:
                continue
            score, strat = matcher.match(seg, gtext, None)
            if score > best_score:
                best_score = score
                best_j = j
                best_strat = strat

        if best_j is not None and best_score >= 0.36:
            used_seg.add(best_j)
            seg_text = segs[best_j]
            if best_score >= 0.9:
                status = MathStepStatus.CORRECT
                pts = float(gold.points)
            elif best_score >= 0.5:
                status = MathStepStatus.PARTIALLY_CORRECT
                pts = round(float(gold.points) * min(1.0, best_score), 2)
            else:
                status = MathStepStatus.PARTIALLY_CORRECT
                pts = round(float(gold.points) * best_score * 0.78, 2)
            pts = min(pts, float(gold.points))
            fb = f"Rubric match ({best_strat}, {best_score:.0%})"
            evaluations.append(
                StepEvaluation(status, pts, fb, matched_gold_step=gi)
            )
            display_steps.append(seg_text if len(seg_text) <= 2000 else seg_text[:1997] + "...")
            total += pts
        else:
            evaluations.append(
                StepEvaluation(
                    MathStepStatus.INCORRECT,
                    0.0,
                    "No passage in the answer clearly matches this rubric item",
                    matched_gold_step=None,
                )
            )
            display_steps.append("—")

    if total <= 0 or len(evaluations) != len(gold_steps):
        return None

    return {
        "evaluations": evaluations,
        "total_score": round(total, 2),
        "max_score": max_score,
        "strategies_used": ["prose_rubric"] * len(evaluations),
        "student_steps_for_storage": display_steps,
    }


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

        combined = "\n".join(s.strip() for s in student_steps if s and s.strip()).strip()
        if (
            results["total_score"] == 0
            and results.get("max_score", 0) > 0
            and len(combined) >= 40
        ):
            prose = _try_prose_rubric_grade(combined, self.gold_steps)
            if prose and prose["total_score"] > results["total_score"]:
                results = prose
                results["percentage"] = (
                    (results["total_score"] / results["max_score"] * 100)
                    if results["max_score"] > 0
                    else 0.0
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
