#!/usr/bin/env python3
"""
Seed regression / QA exams for manual and automated testing.

Creates course "QA Regression (auto-seeded)" and exams whose titles start with "[QA]".
Re-running removes previous [QA] exams in that course and recreates them.

Usage (from backend/, venv active):
    python seed_qa_exams.py
    python seed_qa_exams.py --no-publish
    python seed_qa_exams.py --no-enroll

Prerequisites: at least one professor user (e.g. demo professor@university.edu after first API startup).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import models
from database import SessionLocal, init_db


COURSE_CODE = "QA-REG"
COURSE_NAME = "QA Regression (auto-seeded)"
QA_TITLE_PREFIX = "[QA]"
DEMO_STUDENT_EMAIL = "student@university.edu"

RICH_SAMPLE = {
    "type": "doc",
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Problem (rich text + math)"}],
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Let "},
                {"type": "inlineMath", "attrs": {"latex": "f(x)=x^2-4x+3"}},
                {"type": "text", "text": ". Find "},
                {"type": "text", "text": "f'(2)", "marks": [{"type": "bold"}]},
                {"type": "text", "text": "."},
            ],
        },
        {
            "type": "blockMath",
            "attrs": {"latex": "\\frac{d}{dx}(x^2-4x+3) = 2x-4"},
        },
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Show the derivative."}],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Substitute x=2."}],
                        }
                    ],
                },
            ],
        },
    ],
}


def _gold(db, qid, steps: list[tuple]) -> None:
    for sn, desc, expr, latex, pts, req in steps:
        db.add(
            models.GoldSolutionStep(
                question_id=qid,
                step_number=sn,
                description=desc,
                expression=expr,
                latex=latex,
                points=pts,
                required=req,
            )
        )


def sum_points(db, exam_id: str) -> int:
    rows = db.query(models.Question.points).filter(models.Question.exam_id == exam_id).all()
    return sum(r[0] for r in rows)


def wipe_qa_exams(db, course_id: str) -> int:
    n = 0
    exams = (
        db.query(models.Exam)
        .filter(
            models.Exam.course_id == course_id,
            models.Exam.title.like(f"{QA_TITLE_PREFIX}%"),
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
    enr = models.CourseEnrollment(
        course_id=course_id,
        student_id=student_id,
        status=models.EnrollmentStatus.APPROVED,
        enrolled_at=datetime.now(timezone.utc),
    )
    db.add(enr)
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed QA regression exams")
    parser.add_argument("--no-publish", action="store_true", help="Leave exams unpublished")
    parser.add_argument("--no-enroll", action="store_true", help="Skip enrolling demo student")
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
            print("❌ No professor user found. Start the API once on an empty DB to seed demo users,")
            print("   or register a professor, then re-run this script.")
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
                description="Automated QA exams — safe to delete. Used for grading, PDF, and UI tests.",
                level=models.CourseLevel.ALL_LEVELS,
                professor_id=prof.id,
            )
            db.add(course)
            db.commit()
            db.refresh(course)
            print(f"✅ Created course: {course.name} ({course.code})")
        else:
            print(f"✅ Using course: {course.name} ({course.id})")

        removed = wipe_qa_exams(db, course.id)
        if removed:
            print(f"🗑️  Removed {removed} prior [QA] exam(s)")

        due = datetime.now(timezone.utc) + timedelta(days=14)
        pub_at = datetime.now(timezone.utc) if auto_publish else None

        e1 = models.Exam(
            course_id=course.id,
            title=f"{QA_TITLE_PREFIX} 01 Smoke — Linear equation",
            description="Single question, 3 gold steps. Best for first typed submission + auto-grade.",
            total_points=0,
            due_date=due,
            is_published=auto_publish,
            published_at=pub_at,
        )
        db.add(e1)
        db.flush()
        q1 = models.Question(
            exam_id=e1.id,
            number=1,
            text="Solve for x: 2x - 8 = 10",
            points=10,
            final_answer="x = 9",
            final_answer_latex="x = 9",
            question_type="standard",
        )
        db.add(q1)
        db.flush()
        _gold(
            db,
            q1.id,
            [
                (1, "Add 8 to both sides", "2x = 18", "2x = 18", 3, True),
                (2, "Divide by 2", "x = 9", "x = 9", 4, True),
                (3, "State solution", "x = 9", "x = 9", 3, True),
            ],
        )
        e1.total_points = sum_points(db, e1.id)

        e2 = models.Exam(
            course_id=course.id,
            title=f"{QA_TITLE_PREFIX} 02 Rich text + LaTeX",
            description="TipTap JSON with inline/block math. Tests exam PDF, student view, marked PDF.",
            total_points=0,
            due_date=due,
            is_published=auto_publish,
            published_at=pub_at,
        )
        db.add(e2)
        db.flush()
        q2 = models.Question(
            exam_id=e2.id,
            number=1,
            text="(See rich content) Find f'(2) for f(x)=x^2-4x+3.",
            points=12,
            final_answer="0",
            final_answer_latex="f'(2)=0",
            question_type="standard",
            rich_content=json.dumps(RICH_SAMPLE),
        )
        db.add(q2)
        db.flush()
        _gold(
            db,
            q2.id,
            [
                (1, "Derivative", "f'(x)=2x-4", "f'(x) = 2x - 4", 5, True),
                (2, "Evaluate at 2", "f'(2)=0", "f'(2) = 0", 4, True),
                (3, "Answer", "0", "0", 3, True),
            ],
        )
        e2.total_points = sum_points(db, e2.id)

        e3 = models.Exam(
            course_id=course.id,
            title=f"{QA_TITLE_PREFIX} 03 Multi-part (parent + subs)",
            description="Parent prompt; (a) and (b) are separate questions for grading IDs.",
            total_points=0,
            due_date=due,
            is_published=auto_publish,
            published_at=pub_at,
        )
        db.add(e3)
        db.flush()
        parent = models.Question(
            exam_id=e3.id,
            number=1,
            text="Answer both parts. Show work.",
            points=0,
            final_answer="",
            final_answer_latex="",
            question_type="multi-part",
        )
        db.add(parent)
        db.flush()
        qa = models.Question(
            exam_id=e3.id,
            number=1,
            text="(a) Compute 12 + 15.",
            points=8,
            final_answer="27",
            final_answer_latex="27",
            question_type="standard",
            parent_question_id=parent.id,
        )
        qb = models.Question(
            exam_id=e3.id,
            number=2,
            text="(b) Compute 7 × 6.",
            points=12,
            final_answer="42",
            final_answer_latex="42",
            question_type="standard",
            parent_question_id=parent.id,
        )
        db.add_all([qa, qb])
        db.flush()
        _gold(db, qa.id, [(1, "Sum", "27", "12+15=27", 8, True)])
        _gold(
            db,
            qb.id,
            [
                (1, "Multiply", "42", "7 \\times 6 = 42", 8, True),
                (2, "Result", "42", "42", 4, True),
            ],
        )
        e3.total_points = sum_points(db, e3.id)

        e4 = models.Exam(
            course_id=course.id,
            title=f"{QA_TITLE_PREFIX} 04 Optional gold step",
            description="Step 3 is not required; partial-credit / matcher behaviour.",
            total_points=0,
            due_date=due,
            is_published=auto_publish,
            published_at=pub_at,
        )
        db.add(e4)
        db.flush()
        q4 = models.Question(
            exam_id=e4.id,
            number=1,
            text="Expand (x+2)^2.",
            points=10,
            final_answer="x^2 + 4x + 4",
            final_answer_latex="x^2 + 4x + 4",
            question_type="standard",
        )
        db.add(q4)
        db.flush()
        _gold(
            db,
            q4.id,
            [
                (1, "Formula", "(a+b)^2=a^2+2ab+b^2", "(a+b)^2=a^2+2ab+b^2", 2, True),
                (2, "Substitute", "x^2+4x+4", "x^2 + 4x + 4", 5, True),
                (3, "Alternative foil (optional)", "x^2+2x+2x+4", "x^2+2x+2x+4", 2, False),
                (4, "Simplify", "x^2+4x+4", "x^2 + 4x + 4", 1, True),
            ],
        )
        e4.total_points = sum_points(db, e4.id)

        e5 = models.Exam(
            course_id=course.id,
            title=f"{QA_TITLE_PREFIX} 05 Wordy steps (OCR-style)",
            description="Longer expression strings; closer to OCR line dumps.",
            total_points=0,
            due_date=due,
            is_published=auto_publish,
            published_at=pub_at,
        )
        db.add(e5)
        db.flush()
        q5 = models.Question(
            exam_id=e5.id,
            number=1,
            text="Solve: The sum of two consecutive integers is 47. Find the integers.",
            points=15,
            final_answer="23 and 24",
            final_answer_latex="23,\\,24",
            question_type="standard",
        )
        db.add(q5)
        db.flush()
        _gold(
            db,
            q5.id,
            [
                (1, "Define variables", "Let n and n+1 be the integers", "n,\\; n+1", 3, True),
                (2, "Equation", "n + (n+1) = 47", "n + (n+1) = 47", 4, True),
                (3, "Solve", "2n + 1 = 47, 2n = 46, n = 23", "2n+1=47 \\Rightarrow n=23", 5, True),
                (4, "Answer", "23 and 24", "23,\\,24", 3, True),
            ],
        )
        e5.total_points = sum_points(db, e5.id)

        e6 = models.Exam(
            course_id=course.id,
            title=f"{QA_TITLE_PREFIX} 06 Limit + derivative",
            description="More LaTeX in gold steps (PDF mathtext, symbolic paths).",
            total_points=0,
            due_date=due,
            is_published=auto_publish,
            published_at=pub_at,
        )
        db.add(e6)
        db.flush()
        q6 = models.Question(
            exam_id=e6.id,
            number=1,
            text="Evaluate lim(x→0) (sin x)/x and state the derivative of sin(x) at 0.",
            points=15,
            final_answer="1",
            final_answer_latex="1",
            question_type="standard",
        )
        db.add(q6)
        db.flush()
        _gold(
            db,
            q6.id,
            [
                (
                    1,
                    "Limit",
                    "lim sin(x)/x = 1 as x→0",
                    "\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1",
                    7,
                    True,
                ),
                (
                    2,
                    "Derivative",
                    "d/dx sin x = cos x",
                    "\\frac{d}{dx}\\sin x = \\cos x",
                    4,
                    True,
                ),
                (3, "At 0", "cos(0)=1", "\\cos 0 = 1", 4, True),
            ],
        )
        e6.total_points = sum_points(db, e6.id)

        db.commit()

        print("\n✅ QA exams created (all titles start with [QA]):")
        for ex in (
            db.query(models.Exam)
            .filter(models.Exam.course_id == course.id, models.Exam.title.like(f"{QA_TITLE_PREFIX}%"))
            .order_by(models.Exam.title)
            .all()
        ):
            pub = "published" if ex.is_published else "draft"
            print(f"   • {ex.title} — {ex.total_points} pts — {pub}")

        if do_enroll:
            stu = db.query(models.User).filter(models.User.email == DEMO_STUDENT_EMAIL).first()
            if stu:
                ensure_enrollment(db, course.id, stu.id)
                print(f"\n✅ Demo student ({DEMO_STUDENT_EMAIL}) enrollment: APPROVED on this course")
            else:
                print(f"\n⚠️  No user {DEMO_STUDENT_EMAIL} — skip enroll (start API on empty DB for demo users)")

        print("\n📋 Suggested test matrix:")
        print("   • Typed submit + auto-grade     → QA 01, 03, 04")
        print("   • Rich / math in UI + PDFs      → QA 02")
        print("   • Sub-question grading          → QA 03")
        print("   • Partial / optional steps      → QA 04")
        print("   • OCR / scan upload             → QA 05")
        print("   • Heavy LaTeX                   → QA 06")
        print(f"\n   Course code: {COURSE_CODE}  |  Professor: {prof.email}")
    except Exception as e:
        db.rollback()
        print(f"❌ {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
