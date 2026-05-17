#!/usr/bin/env python3
"""
Seed four full-length demo exams (Math, Biology, Physics, Chemistry) for grading UI/PDF demos.

Each paper:
  • Section A — six compulsory questions (several multi-part with (a)(b)(c))
  • Section B — three questions; instructions say to answer TWO (honour system for the demo)

Creates course "Demo examination papers" (code DEMO-PAPERS). Re-run wipes prior [DEMO] exams.

Usage (from backend/, venv active):
    python seed_demo_exams.py
    python seed_demo_exams.py --no-publish
    python seed_demo_exams.py --no-enroll
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))

import models
from database import SessionLocal, init_db

DEMO_PREFIX = "[DEMO]"
COURSE_CODE = "DEMO-PAPERS"
COURSE_NAME = "Demo examination papers"
DEMO_STUDENT_EMAIL = "student@university.edu"

# ---------------------------------------------------------------------------
# TipTap JSON helpers (graphs, math, tables, SVG “diagrams”)
# ---------------------------------------------------------------------------


def _t(text: str) -> dict:
    return {"type": "text", "text": text}


def _p(*nodes: dict) -> dict:
    return {"type": "paragraph", "content": list(nodes)}


def _h(level: int, text: str) -> dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [_t(text)]}


def _imath(latex: str) -> dict:
    return {"type": "inlineMath", "attrs": {"latex": latex}}


def _bmath(latex: str) -> dict:
    return {"type": "blockMath", "attrs": {"latex": latex}}


def _graph(
    graph_type: str,
    data: List[dict],
    title: str,
    x_label: str,
    y_label: str,
) -> dict:
    return {
        "type": "graph",
        "attrs": {
            "graphType": graph_type,
            "data": data,
            "title": title,
            "xLabel": x_label,
            "yLabel": y_label,
        },
    }


def _svg_image(svg: str) -> dict:
    src = "data:image/svg+xml;charset=utf-8," + quote(svg)
    return {"type": "image", "attrs": {"src": src, "alt": "Diagram"}}


def _table(headers: List[str], rows: List[List[str]]) -> dict:
    def cell(text: str, header: bool = False) -> dict:
        t = "tableHeader" if header else "tableCell"
        return {
            "type": t,
            "content": [{"type": "paragraph", "content": [_t(text)]}],
        }

    return {
        "type": "table",
        "content": [
            {
                "type": "tableRow",
                "content": [cell(h, True) for h in headers],
            },
            *[
                {"type": "tableRow", "content": [cell(c) for c in row]}
                for row in rows
            ],
        ],
    }


def doc(*blocks: dict) -> str:
    return json.dumps({"type": "doc", "content": list(blocks)}, ensure_ascii=False)


def _gold(
    db,
    qid: str,
    steps: List[Tuple[int, str, str, str, int, bool]],
) -> None:
    for sn, desc, expr, latex, pts, req in steps:
        db.add(
            models.GoldSolutionStep(
                question_id=qid,
                step_number=sn,
                description=desc,
                expression=expr[:500],
                latex=(latex or "")[:500],
                points=pts,
                required=req,
            )
        )


def sum_points(db, exam_id: str) -> int:
    rows = db.query(models.Question.points).filter(models.Question.exam_id == exam_id).all()
    return sum(r[0] for r in rows)


def wipe_demo_exams(db, course_id: str) -> int:
    n = 0
    exams = (
        db.query(models.Exam)
        .filter(
            models.Exam.course_id == course_id,
            models.Exam.title.like(f"{DEMO_PREFIX}%"),
        )
        .all()
    )
    for ex in exams:
        db.delete(ex)
        n += 1
    db.commit()
    return n


def ensure_enrollment(db, course_id: str, student_id: str) -> None:
    existing = (
        db.query(models.CourseEnrollment)
        .filter(
            models.CourseEnrollment.course_id == course_id,
            models.CourseEnrollment.student_id == student_id,
        )
        .first()
    )
    if existing:
        if existing.status != models.EnrollmentStatus.APPROVED:
            existing.status = models.EnrollmentStatus.APPROVED
            existing.enrolled_at = datetime.now(timezone.utc)
            db.commit()
        return
    db.add(
        models.CourseEnrollment(
            course_id=course_id,
            student_id=student_id,
            status=models.EnrollmentStatus.APPROVED,
            enrolled_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


# ---------------------------------------------------------------------------
# Shared diagram snippets
# ---------------------------------------------------------------------------

SVG_TRIANGLE = """<svg xmlns='http://www.w3.org/2000/svg' width='220' height='140'>
  <polygon points='20,120 200,120 20,30' fill='none' stroke='#111' stroke-width='2'/>
  <text x='100' y='135' font-size='12' text-anchor='middle'>5 cm</text>
  <text x='8' y='78' font-size='12'>3 cm</text>
  <text x='115' y='68' font-size='12'>θ</text>
