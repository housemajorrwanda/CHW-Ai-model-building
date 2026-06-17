"""Tests for exam upload parsing (handwritten OCR and structured exams)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from exam_parser import ExamParser
from ocr.text_rich_content import normalize_exam_ocr_text


def _ocr_pdf(path: Path) -> str:
    from ocr.ocr_pipeline import OCRProcessor

    result = OCRProcessor().extract_steps_from_file(path.read_bytes(), path.name)
    return normalize_exam_ocr_text(result.combined_text or "")


def test_handwritten_answer_only_pdf():
    pdf = Path("/Users/a/Downloads/questions and golden answers.pdf")
    if not pdf.exists():
        return
    parsed = ExamParser().parse_exam(_ocr_pdf(pdf))
    assert parsed["title"] == "Imported Exam"
    assert len(parsed["questions"]) == 3
    assert len(parsed["questions"][0]["gold_solution_steps"]) >= 2


def test_structured_exam_with_gold_markers():
    pdf = Path("/Users/a/Downloads/students answer.pdf")
    if not pdf.exists():
        return
    parsed = ExamParser().parse_exam(_ocr_pdf(pdf))

    assert "Mathematics" in parsed["title"]
    assert "show all works" in parsed["description"].lower()

    q1 = parsed["questions"][0]
    assert "solve for" in (q1.get("text") or "").lower()
    assert "3 x + 7 = 22" in (q1.get("text") or "")
    assert len(q1["gold_solution_steps"]) == 4
    assert all("solve for" not in (s.get("expression") or "").lower() for s in q1["gold_solution_steps"])

    q2_subs = parsed["questions"][1].get("sub_questions") or []
    assert len(q2_subs) == 2
    assert "quadratic equation" in (q2_subs[0].get("text") or "").lower()
    assert q2_subs[0]["gold_solution_steps"][0]["expression"]
    assert "squares" in q2_subs[1]["gold_solution_steps"][0]["expression"].lower()

    q3_subs = parsed["questions"][2].get("sub_questions") or []
    assert len(q3_subs) == 2
    assert "integral" in (q3_subs[0].get("text") or "").lower()
    assert len(q3_subs[0]["gold_solution_steps"]) >= 2
    assert "derivative" in (q3_subs[1].get("text") or "").lower()


if __name__ == "__main__":
    test_handwritten_answer_only_pdf()
    test_structured_exam_with_gold_markers()
    print("OK")
