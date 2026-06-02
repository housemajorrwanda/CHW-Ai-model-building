"""
Align separately-uploaded answer keys with existing exam questions.

Professors can upload questions first (without gold solutions), then upload a
dedicated marking scheme / answer key document. Parsed solutions are matched to
exam questions by question number and sub-part labels.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from exam_parser import ExamParser


def _normalize_label(label: Optional[str]) -> str:
    if not label:
        return ""
    s = label.strip().lower()
    s = re.sub(r"^\(|\)$", "", s)
    s = re.sub(r"[\.\):]+$", "", s)
    return s


def _meaningful_steps(steps: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    for step in steps or []:
        expr = (step.get("expression") or "").strip()
        desc = (step.get("description") or "").strip()
        if expr or (desc and desc.lower() not in ("solution", "answer")):
            out.append(step)
    return out


def _has_gold_content(node: Dict) -> bool:
    if _meaningful_steps(node.get("gold_solution_steps") or []):
        return True
    if (node.get("final_answer") or "").strip():
        return True
    return any(_has_gold_content(s) for s in node.get("sub_questions") or [])


def _gold_tree_from_parsed(questions: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    for q in questions:
        node = {
            "number": q.get("number"),
            "label": (q.get("label") or "").strip(),
            "gold_solution_steps": q.get("gold_solution_steps") or [],
            "final_answer": (q.get("final_answer") or "").strip(),
            "final_answer_latex": (q.get("final_answer_latex") or "").strip(),
            "sub_questions": _gold_tree_from_parsed(q.get("sub_questions") or []),
        }
        if _has_gold_content(node):
            out.append(node)
    return out


_QMARKER = "<<QMARKER:{n}>>"

# Mathpix often misreads handwritten "Q2." as $a _ { 2 }$. or "Q3." as $\theta _ { 3 }$.
_HANDWRITTEN_Q_MARKER = re.compile(
    r"(?mx)"
    r"^\s*\$\s*[Qq]\s*_?\s*\{\s*(\d+)\s*\}\s*\$\.?\s*$"
    r"|^\s*\$\s*[aA]\s*_?\s*\{\s*(\d+)\s*\}\s*\$\.?\s*$"
    r"|^\s*\$\s*\\theta\s*_?\s*\{\s*(\d+)\s*\}\s*\$\.?\s*$"
    r"|^\s*(?:Question|Q)\s*(\d+)\s*[\.\):]?\s*$"
    r"|^\s*(\d{1,2})\.\s*$"
)


def _normalize_handwritten_key_markers(text: str) -> str:
    """Turn OCR question headings into split markers for handwritten answer keys."""
    if not text:
        return text
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip scanner watermarks.
    cleaned: List[str] = []
    for line in text.splitlines():
        normalised = re.sub(r"[^A-Za-z]+", "", line).lower()
        if normalised and re.search(
            r"(camscanner|scannedwith|adobescan|tinyscanner|microsoftlens|"
            r"geniusscan|scannerapp|notescan|officelens|clearscanner)",
            normalised,
        ):
            continue
        cleaned.append(line)
    text = "\n".join(cleaned)

    # Leading "(x)" / "(F)" on handwritten keys is usually Q1.
    text = re.sub(
        r"^\s*\(\s*[xXfF1]\s*\)\s*",
        _QMARKER.format(n=1) + "\n",
        text,
        count=1,
    )

    out_lines: List[str] = []
    for line in text.splitlines():
        m = _HANDWRITTEN_Q_MARKER.match(line.strip())
        if m:
            num = next(g for g in m.groups() if g)
            out_lines.append(_QMARKER.format(n=int(num)))
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def _extract_latex_chunks(body: str) -> List[str]:
    """Split an answer section into step-sized chunks (equations / lines)."""
    body = body.strip()
    if not body:
        return []
    chunks: List[str] = []
    buf: List[str] = []
    for line in body.splitlines():
        sl = line.strip()
        if not sl:
            if buf:
                chunks.append("\n".join(buf).strip())
                buf = []
            continue
        buf.append(sl)
    if buf:
        chunks.append("\n".join(buf).strip())

    if len(chunks) == 1 and "\\\\" in chunks[0]:
        parts = [p.strip() for p in re.split(r"\\\\", chunks[0]) if p.strip()]
        if len(parts) > 1:
            return parts
    return [c for c in chunks if c]


def _body_to_gold_steps(body: str) -> List[Dict]:
    chunks = _extract_latex_chunks(body)
    if not chunks and body.strip():
        chunks = [body.strip()]
    steps: List[Dict] = []
    for i, chunk in enumerate(chunks, start=1):
        steps.append(
            {
                "step_number": i,
                "description": "Solution",
                "expression": chunk,
                "points": 1,
                "required": True,
            }
        )
    return steps


def _parse_sub_part_answer_key(body: str) -> Tuple[List[Dict], List[Dict]]:
    """
    When an answer section uses (a) / (b) labels, return (sub_questions, top_steps).
    """
    parts = re.split(r"(?<=\n)(?=\([a-z]\)\s)", body, flags=re.IGNORECASE)
    if len(parts) <= 1:
        parts = re.split(r"(?<=\n)(?=[a-z]\)\s)", body, flags=re.IGNORECASE)
    if len(parts) <= 1:
        return [], _body_to_gold_steps(body)

    subs: List[Dict] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^\(([a-z])\)\s*(.*)$", part, re.IGNORECASE | re.DOTALL)
        if not m:
            m = re.match(r"^([a-z])\)\s*(.*)$", part, re.IGNORECASE | re.DOTALL)
        if not m:
            continue
        letter, content = m.group(1).lower(), m.group(2).strip()
        steps = _body_to_gold_steps(content)
        if not steps:
            continue
        subs.append(
            {
                "number": ord(letter) - ord("a") + 1,
                "label": f"({letter})",
                "text": "",
                "points": sum(s.get("points", 1) for s in steps),
                "gold_solution_steps": steps,
                "sub_questions": [],
            }
        )
    return subs, []


def _parse_handwritten_answer_key(text: str) -> List[Dict]:
    """Parse OCR'd handwritten marking schemes (Q1 / Q2 blocks, no 'Gold Solution:' labels)."""
    normalized = _normalize_handwritten_key_markers(text)
    if _QMARKER.format(n=1) not in normalized and not re.search(
        r"<<QMARKER:\d+>>", normalized
    ):
        return []

    sections: List[Dict] = []
    parts = re.split(r"<<QMARKER:(\d+)>>", normalized)
    # parts[0] is preamble; then num, body, num, body, ...
    i = 1
    while i + 1 < len(parts):
        num = int(parts[i])
        body = parts[i + 1].strip()
        i += 2
        if not body:
            continue
        subs, top_steps = _parse_sub_part_answer_key(body)
        node: Dict = {
            "number": num,
            "label": "",
            "text": "",
            "points": 1,
            "gold_solution_steps": top_steps,
            "sub_questions": subs,
            "page_num": 0,
        }
        if subs:
            node["points"] = sum(s.get("points", 1) for s in subs)
        elif top_steps:
            node["points"] = sum(s.get("points", 1) for s in top_steps)
        sections.append(node)
    return sections