</svg>"""

SVG_RAMP = """<svg xmlns='http://www.w3.org/2000/svg' width='240' height='120'>
  <line x1='20' y1='100' x2='200' y2='40' stroke='#111' stroke-width='3'/>
  <line x1='20' y1='100' x2='200' y2='100' stroke='#666' stroke-width='2'/>
  <text x='210' y='75' font-size='11'>m = 8.0 kg</text>
  <text x='90' y='115' font-size='11'>α = 30°</text>
</svg>"""


def add_multipart(
    db,
    exam_id: str,
    qnum: int,
    parent_text: str,
    parent_rich: Optional[str],
    subs: List[dict],
) -> None:
    parent = models.Question(
        exam_id=exam_id,
        number=qnum,
        text=parent_text,
        points=0,
        final_answer="",
        final_answer_latex="",
        question_type="multi-part",
        rich_content=parent_rich,
        outline_level=1,
    )
    db.add(parent)
    db.flush()
    for i, sub in enumerate(subs, start=1):
        sq = models.Question(
            exam_id=exam_id,
            number=i,
            text=sub["text"],
            points=sub["points"],
            final_answer=sub.get("final_answer", ""),
            final_answer_latex=sub.get("final_answer_latex", ""),
            question_type="standard",
            rich_content=sub.get("rich_content"),
            parent_question_id=parent.id,
            outline_level=2,
        )
        db.add(sq)
        db.flush()
        _gold(db, sq.id, sub["gold"])


def add_single(
    db,
    exam_id: str,
    qnum: int,
    text: str,
    points: int,
    gold: List[Tuple[int, str, str, str, int, bool]],
    final_answer: str,
    final_latex: str = "",
    rich_content: Optional[str] = None,
) -> None:
    q = models.Question(
        exam_id=exam_id,
        number=qnum,
        text=text,
        points=points,
        final_answer=final_answer,
        final_answer_latex=final_latex or "",
        question_type="standard",
        rich_content=rich_content,
        outline_level=1,
    )
    db.add(q)
    db.flush()
    _gold(db, q.id, gold)


def build_math_exam(db, course_id: str, due, pub_at, auto_publish: bool) -> None:
    desc = (
        "Time: 2 hours. Total marks shown sum all items; for Section B, answer exactly "
        "TWO of Questions 7–9 (maximum 24 marks from that section). "
        "Unless stated, show all reasoning. Calculators permitted where appropriate."
    )
    ex = models.Exam(
        course_id=course_id,
        title=f"{DEMO_PREFIX} Mathematics — Year-End Paper",
        description=desc,
        total_points=0,
        due_date=due,
        is_published=auto_publish,
        published_at=pub_at,
    )
    db.add(ex)
    db.flush()

    # Q1
    add_multipart(
        db,
        ex.id,
        1,
        "Section A — Q1. Quadratic model",
        doc(
            _h(3, "Section A — Compulsory (Questions 1–6)"),
            _p(
                _t("A ball’s height is "),
                _imath("h(t) = -5t^2 + 20t + 25"),
                _t(" metres."),
            ),
            _p(_t("(Answer all parts.)")),
        ),
        [
            {
                "text": "(a) Compute the discriminant of h(t) (treat as quadratic in t) and state the nature of the roots.",
                "points": 6,
                "final_answer": "Δ = 0, one repeated real root",
                "final_answer_latex": "\\Delta = 0",
                "gold": [
                    (1, "Expand standard form", "a=-5,b=20,c=25", "a=-5,\\; b=20,\\; c=25", 2, True),
                    (2, "Discriminant", "b^2-4ac=0", "b^2-4ac = 0", 3, True),
                    (3, "Conclusion", "one repeated real root", "\\text{repeated real root}", 1, True),
                ],
            },
            {
                "text": "(b) Find the time when the ball hits the ground (h = 0).",
                "points": 6,
                "final_answer": "t = 5",
                "final_answer_latex": "t = 5",
                "gold": [
                    (1, "Set h=0", "-5t^2+20t+25=0", "-5t^2+20t+25=0", 2, True),
                    (2, "Solve", "t=5 (positive root)", "t = 5", 4, True),
                ],
            },
        ],
    )

    # Q2 triangle
    add_multipart(
        db,
        ex.id,
        2,
        "Section A — Q2. Geometry",
        doc(
            _p(_t("The diagram shows a right triangle (right angle at the bottom-left).")),
            _svg_image(SVG_TRIANGLE),
            _p(_t("Lengths in cm as labelled.")),
        ),
        [
            {
                "text": "(a) Find sin θ.",
                "points": 5,
                "final_answer": "4/5",
                "final_answer_latex": "\\frac{4}{5}",
                "gold": [
                    (1, "Hypotenuse", "5 cm given", "5", 1, True),
                    (2, "Opposite to θ", "4 cm (Pythagoras)", "4", 2, True),
                    (3, "sin θ", "4/5", "\\frac{4}{5}", 2, True),
                ],
            },
            {
                "text": "(b) Find the area.",
                "points": 5,
                "final_answer": "6 cm²",
                "final_answer_latex": "6\\ \\text{cm}^2",
                "gold": [
                    (1, "Area formula", "(1/2)*3*4", "\\tfrac{1}{2}\\cdot 3 \\cdot 4", 3, True),
                    (2, "Value", "6", "6", 2, True),
                ],
            },
        ],
    )

    # Q3 vectors
    add_multipart(
        db,
        ex.id,
        3,
        "Section A — Q3. Vectors in ℝ²",
        doc(
            _p(_t("Let "), _imath("\\mathbf{a} = (3,4)"), _t(" and "), _imath("\\mathbf{b} = (1,-2)"), _t(".")),
        ),
        [
            {
                "text": "(a) Find ‖a‖.",
                "points": 4,
                "final_answer": "5",
                "final_answer_latex": "5",
                "gold": [
                    (1, "Formula", "sqrt(3^2+4^2)", "\\sqrt{3^2+4^2}", 2, True),
                    (2, "Result", "5", "5", 2, True),
                ],
            },
            {
                "text": "(b) Find a · b.",
                "points": 4,
                "final_answer": "-5",
                "final_answer_latex": "-5",
                "gold": [
                    (1, "Dot product", "3*1+4*(-2)=-5", "3(1)+4(-2)=-5", 4, True),
                ],
            },
        ],
    )

    # Q4 limit
    add_single(
        db,
        ex.id,
        4,
        "Section A — Q4. Evaluate lim(x→0) (sin 3x) / x.",
        8,
        [
            (1, "Standard limit", "sin(3x)/x = 3 * sin(3x)/(3x)", "3\\frac{\\sin 3x}{3x}", 4, True),
            (2, "Limit", "→ 3", "\\to 3", 4, True),
        ],
        "3",
        "3",
    )

    # Q5 AP
    add_multipart(
        db,
        ex.id,
        5,
        "Section A — Q5. Arithmetic sequence",
        doc(
            _p(_t("An AP has first term "), _imath("a_1 = 7"), _t(" and common difference "), _imath("d = 4"), _t(".")),
        ),
        [
            {
                "text": "(a) Find the 10th term.",
                "points": 4,
                "final_answer": "43",
                "final_answer_latex": "43",
                "gold": [
                    (1, "Formula", "a_n = a1+(n-1)d", "a_{10}=7+9\\cdot 4", 2, True),
                    (2, "Compute", "43", "43", 2, True),
                ],
            },
            {
                "text": "(b) Sum of first 15 terms.",
                "points": 6,
                "final_answer": "465",
                "final_answer_latex": "465",
                "gold": [
                    (1, "Sum formula", "n/2(2a1+(n-1)d)", "S_{15}=\\frac{15}{2}(14+56)", 3, True),
                    (2, "Result", "465", "465", 3, True),
                ],
            },
        ],
    )

    # Q6 derivative / tangent
    add_multipart(
        db,
        ex.id,
        6,
        "Section A — Q6. Differentiation",
        doc(
            _p(_t("Let "), _imath("f(x) = x^3 - 3x^2"), _t(".")),
        ),
        [
            {
                "text": "(a) Find f′(x).",
                "points": 5,
                "final_answer": "3x² - 6x",
                "final_answer_latex": "3x^2 - 6x",
                "gold": [
                    (1, "Power rule", "3x^2-6x", "3x^2-6x", 5, True),
                ],
            },
            {
                "text": "(b) Equation of tangent at x = 2.",
                "points": 7,
                "final_answer": "y = -4",
                "final_answer_latex": "y = -4",
                "gold": [
                    (1, "Point", "f(2)=-4", "f(2)=-4", 2, True),
                    (2, "Slope", "f'(2)=0", "f'(2)=0", 3, True),
                    (3, "Tangent line", "y=-4", "y=-4", 2, True),
                ],
            },
        ],
    )

    # Section B
    add_single(
        db,
        ex.id,
        7,
        "Section B — Q7 (choose 2 of Q7–9). Prove by induction that ∑_{k=1}^{n} k = n(n+1)/2.",
        12,
        [
            (1, "Base case", "n=1 holds", "n=1", 3, True),
            (2, "Inductive hypothesis", "assume true for n", "P(n)", 2, True),
            (3, "Inductive step", "algebra to P(n+1)", "P(n)\\Rightarrow P(n+1)", 5, True),
            (4, "Conclusion", "true for all n", "\\forall n", 2, True),
        ],
        "Proof complete",
        "\\text{QED}",
    )
    add_single(
        db,
        ex.id,
        8,
        "Section B — Q8 (choose 2 of Q7–9). ∫₀¹ 2x e^{x²} dx.",
        12,
        [
            (1, "Substitution", "u=x^2, du=2x dx", "u=x^2", 4, True),
            (2, "Integrate", "e^u", "e^u", 3, True),
            (3, "Evaluate", "e-1", "e-1", 5, True),
        ],
        "e - 1",
        "e - 1",
    )
    add_single(
        db,
        ex.id,
        9,
        "Section B — Q9 (choose 2 of Q7–9). Solve 2 sin²x = 1 on [0, π).",
        12,
        [
            (1, "Simplify", "sin x = ±1/√2", "\\sin x = \\pm \\frac{1}{\\sqrt{2}}", 3, True),
            (2, "Solutions in interval", "π/4, 3π/4", "\\frac{\\pi}{4},\\;\\frac{3\\pi}{4}", 6, True),
            (3, "Reject extraneous if any", "both valid", "\\text{both in }[0,\\pi)", 3, True),
        ],
        "π/4 and 3π/4",
        "\\frac{\\pi}{4},\\;\\frac{3\\pi}{4}",
    )

    ex.total_points = sum_points(db, ex.id)
    db.commit()


def build_biology_exam(db, course_id: str, due, pub_at, auto_publish: bool) -> None:
    desc = (
        "Section A: answer ALL. Section B: answer TWO of three. "
        "Use precise terminology; bullet lists acceptable where noted."
    )
    ex = models.Exam(
        course_id=course_id,
        title=f"{DEMO_PREFIX} Biology — Final Assessment",
        description=desc,
        total_points=0,
        due_date=due,
        is_published=auto_publish,
        published_at=pub_at,
    )
    db.add(ex)
    db.flush()

    add_multipart(
        db,
        ex.id,
        1,
        "Section A — Q1. Cell structure",
        doc(
            _h(3, "Section A"),
            _p(_t("Organelle identification and function.")),
        ),
        [
            {
                "text": "(a) Name the organelle that houses most DNA in a eukaryotic cell.",
                "points": 4,
                "final_answer": "nucleus",
                "final_answer_latex": "\\text{nucleus}",
                "gold": [
                    (1, "Answer", "nucleus", "\\text{nucleus}", 4, True),
                ],
            },
            {
                "text": "(b) Where is ATP mainly produced in aerobic respiration?",
                "points": 6,
                "final_answer": "mitochondria / inner mitochondrial membrane",
                "final_answer_latex": "\\text{mitochondria}",
                "gold": [
                    (1, "Organelle", "mitochondria", "\\text{mitochondria}", 4, True),
                    (2, "Site detail", "cristae / inner membrane", "\\text{inner membrane}", 2, True),
                ],
            },
        ],
    )

    add_multipart(
        db,
        ex.id,
        2,
        "Section A — Q2. Genetics",
        doc(
            _p(
                _t("Autosomal trait; A dominant, a recessive. Cross "),
                _imath("Aa \\times aa"),
                _t("."),
            ),
        ),
        [
            {
                "text": "(a) Punnett ratios for offspring genotypes.",
                "points": 6,
                "final_answer": "1 Aa : 1 aa",
                "final_answer_latex": "1:1\\ (Aa:aa)",
                "gold": [
                    (1, "Gametes", "A,a from Aa; a from aa", "\\text{gametes}", 2, True),
                    (2, "Ratio", "50% Aa, 50% aa", "1:1", 4, True),
                ],
            },
            {
                "text": "(b) Phenotype ratio if A shows dominant phenotype.",
                "points": 4,
                "final_answer": "1 dominant : 1 recessive",
                "final_answer_latex": "1:1",
                "gold": [
                    (1, "Phenotype", "1:1 dominant:recessive", "1:1", 4, True),
                ],
            },
        ],
    )

    add_multipart(
        db,
        ex.id,
        3,
        "Section A — Q3. Photosynthesis & data",
        doc(
            _p(_t("Light-dependent reactions and a simple productivity table.")),
            _table(
                ["Lake", "Chlorophyll (µg/L)"],
                [["P", "12"], ["Q", "7"], ["R", "18"]],
            ),
            _graph(
                "bar",
                [{"name": "P", "value": 12}, {"name": "Q", "value": 7}, {"name": "R", "value": 18}],
                "Chlorophyll by site",
                "Site",
                "µg/L",
            ),
        ),
        [
            {
                "text": "(a) Overall equation for glucose-forming photosynthesis (words or symbols).",
                "points": 6,
                "final_answer": "CO2 + H2O → glucose + O2 (light/chlorophyll)",
                "final_answer_latex": "6CO_2 + 6H_2O \\rightarrow C_6H_{12}O_6 + 6O_2",
                "gold": [
                    (1, "Reactants", "CO2 and H2O", "CO_2,\\ H_2O", 2, True),
                    (2, "Products", "glucose and O2", "C_6H_{12}O_6,\\ O_2", 2, True),
                    (3, "Energy input", "light", "\\text{light}", 2, True),
                ],
            },
            {
                "text": "(b) Which lake likely has highest primary productivity? Justify briefly.",
                "points": 4,
                "final_answer": "Lake R — highest chlorophyll",
                "final_answer_latex": "R",
                "gold": [
                    (1, "Choice", "Lake R", "R", 2, True),
                    (2, "Reason", "highest chlorophyll proxy", "\\text{highest chl}", 2, True),
                ],
            },
        ],
    )

    add_single(
        db,
        ex.id,
        4,
        "Section A — Q4. Enzymes: define Vmax and Km in one sentence each.",
        8,
        [
            (1, "Vmax", "maximum velocity at saturating substrate", "V_{\\max}", 4, True),
            (2, "Km", "substrate at half Vmax", "K_m", 4, True),
        ],
        "Vmax = max rate; Km = [S] at ½ Vmax",
        "",
    )

    add_multipart(
        db,
        ex.id,
        5,
        "Section A — Q5. Ecology",
        None,
        [
            {
                "text": "(a) State the 10% rule of energy transfer between trophic levels.",
                "points": 5,
                "final_answer": "≈10% passes to next level",
                "final_answer_latex": "\\approx 10\\%",
                "gold": [
                    (1, "Rule", "~10% energy transfer", "10\\%", 5, True),
                ],
            },
            {
                "text": "(b) Why are food chains rarely longer than 5 levels?",
                "points": 5,
                "final_answer": "energy losses accumulate",
                "final_answer_latex": "\\text{energy loss}",
                "gold": [
                    (1, "Reason", "insufficient energy", "\\text{energy}", 5, True),
                ],
            },
        ],
    )

    add_multipart(
        db,
        ex.id,
        6,
        "Section A — Q6. Membrane transport",
        None,
        [
            {
                "text": "(a) Diffusion vs osmosis (one distinction).",
                "points": 4,
                "final_answer": "osmosis is diffusion of water",
                "final_answer_latex": "\\text{osmosis } H_2O",
                "gold": [
                    (1, "Distinction", "osmosis water specifically", "\\text{water}", 4, True),
                ],
            },
            {
                "text": "(b) Example of active transport.",
                "points": 6,
                "final_answer": "Na+/K+ pump (or similar)",
                "final_answer_latex": "\\text{Na/K pump}",
                "gold": [
                    (1, "Example", "sodium-potassium pump", "\\text{Na/K pump}", 4, True),
                    (2, "Uses energy", "ATP", "ATP", 2, True),
                ],
            },
        ],
    )

    add_single(
        db,
        ex.id,
        7,
        "Section B — Q7. Outline semiconservative DNA replication.",
        12,
        [
            (1, "Unwinding", "helicase / fork", "\\text{helicase}", 3, True),
            (2, "Priming & polymerase", "DNA pol extends 5'→3'", "DNA\\ pol", 4, True),
            (3, "Result", "each daughter hybrid old+new", "\\text{semiconservative}", 5, True),
        ],
        "Each strand templates a new complementary strand",
        "",
    )
    add_single(
        db,
        ex.id,
        8,
        "Section B — Q8. Mechanisms of natural selection (brief).",
        12,
        [
            (1, "Variation", "heritable variation exists", "\\text{variation}", 3, True),
            (2, "Selection", "differential survival/reproduction", "\\text{selection}", 4, True),
            (3, "Inheritance", "traits passed on", "\\text{inheritance}", 3, True),
            (4, "Outcome", "allele frequency change", "\\text{evolution}", 2, True),
        ],
        "Variation, selection, inheritance → adaptation",
        "",
    )
    add_single(
        db,
        ex.id,
        9,
        "Section B — Q9. Innate vs adaptive immunity — one difference.",
        12,
        [
            (1, "Innate", "fast, non-specific", "\\text{innate}", 4, True),
            (2, "Adaptive", "slow, specific, memory", "\\text{adaptive}", 5, True),
            (3, "Contrast", "clear comparison", "\\text{vs}", 3, True),
        ],
        "Innate: immediate/non-specific; Adaptive: specific/memory",
        "",
    )

    ex.total_points = sum_points(db, ex.id)
    db.commit()


def build_physics_exam(db, course_id: str, due, pub_at, auto_publish: bool) -> None:
    desc = "SI units unless noted. Section B: answer TWO of Q7–9. Show substitutions in calculations."
    ex = models.Exam(
        course_id=course_id,
        title=f"{DEMO_PREFIX} Physics — Mechanics & Waves",
        description=desc,
        total_points=0,
        due_date=due,
        is_published=auto_publish,
        published_at=pub_at,
    )
    db.add(ex)
    db.flush()

    add_multipart(
        db,
        ex.id,
        1,
        "Section A — Q1. Kinematics from graph",
        doc(
            _p(_t("Uniform acceleration in one dimension. Graph of velocity vs time:")),
            _graph(
                "line",
                [{"name": "0", "value": 0}, {"name": "1", "value": 2}, {"name": "2", "value": 4}, {"name": "3", "value": 6}],
                "Velocity vs time",
                "t (s)",
                "v (m/s)",
            ),
        ),
        [
            {
                "text": "(a) Estimate acceleration.",
                "points": 5,
                "final_answer": "2 m/s²",
                "final_answer_latex": "2\\ \\mathrm{m/s^2}",
                "gold": [
                    (1, "Slope", "Δv/Δt", "a=\\Delta v/\\Delta t", 3, True),
                    (2, "Value", "2", "2", 2, True),
                ],
            },
            {
                "text": "(b) Displacement 0–3 s if v0=0.",
                "points": 5,
                "final_answer": "9 m",
                "final_answer_latex": "9\\ \\mathrm{m}",
                "gold": [
                    (1, "Area under curve", "triangle or integral", "s=\\tfrac{1}{2}at^2", 3, True),
                    (2, "Result", "9 m", "9", 2, True),
                ],
            },
        ],
    )

    add_multipart(
        db,
        ex.id,
        2,
        "Section A — Q2. Inclined plane",
        doc(_p(_t("Block on smooth incline (diagram).")), _svg_image(SVG_RAMP)),
        [
            {
                "text": "(a) Component of weight parallel to plane.",
                "points": 6,
                "final_answer": "39.2 N",
                "final_answer_latex": "mg\\sin 30^\\circ \\approx 39.2\\ \\mathrm{N}",
                "gold": [
                    (1, "Formula", "mg sin θ", "mg\\sin\\theta", 3, True),
                    (2, "Substitute", "8*9.8*0.5", "39.2", 3, True),
                ],
            },
            {
                "text": "(b) Normal force (smooth plane).",
                "points": 4,
                "final_answer": "67.9 N",
                "final_answer_latex": "mg\\cos 30^\\circ",
                "gold": [
                    (1, "Formula", "mg cos θ", "mg\\cos\\theta", 2, True),
                    (2, "Value", "~67.9 N", "67.9", 2, True),
                ],
            },
        ],
    )

    add_multipart(
        db,
        ex.id,
        3,
        "Section A — Q3. Circuits",
        doc(
            _p(_t("Two identical resistors R in series across battery V.")),
        ),
        [
            {
                "text": "(a) Equivalent resistance.",
                "points": 4,
                "final_answer": "2R",
                "final_answer_latex": "2R",
                "gold": [(1, "Series sum", "R+R", "2R", 4, True)],
            },
            {
                "text": "(b) Power in one resistor.",
                "points": 6,
                "final_answer": "V²/(4R)",
                "final_answer_latex": "P = \\frac{V^2}{4R}",
                "gold": [
                    (1, "Current", "I=V/(2R)", "I=V/2R", 2, True),
                    (2, "Power", "I^2 R", "P=I^2R=V^2/4R", 4, True),
                ],
            },
        ],
    )

    add_single(
        db,
        ex.id,
        4,
        "Section A — Q4. Wave: f = 50 Hz, λ = 6 m. Find wave speed.",
        6,
        [(1, "Relation", "v=fλ", "v=f\\lambda", 3, True), (2, "Compute", "300 m/s", "300", 3, True)],
        "300 m/s",
        "300\\ \\mathrm{m/s}",
    )

    add_multipart(
        db,
        ex.id,
        5,
        "Section A — Q5. Energy",
        None,
        [
            {
                "text": "(a) Gravitational PE change lifting 2 kg by 4 m (g=9.8).",
                "points": 5,
                "final_answer": "78.4 J",
                "final_answer_latex": "78.4\\ \\mathrm{J}",
                "gold": [(1, "mgh", "2*9.8*4", "78.4", 5, True)],
            },
            {
                "text": "(b) State work–energy theorem in one line.",
                "points": 5,
                "final_answer": "W_net = ΔK",
                "final_answer_latex": "W_{\\mathrm{net}} = \\Delta K",
                "gold": [(1, "Theorem", "net work equals change in kinetic energy", "W=\\Delta K", 5, True)],
            },
        ],
    )

    add_single(
        db,
        ex.id,
        6,
        "Section A — Q6. Ideal gas: double absolute temperature at fixed volume. What happens to pressure?",
        8,
        [
            (1, "Law", "P/T constant (V const)", "P\\propto T", 4, True),
            (2, "Result", "pressure doubles", "2P", 4, True),
        ],
        "Pressure doubles",
        "P_2 = 2P_1",
    )

    add_single(
        db,
        ex.id,
        7,
        "Section B — Q7. Angular momentum conservation — give one everyday example.",
        12,
        [
            (1, "Principle", "L constant if no external torque", "L=\\text{const}", 5, True),
            (2, "Example", "ice skater spin", "\\text{skater}", 4, True),
            (3, "Mechanism", "Iω adjustment", "I\\omega", 3, True),
        ],
        "e.g. skater pulling arms in spins faster",
        "",
    )
    add_single(
        db,
        ex.id,
        8,
        "Section B — Q8. Snell’s law: light n1=1.0 to n2=1.5, incident 40°. Find refracted angle (sin⁻¹ steps OK).",
        12,
        [
            (1, "Snell", "n1 sin θ1 = n2 sin θ2", "n_1\\sin\\theta_1=n_2\\sin\\theta_2", 4, True),
            (2, "Solve", "θ2 ≈ 25.4°", "\\approx 25.4^\\circ", 5, True),
            (3, "Toward normal", "θ2 < θ1", "\\theta_2<\\theta_1", 3, True),
        ],
        "≈25.4°",
        "\\approx 25.4^\\circ",
    )
    add_single(
        db,
        ex.id,
        9,
        "Section B — Q9. First law of thermodynamics: write ΔU = … and define each term briefly.",
        12,
        [
            (1, "Equation", "ΔU = Q - W", "\\Delta U = Q - W", 4, True),
            (2, "ΔU", "internal energy change", "\\Delta U", 3, True),
            (3, "Q,W", "heat in, work by system", "Q,W", 5, True),
        ],
        "ΔU = Q − W (sign conventions stated)",
        "\\Delta U = Q - W",
    )

    ex.total_points = sum_points(db, ex.id)
    db.commit()


def build_chemistry_exam(db, course_id: str, due, pub_at, auto_publish: bool) -> None:
    desc = "Section A compulsory. Section B: two of three. Balance equations with smallest integers."
    ex = models.Exam(
        course_id=course_id,
        title=f"{DEMO_PREFIX} Chemistry — Stoichiometry & Reactions",
        description=desc,
        total_points=0,
        due_date=due,
        is_published=auto_publish,
        published_at=pub_at,
    )
    db.add(ex)
    db.flush()

    add_single(
        db,
        ex.id,
        1,
        "Section A — Q1. Balance: Fe + O2 → Fe2O3",
        8,
        [
            (1, "Iron", "4 Fe", "4Fe", 2, True),
            (2, "Oxygen", "3 O2", "3O_2", 2, True),
            (3, "Product", "2 Fe2O3", "2Fe_2O_3", 4, True),
        ],
        "4 Fe + 3 O2 → 2 Fe2O3",
        "4\\mathrm{Fe} + 3\\mathrm{O}_2 \\rightarrow 2\\mathrm{Fe}_2\\mathrm{O}_3",
    )

    add_multipart(
        db,
        ex.id,
        2,
        "Section A — Q2. Stoichiometry",
        doc(
            _p(_t("N2 + 3 H2 → 2 NH3. Molar masses: N2 28, H2 2, NH3 17 g/mol.")),
        ),
        [
            {
                "text": "(a) Moles NH3 from 2 mol N2.",
                "points": 5,
                "final_answer": "4 mol",
                "final_answer_latex": "4\\ \\mathrm{mol}",
                "gold": [(1, "Ratio", "1:2 N2:NH3", "4\\ \\text{mol}", 5, True)],
            },
            {
                "text": "(b) Mass of NH3 in (a).",
                "points": 5,
                "final_answer": "68 g",
                "final_answer_latex": "68\\ \\mathrm{g}",
                "gold": [(1, "Multiply", "4*17", "68", 5, True)],
            },
        ],
    )

    add_multipart(
        db,
        ex.id,
        3,
        "Section A — Q3. Periodic trends",
        None,
        [
            {
                "text": "(a) Atomic radius trend down Group 1.",
                "points": 4,
                "final_answer": "increases",
                "final_answer_latex": "\\text{increases}",
                "gold": [(1, "Trend", "increases down group", "\\downarrow\\text{ size}", 4, True)],
            },
            {
                "text": "(b) First ionisation energy across Period 3 (left to right).",
                "points": 4,
                "final_answer": "generally increases",
                "final_answer_latex": "\\text{increases}",
                "gold": [(1, "Trend", "increases across period", "\\rightarrow", 4, True)],
            },
        ],
    )

    add_multipart(
        db,
        ex.id,
        4,
        "Section A — Q4. Acid–base titration",
        doc(
            _table(["Reading", "Volume (mL)"], [["Initial", "2.40"], ["Final", "16.85"]]),
        ),
        [
            {
                "text": "(a) Titre volume.",
                "points": 4,
                "final_answer": "14.45 mL",
                "final_answer_latex": "14.45\\ \\mathrm{mL}",
                "gold": [(1, "Subtract", "16.85-2.40", "14.45", 4, True)],
            },
            {
                "text": "(b) Why use indicator?",
                "points": 4,
                "final_answer": "signal equivalence point",
                "final_answer_latex": "\\text{end point}",
                "gold": [(1, "Reason", "visual end point", "\\text{indicator}", 4, True)],
            },
        ],
    )

    add_single(
        db,
        ex.id,
        5,
        "Section A — Q5. Name the functional group in CH3CH2OH.",
        4,
        [(1, "Group", "alcohol / hydroxyl", "-OH", 4, True)],
        "alcohol (hydroxyl)",
        "\\text{-OH}",
    )

    add_multipart(
        db,
        ex.id,
        6,
        "Section A — Q6. Redox",
        doc(_p(_t("Half-reaction method for acidic solution."))),
        [
            {
                "text": "(a) Is MnO4⁻ → Mn²+ oxidation or reduction?",
                "points": 4,
                "final_answer": "reduction",
                "final_answer_latex": "\\text{reduction}",
                "gold": [(1, "Oxidation state", "Mn decreases", "\\text{reduction}", 4, True)],
            },
            {
                "text": "(b) Balance electrons conceptually (how many e⁻ for one MnO4⁻ → Mn²+ in acid)?",
                "points": 8,
                "final_answer": "5 electrons",
                "final_answer_latex": "5e^-",
                "gold": [
                    (1, "Δ oxidation number", "7 to 2 = 5", "+7\\rightarrow+2", 4, True),
                    (2, "Electrons", "5 e⁻ gained", "5e^-", 4, True),
                ],
            },
        ],
    )

    add_single(
        db,
        ex.id,
        7,
        "Section B — Q7. Le Châtelier: N2O4(g) ⇌ 2 NO2(g) endothermic forward. Effect of increasing T at constant V.",
        12,
        [
            (1, "Shift", "toward NO2 / products", "\\rightarrow \\text{products}", 5, True),
            (2, "Reason", "consume added heat", "\\text{endothermic}", 4, True),
            (3, "Colour note", "darker brown if NO2", "NO_2", 3, True),
        ],
        "Equilibrium shifts right (more NO2)",
        "",
    )
    add_single(
        db,
        ex.id,
        8,
        "Section B — Q8. Rate law: if order in A is 2 and doubling [A] quadruples rate — verify consistency.",
        12,
        [
            (1, "Rate law", "R = k[A]^2", "R=k[A]^2", 4, True),
            (2, "Factor", "[2]^2 = 4", "4\\times", 5, True),
            (3, "Conclusion", "consistent", "\\checkmark", 3, True),
        ],
        "Consistent: second order gives ×4 rate",
        "",
    )
    add_single(
        db,
        ex.id,
        9,
        "Section B — Q9. Standard hydrogen electrode: role of Pt and H2(g).",
        12,
        [
            (1, "Reference", "0 V by definition", "E^\\circ=0", 4, True),
            (2, "Pt", "inert conductor / catalyst", "Pt", 4, True),
            (3, "H2", "1 bar, a(H+)=1", "H_2", 4, True),
        ],
        "SHE: H2 | H+ || ; E° = 0",
        "",
    )

    ex.total_points = sum_points(db, ex.id)
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo examination papers")
    parser.add_argument("--no-publish", action="store_true")
    parser.add_argument("--no-enroll", action="store_true")
    args = parser.parse_args()
    auto_publish = not args.no_publish
    do_enroll = not args.no_enroll

    init_db()
    db = SessionLocal()
    try:
        prof = (
            db.query(models.User)
            .filter(models.User.role == models.UserRole.PROFESSOR)
            .first()
        )
        if not prof:
            print("❌ No professor user found.")
            sys.exit(1)

        course = (
            db.query(models.Course)
            .filter(
                models.Course.code == COURSE_CODE,
                models.Course.professor_id == prof.id,
            )
            .first()
        )
        if not course:
            course = models.Course(
                name=COURSE_NAME,
                code=COURSE_CODE,
                description="Full-length demo papers for grading, PDF, and student UI demos.",
                level=models.CourseLevel.ALL_LEVELS,
                professor_id=prof.id,
            )
            db.add(course)
            db.commit()
            db.refresh(course)
            print(f"✅ Created course: {course.name} ({course.code})")
        else:
            print(f"✅ Using course: {course.name} ({course.id})")

        removed = wipe_demo_exams(db, course.id)
        if removed:
            print(f"🗑️  Removed {removed} prior {DEMO_PREFIX} exam(s)")

        due = datetime.now(timezone.utc) + timedelta(days=21)
        pub_at = datetime.now(timezone.utc) if auto_publish else None

        build_math_exam(db, course.id, due, pub_at, auto_publish)
        build_biology_exam(db, course.id, due, pub_at, auto_publish)
        build_physics_exam(db, course.id, due, pub_at, auto_publish)
        build_chemistry_exam(db, course.id, due, pub_at, auto_publish)

        print(f"\n✅ Created 4 {DEMO_PREFIX} exams:")
        for ex in (
            db.query(models.Exam)
            .filter(models.Exam.course_id == course.id, models.Exam.title.like(f"{DEMO_PREFIX}%"))
            .order_by(models.Exam.title)
            .all()
        ):
            nq = (
                db.query(models.Question)
                .filter(models.Question.exam_id == ex.id, models.Question.parent_question_id.is_(None))
                .count()
            )
            nl = db.query(models.Question).filter(models.Question.exam_id == ex.id).count()
            pub = "published" if ex.is_published else "draft"
            print(f"   • {ex.title}")
            print(f"     {ex.total_points} pts | {nq} top-level questions | {nl} total rows (incl. sub-parts) | {pub}")

        if do_enroll:
            stu = db.query(models.User).filter(models.User.email == DEMO_STUDENT_EMAIL).first()
            if stu:
                ensure_enrollment(db, course.id, stu.id)
                print(f"\n✅ Demo student enrolled: {DEMO_STUDENT_EMAIL}")
            else:
                print(f"\n⚠️  No {DEMO_STUDENT_EMAIL} — skip enroll")

        print(f"\n📋 Course code: {COURSE_CODE}  |  Professor: {prof.email}")
        print("   Run:  cd backend && source venv/bin/activate && python seed_demo_exams.py")
    except Exception as e:
        db.rollback()
        print(f"❌ {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
