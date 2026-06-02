"""
Optimal student-step ↔ gold-step assignment for multi-step grading.

Uses the Hungarian algorithm so a student step is matched to the best rubric
step globally (not greedy first-come-first-served), then scores via symbolic +
semantic matchers.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment

from math_grader import MathGrader, Step as MathStep, StepEvaluation, StepStatus
from grading.matching_engine import MatchingEngine

logger = logging.getLogger(__name__)


def _pair_score(
    student_text: str,
    gold_content: str,
    math_grader: MathGrader,
    matcher: MatchingEngine,
    question_context: Optional[Dict],
) -> Tuple[float, str]:
    """Best score across symbolic and semantic strategies for one pair."""
    sym_score, sym_desc = math_grader._compare_steps(student_text, gold_content)
    sem_score, sem_strat = matcher.match(student_text, gold_content, question_context)
    if sem_score > sym_score:
        return sem_score, sem_strat
    return sym_score, f"symbolic:{sym_desc}"


def optimal_step_assignment(
    student_steps: List[str],
    gold_steps: List[MathStep],
    math_grader: MathGrader,
    matcher: MatchingEngine,
    question_context: Optional[Dict] = None,
    min_score: float = 0.32,
) -> List[Tuple[int, int, float, str]]:
    """
    Return (student_index, gold_index, score, strategy) assignments.
    Each gold step matches at most one student step and vice versa.
    """
    n_s = len(student_steps)
    n_g = len(gold_steps)
    if n_s == 0 or n_g == 0:
        return []

    matrix = np.zeros((n_s, n_g), dtype=float)
    strategies: Dict[Tuple[int, int], str] = {}
    for i, stu in enumerate(student_steps):
        if not (stu or "").strip():
            continue
        for j, gold in enumerate(gold_steps):
            score, strat = _pair_score(
                stu, gold.content, math_grader, matcher, question_context
            )
            matrix[i, j] = score
            strategies[(i, j)] = strat

    row_ind, col_ind = linear_sum_assignment(-matrix)
    out: List[Tuple[int, int, float, str]] = []
    for r, c in zip(row_ind, col_ind):
        score = float(matrix[r, c])
        if score >= min_score:
            out.append((int(r), int(c), score, strategies.get((r, c), "")))
    return out


def grade_with_optimal_assignment(
    student_steps: List[str],
    gold_steps: List[MathStep],
    question_context: Optional[Dict] = None,
    min_match_score: float = 0.32,
) -> Dict[str, Any]:
    """
    Grade using globally optimal step matching.

    Returns the same shape as MathGrader.grade() with extra keys:
      - assignment: list of (student_idx, gold_idx, score)
      - unmatched_gold: indices of rubric steps with no student match
    """
    if not gold_steps:
        return {
            "evaluations": [],
            "total_score": 0.0,
            "max_score": 0.0,
            "percentage": 0.0,
            "assignment": [],
            "unmatched_gold": [],
        }

    cleaned = [s.strip() for s in student_steps if s and s.strip()]
    math_grader = MathGrader(gold_steps)
    matcher = MatchingEngine(use_symbolic=True, use_ml=True, similarity_threshold=0.55)

    pairs = optimal_step_assignment(
        cleaned,
        gold_steps,
        math_grader,
        matcher,
        question_context,
        min_score=min_match_score,
    )

    matched_gold: set = set()
    evaluations: List[Optional[StepEvaluation]] = [None] * len(cleaned)

    for si, gj, score, strat in pairs:
        gold = gold_steps[gj]
        matched_gold.add(gj)
        if score >= 0.92:
            status = StepStatus.CORRECT
            pts = float(gold.points)
            fb = f"Correct — matches rubric step {gj + 1} ({strat})"
        elif score >= 0.48:
            status = StepStatus.PARTIALLY_CORRECT
            pts = round(float(gold.points) * min(1.0, score), 2)
            fb = f"Partially correct ({score:.0%}) — rubric step {gj + 1} ({strat})"
        else:
            status = StepStatus.PARTIALLY_CORRECT
            pts = round(float(gold.points) * score * 0.75, 2)
            fb = f"Weak match ({score:.0%}) — rubric step {gj + 1} ({strat})"
        evaluations[si] = StepEvaluation(status, pts, fb, gj)

    for i in range(len(cleaned)):
        if evaluations[i] is None:
            evaluations[i] = StepEvaluation(
                StepStatus.INCORRECT,
                0.0,
                "Extra step — does not match any rubric item",
                None,
            )

    unmatched_gold = [j for j in range(len(gold_steps)) if j not in matched_gold]
    total = sum(ev.points_earned for ev in evaluations if ev)
    max_score = sum(float(g.points) for g in gold_steps)

    return {
        "evaluations": evaluations,
        "total_score": round(total, 2),
        "max_score": max_score,
        "percentage": (total / max_score * 100) if max_score > 0 else 0.0,
        "assignment": [(si, gj, sc) for si, gj, sc, _ in pairs],
        "unmatched_gold": unmatched_gold,
        "student_steps_for_storage": cleaned,
    }