def parse_answer_key_text(text: str) -> List[Dict]:
    """Parse an answer-key document into a slim gold-only question tree."""
    parser = ExamParser()
    parsed = parser.parse_answer_key(text)
    tree = _gold_tree_from_parsed(parsed.get("questions") or [])
    if tree:
        return tree
    handwritten = _parse_handwritten_answer_key(text)
    return _gold_tree_from_parsed(handwritten)


def parse_student_answer_sections(text: str) -> Dict[int, str]:
    """
    Map question number → raw answer body from OCR'd handwritten student work.
    Uses the same Q1 / Q2 marker normalization as answer-key parsing.
    """
    normalized = _normalize_handwritten_key_markers(text)
    if not re.search(r"<<QMARKER:\d+>>", normalized):
        return {}
    sections: Dict[int, str] = {}
    parts = re.split(r"<<QMARKER:(\d+)>>", normalized)
    i = 1
    while i + 1 < len(parts):
        num = int(parts[i])
        body = parts[i + 1].strip()
        if body:
            sections[num] = body
        i += 2
    return sections


def split_student_work_by_question_number(
    text: str,
    question_numbers: List[int],
) -> Optional[List[str]]:
    """
    Split a student answer sheet on Q-number markers.
    Returns one chunk per exam question number (empty string when that Q is missing).
    """
    sections = parse_student_answer_sections(text)
    if len(sections) < 2:
        return None
    out = [sections.get(num, "").strip() for num in question_numbers]
    if sum(1 for c in out if c) < max(2, len(question_numbers) // 3):
        return None
    return out


def build_exam_tree_for_alignment(questions: List[Any]) -> List[Dict]:
    """Build a nested tree from flat Question ORM rows (id, number, outline_title, text)."""
    by_parent: Dict[str, List[Any]] = {}
    top_level: List[Any] = []
    for q in questions:
        pid = getattr(q, "parent_question_id", None)
        if pid:
            by_parent.setdefault(pid, []).append(q)
        else:
            top_level.append(q)

    for lst in by_parent.values():
        lst.sort(key=lambda x: x.number)
    top_level.sort(key=lambda x: x.number)

    def wrap(q: Any) -> Dict:
        return {
            "id": q.id,
            "number": q.number,
            "label": (getattr(q, "outline_title", None) or "").strip(),
            "text_preview": ((q.text or "").strip())[:100],
            "sub_questions": [wrap(c) for c in by_parent.get(q.id, [])],
        }

    return [wrap(q) for q in top_level]


def _final_from_steps(steps: List[Dict]) -> str:
    if not steps:
        return ""
    for step in reversed(steps):
        expr = (step.get("expression") or "").strip()
        if expr:
            return expr
    return ""


def _pair_subquestions(
    exam_subs: List[Dict],
    key_subs: List[Dict],
    parent_path: str,
) -> List[Tuple[Dict, Optional[Dict], str]]:
    """Pair exam sub-questions with answer-key sub-parts by label, then by order."""
    if not exam_subs:
        return []

    pairs: List[Tuple[Dict, Optional[Dict], str]] = []
    key_by_label = {
        _normalize_label(k.get("label")): k
        for k in key_subs
        if _normalize_label(k.get("label"))
    }
    used_keys: set = set()

    for es in exam_subs:
        label = _normalize_label(es.get("label"))
        sub_path = f"{parent_path}.{label or es['number']}"
        ks = key_by_label.get(label) if label else None
        if ks is not None:
            used_keys.add(id(ks))
        pairs.append((es, ks, sub_path))

    remaining_exam = [es for es, ks, _ in pairs if ks is None]
    remaining_key = [k for k in key_subs if id(k) not in used_keys]
    for es, ks in zip(remaining_exam, remaining_key):
        for i, (e, k, _) in enumerate(pairs):
            if e is es and k is None:
                label = _normalize_label(es.get("label")) or es["number"]
                pairs[i] = (es, ks, f"{parent_path}.{label}")
                break

    return pairs


def _collect_unmatched_key_subs(
    key_subs: List[Dict],
    paired_keys: List[Optional[Dict]],
    parent_path: str,
) -> List[Dict]:
    paired_ids = {id(k) for k in paired_keys if k is not None}
    out: List[Dict] = []
    for ks in key_subs:
        if id(ks) in paired_ids:
            continue
        if not _has_gold_content(ks):
            continue
        out.append(
            {
                "number": ks.get("number"),
                "label": ks.get("label"),
                "path": f"{parent_path}.{_normalize_label(ks.get('label')) or ks.get('number')}",
                "preview": _preview_from_key_node(ks),
                "reason": "Could not map to an exam sub-part",
            }
        )
    return out


def _align_nodes(
    exam_node: Dict,
    key_node: Optional[Dict],
    path: str,
) -> Tuple[List[Dict], List[Dict]]:
    """Return (matched_entries, unmatched_key_subtrees)."""
    matched: List[Dict] = []
    unmatched_key: List[Dict] = []

    if key_node is None:
        return matched, unmatched_key

    key_steps = _meaningful_steps(key_node.get("gold_solution_steps") or [])
    exam_subs = exam_node.get("sub_questions") or []
    key_subs = key_node.get("sub_questions") or []

    if key_steps and not key_subs:
        matched.append(
            {
                "question_id": exam_node["id"],
                "question_number": exam_node["number"],
                "path": path,
                "gold_steps": key_steps,
                "final_answer": (key_node.get("final_answer") or "").strip()
                or _final_from_steps(key_steps),
                "final_answer_latex": (key_node.get("final_answer_latex") or "").strip(),
                "step_count": len(key_steps),
                "preview": (key_steps[0].get("expression") or key_steps[0].get("description") or "")[:160],
            }
        )
    elif key_subs and not exam_subs and key_steps:
        matched.append(
            {
                "question_id": exam_node["id"],
                "question_number": exam_node["number"],
                "path": path,
                "gold_steps": key_steps,
                "final_answer": (key_node.get("final_answer") or "").strip()
                or _final_from_steps(key_steps),
                "final_answer_latex": (key_node.get("final_answer_latex") or "").strip(),
                "step_count": len(key_steps),
                "preview": (key_steps[0].get("expression") or key_steps[0].get("description") or "")[:160],
            }
        )

    sub_pairs = _pair_subquestions(exam_subs, key_subs, path)
    paired_key_subs = [ks for _, ks, _ in sub_pairs]
    unmatched_key.extend(_collect_unmatched_key_subs(key_subs, paired_key_subs, path))
    for es, ks, sub_path in sub_pairs:
        sub_matched, sub_unmatched = _align_nodes(es, ks, sub_path)
        matched.extend(sub_matched)
        unmatched_key.extend(sub_unmatched)

    return matched, unmatched_key


def _preview_from_key_node(node: Dict) -> str:
    steps = _meaningful_steps(node.get("gold_solution_steps") or [])
    if steps:
        return (steps[0].get("expression") or steps[0].get("description") or "")[:160]
    subs = node.get("sub_questions") or []
    if subs:
        return _preview_from_key_node(subs[0])
    return ""


def align_answer_key(exam_tree: List[Dict], key_tree: List[Dict]) -> Dict[str, Any]:
    """
    Match parsed answer-key entries to existing exam questions.

    Returns preview payload with matched / unmatched lists (no DB writes).
    """
    key_by_number = {q["number"]: q for q in key_tree if q.get("number") is not None}
    matched: List[Dict] = []
    unmatched_exam: List[Dict] = []
    unmatched_key: List[Dict] = []
    used_key_numbers: set = set()

    for eq in exam_tree:
        kn = key_by_number.get(eq["number"])
        path = f"Q{eq['number']}"
        if kn is None:
            unmatched_exam.append(
                {
                    "question_id": eq["id"],
                    "question_number": eq["number"],
                    "path": path,
                    "text_preview": eq.get("text_preview", ""),
                }
            )
            continue

        used_key_numbers.add(eq["number"])
        node_matches, node_unmatched_key = _align_nodes(eq, kn, path)
        matched.extend(node_matches)
        unmatched_key.extend(node_unmatched_key)

        if not node_matches and _has_gold_content(kn):
            unmatched_key.append(
                {
                    "number": kn.get("number"),
                    "label": kn.get("label"),
                    "path": path,
                    "preview": _preview_from_key_node(kn),
                    "reason": "Could not map to a specific question or sub-part",
                }
            )

    for kn in key_tree:
        num = kn.get("number")
        if num is not None and num not in used_key_numbers:
            unmatched_key.append(
                {
                    "number": num,
                    "label": kn.get("label"),
                    "path": f"Q{num}",
                    "preview": _preview_from_key_node(kn),
                    "reason": "No matching exam question",
                }
            )

    return {
        "matched": matched,
        "unmatched_exam_questions": unmatched_exam,
        "unmatched_key_sections": unmatched_key,
        "summary": {
            "key_sections_found": len(key_tree),
            "matched_count": len(matched),
            "unmatched_exam_count": len(unmatched_exam),
            "unmatched_key_count": len(unmatched_key),
        },
    }
