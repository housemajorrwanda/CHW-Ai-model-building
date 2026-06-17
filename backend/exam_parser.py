import re
from typing import List, Dict, Optional, Tuple
import logging

from ocr.text_rich_content import looks_like_math_ocr, looks_like_equation_line, normalize_exam_ocr_text

logger = logging.getLogger(__name__)

_ROMAN_NUMERAL = r"i{1,3}|iv|vi{0,3}|ix|x"
_MARK_RE = re.compile(r"[\[\(](\d+)\s*(?:points?|pts?|marks?)[\]\)]", re.IGNORECASE)
_GOLD_MARKER_RE = re.compile(
    r"(?i)(?:"
    r"gold(?:en)?\s+(?:solution|answer|soltion|solu\w*)"
    r"|model\s+answer"
    r"|expected\s+answer"
    r"|correct\s+answer"
    r"|answer\s+key"
    r"|(?:worked\s+)?solution\s*:"
    r"|(?:final\s+)?answer\s*:"
    r")"
)


class ExamParser:
    """
    Parses exam uploads following the official EXAM UPLOAD TEMPLATE and common
    exam-paper layouts (e.g. chemistry tests with A/B/C parts and i/ii/iii sub-parts).
    """

    def __init__(self):
        self.question_patterns = [
            r"(?:question|q)\s*[:\.]?\s*(\d+)",
            r"(?:question|q)\s+(\d+)",
            r"question\s*(\d+)\s*[\[\(]",
            r"^\s*[Qq]\s*(\d{1,2})\.?\s",
            r"^\s*(\d{1,2})\.(?!\d)\s+\S",
            r"^\s*(\d{1,2}):\s+\S",
            r"problem\s*(\d+)",
            r"question\s*(\d+)",
        ]

        self.gold_solution_markers = [
            "gold solution:",
            "model answer:",
            "expected answer:",
            "correct answer:",
            "answer key:",
            "solution:",
            "answer:",
            "answers:",
            "key:",
            "gold solution",
            "model answer",
            "worked solution",
        ]

        self.step_markers = [
            "step", "solution step", "working", "final answer", "answer ="
        ]

        self.title_markers = ["exam title:", "title:", "exam name:", "name:"]
        self.description_markers = ["description:", "instructions:", "instruction:", "directions:"]

        self._sub_q_re = re.compile(
            r"^\s*(?:"
            r"\([a-z]\)\s*"
            r"|\([ivx]+\)\s*"
            r"|[a-z]\)\s+"
            r"|(?:part\s+)?\([a-z]\)\s*:"
            r")",
            re.IGNORECASE,
        )

        self._page_marker_re = re.compile(
            r"^(?:-+\s*\d+\s+of\s+\d+\s*-+|<<PAGEBREAK>>|page\s+\d+\s+of\s+\d+)$",
            re.IGNORECASE,
        )

        self._roman_paren_re = re.compile(
            rf"^\s*\(({_ROMAN_NUMERAL})\)\s*(.*)$", re.IGNORECASE
        )
        self._roman_dot_re = re.compile(
            rf"^\s*({_ROMAN_NUMERAL})\.\s+(.*)$", re.IGNORECASE
        )
        self._upper_letter_re = re.compile(r"^\s*([A-E])\.\s+(.*)$")
        self._lower_sub_re = re.compile(
            r"^\s*(?:\(([a-z])\)|([a-z])\)\s+)(.*)$", re.IGNORECASE
        )
        self._numeric_sub_re = re.compile(r"^\s*(\d{1,2})\.\s+(.*)$")

    def _document_has_gold_markers(self, text: str) -> bool:
        return bool(_GOLD_MARKER_RE.search(text or ""))

    def _is_gold_marker_line(self, line: str) -> bool:
        return bool(_GOLD_MARKER_RE.search(line or ""))

    def _split_gold_marker_line(self, line: str) -> Tuple[str, str]:
        m = _GOLD_MARKER_RE.search(line or "")
        if not m:
            return "", (line or "").strip()
        after = (line[m.end():] or "").strip()
        if after.startswith(":"):
            after = after[1:].strip()
        return m.group(0), after

    # ------------------------------------------------------------------
    # Text normalisation helpers
    # ------------------------------------------------------------------

    def _normalize_ocr_text(self, text: str) -> str:
        if not text:
            return text
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\x0c", "\n<<PAGEBREAK>>\n", text)
        if "<<PAGEBREAK>>" in text:
            # pdftotext injects <<PAGEBREAK>> at form feeds; drop footer page numbers to avoid double-counting.
            text = re.sub(
                r"(?m)^\s*(?:-+\s*\d+\s+of\s+\d+\s*-+|page\s+\d+\s+of\s+\d+)\s*$",
                "",
                text,
                flags=re.IGNORECASE,
            )
        text = re.sub(r"\n\s*\n", "\n\n", text)
        # PDF layout artifacts: "3.\ (i)" → "3. (i)"
        text = re.sub(r"(\d+)\.\\\s+", r"\1. ", text)
        text = re.sub(r"(\d+)\.\\\(", r"\1. (", text)
        replacements = [
            (r"Quest1on", "Question"),
            (r"quest1on", "question"),
            (r"Q1estion", "Question"),
            (r"Gold\s*S0lution", "Gold Solution"),
            (r"gold\s*s0lution", "gold solution"),
            (r"Gold\s*soltion", "Gold Solution"),
            (r"gold\s*soltion", "Gold Solution"),
            (r"Golden\s*soltion", "Gold Solution"),
            (r"golden\s*soltion", "Gold Solution"),
            (r"Golden\s*answer\s*\?", "Golden answer:"),
            (r"golden\s*answer\s*\?", "Golden answer:"),
            (r"Aiscription", "Description"),
            (r"\bSter\s+", "Step "),
            (r"\bStel\s+", "Step "),
            (r"\bStes\s+", "Step "),
            (r"\bSte\s+", "Step "),
            (r"S0lution", "Solution"),
        ]
        for old, new in replacements:
            text = re.sub(old, new, text, flags=re.IGNORECASE)
        # Drop scanner-app watermark lines before question parsing.
        cleaned: List[str] = []
        for line in text.splitlines():
            sl = line.strip()
            normalised = re.sub(r"[^A-Za-z]+", "", sl).lower()
            if normalised and re.search(
                r"(camscanner|scannedwith|adobescan|tinyscanner|microsoftlens|"
                r"geniusscan|scannerapp|notescan|officelens|clearscanner)",
                normalised,
            ):
                continue
            cleaned.append(line)
        text = "\n".join(cleaned)
        return text

    def _ensure_question_line_breaks(self, text: str) -> str:
        if not text or not text.strip():
            return text
        text = re.sub(r"(?i)(Question|Q)\s*(\d+)", r"\1 \2", text)
        text = re.sub(
            r"(?<!\n)(\s*)((?:Question|Q)\s*[:\.]?\s*\d+)",
            r"\n\2",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"(\.|\?)\s+(\d+)\s*[\.\)]\s+", r"\1\n\2. ", text)
        text = re.sub(
            r"(?<!\n)(\s*)((?:Gold(?:en)?\s+(?:Solution|Answer|Soltion)|Model\s+Answer|Answer\s+Key|Expected\s+Answer|Correct\s+Answer|Solution:)[\s:?]*)",
            r"\n\2",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"(?<!\n)(\s*)(Golden\s+answer\s*:?)",
            r"\n\2",
            text,
            flags=re.IGNORECASE,
        )
        # Handwritten scans: "Q6." / "46." (Q misread) / "6." on their own line.
        text = re.sub(r"(?<!\n)(\s*)([Qq]\s*\d{1,2}\.?)\s*$", r"\n\2", text, flags=re.MULTILINE)
        text = re.sub(r"(?<!\n)(\s*)(\d{1,2}\.)\s*$", r"\n\2", text, flags=re.MULTILINE)
        # Sub-parts like "a) Find the area" on handwritten uploads (line start only).
        text = re.sub(r"(?m)^(\s*)([a-hj-z]\)\s+\S)", r"\n\2", text, flags=re.IGNORECASE)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def parse_answer_key(self, text: str) -> Dict:
        """
        Parse a marking-scheme / answer-key document (questions optional).

        Uses the same question-number and gold-solution parsing as full exam
        uploads, with extra line breaks for answer-only headings.
        """
        text = self._normalize_ocr_text(text)
        text = self._ensure_answer_key_line_breaks(text)
        raw_lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines = []
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            if i + 1 < len(raw_lines) and re.match(r"^(?:question|q|answer)\s*$", line, re.IGNORECASE):
                next_line = raw_lines[i + 1]
                if re.match(r"^\d+\s*[\.\):]", next_line):
                    line = line + " " + next_line
                    i += 1
            lines.append(line)
            i += 1

        questions = self._extract_questions(lines)
        return {"questions": questions}

    def _ensure_answer_key_line_breaks(self, text: str) -> str:
        """Insert breaks before answer-key-only headings (marking scheme, Q1 answer, etc.)."""
        text = self._ensure_question_line_breaks(text)
        patterns = [
            r"(?<!\n)(\s*)((?:Marking\s+Scheme|Mark\s+Scheme|Answer\s+Sheet|Answer\s+Key)\s*[:\-]?\s*)",
            r"(?<!\n)(\s*)((?:Answer|Solution|Key)\s*(?:to\s+)?(?:Question|Q)\s*\d+)",
            r"(?<!\n)(\s*)(Q\s*\d+\s*[\-–—:]\s*(?:Answer|Solution|Key|Marking))",
            r"(?<!\n)(\s*)((?:Question|Q)\s*\d+\s*[\-–—:]\s*(?:Answer|Solution|Key|Marking))",
        ]
        for pat in patterns:
            text = re.sub(pat, r"\n\2", text, flags=re.IGNORECASE)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    def parse_exam(self, text: str) -> Dict:
        text = self._normalize_ocr_text(text)
        text = self._ensure_question_line_breaks(text)
        raw_lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines = []
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            if i + 1 < len(raw_lines) and re.match(r"^(?:question|q)\s*$", line, re.IGNORECASE):
                next_line = raw_lines[i + 1]
                if re.match(r"^\d+\s*[\.\):]", next_line):
                    line = line + " " + next_line
                    i += 1
            lines.append(line)
            i += 1

        title = self._extract_title(lines)
        description = self._extract_description(lines)
        questions = self._extract_questions(lines)
        if not questions:
            questions = self._fallback_handwritten_questions(lines)
        if not self._document_has_gold_markers(text):
            self._promote_math_to_gold_steps(questions)
        total_points = sum(self._question_points_total(q) for q in questions)

        return {
            "title": title,
            "description": description,
            "questions": questions,
            "total_points": total_points,
        }

    def _question_points_total(self, question: Dict) -> int:
        subs = question.get("sub_questions") or []
        if subs:
            return sum(self._question_points_total(sub) for sub in subs)
        return question.get("points") or 1

    # ------------------------------------------------------------------
    # Title / description extraction
    # ------------------------------------------------------------------

    def _extract_title(self, lines: List[str]) -> str:
        for line in lines[:20]:
            if looks_like_math_ocr(line) or looks_like_equation_line(line):
                continue
            if self._is_sub_question_line(line) or re.match(r"^\s*[a-h]\)\s*$", line, re.I):
                continue
            lower = line.lower().strip()
            for marker in self.title_markers:
                if marker in lower:
                    idx = lower.find(marker)
                    after_marker = line[idx + len(marker):].strip()
                    if after_marker.startswith(":"):
                        after_marker = after_marker[1:].strip()
                    elif ":" in after_marker:
                        after_marker = after_marker.split(":", 1)[-1].strip()
                    if after_marker and len(after_marker) > 2:
                        if not looks_like_math_ocr(after_marker) and not looks_like_equation_line(after_marker):
                            return after_marker
            if (
                any(word in lower for word in ["exam", "test", "quiz", "assessment"])
                and not self._is_question_header(line)
                and len(line.strip()) > 3
            ):
                return line.strip()
        for line in lines[:10]:
            s = line.strip()
            if looks_like_math_ocr(s) or looks_like_equation_line(s):
                continue
            if self._is_question_header(line):
                continue
            if self._is_sub_question_line(line) or re.match(r"^\s*[a-h]\)\s*$", s, re.I):
                continue
            if (
                s
                and s != "="
                and len(s) > 1
                and not re.match(r"^\d+[\.\)]\s*$", s)
                and not re.match(r"^(?:question|q)\s*\d+", s, re.I)
            ):
                return s
        return "Imported Exam"

    def _extract_description(self, lines: List[str]) -> str:
        desc_lines = []
        in_desc = False

        for line in lines:
            lower = line.lower().strip()
            for marker in self.description_markers:
                if marker in lower:
                    in_desc = True
                    after = line.split(":", 1)[-1].strip() if ":" in line else ""
                    if after:
                        desc_lines.append(after)
                    break
            else:
                if in_desc:
                    if self._is_question_header(line) or any(m in lower for m in self.gold_solution_markers):
                        break
                    if re.match(r"^\s*SECTION\s", line, re.I):
                        break
                    desc_lines.append(line)

        result = " ".join(desc_lines).strip()
        if result:
            return result
        intro = []
        for line in lines[:30]:
            if self._is_question_header(line):
                break
            s = line.strip()
            if not s or s == "=" or len(s) < 2:
                continue
            if re.match(r"^(?:exam\s+)?title\s*:", s, re.I) or re.match(r"^\d+[\.\)]\s*$", s):
                continue
            if self._is_sub_question_line(line) or re.match(r"^\s*[a-h]\)\s*", s, re.I):
                continue
            if looks_like_math_ocr(s) or looks_like_equation_line(s):
                continue
            if re.match(r"^\s*SECTION\s", s, re.I):
                continue
            intro.append(s)
        if intro and len(" ".join(intro)) < 600:
            return " ".join(intro).strip()
        return "Imported exam"

    # ------------------------------------------------------------------
    # Question-header detection
    # ------------------------------------------------------------------

    def _is_question_header(self, line: str) -> bool:
        return self._find_question_number(line, last_q_num=0, sub_depth=0) is not None

    def _find_question_number(
        self, line: str, last_q_num: int = 0, sub_depth: int = 0
    ) -> Optional[int]:
        if self._page_marker_re.match(line):
            return None
        if re.match(r"^\s*SECTION\s", line, re.I):
            return None

        stripped = line.strip()

        # Handwritten "Q6" / "Q 6."
        m = re.match(r"^[Qq]\s*(\d{1,2})\.?\s*\.?\s*$", stripped)
        if m:
            return int(m.group(1))
        m = re.match(r"^[Qq]\s*(\d{1,2})\.?\s+\S", stripped)
        if m:
            return int(m.group(1))

        # OCR often misreads "Q6." as "46." on its own line.
        m = re.match(r"^4(\d)\.\s*$", stripped)
        if m:
            return int(m.group(1))

        # Standalone question number: "6." with nothing else on the line.
        m = re.match(r"^(\d{1,2})\.\s*$", stripped)
        if m:
            num = int(m.group(1))
            if num > last_q_num:
                return num

        for pattern in self.question_patterns[:4]:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return int(match.group(1))

        m = re.match(r"^\s{0,4}(\d{1,2})\.(?!\d)\s+\S", line)
        if m:
            num = int(m.group(1))
            # Only a strictly higher number starts a new top-level question (e.g. 9 → 10).
            # Lines like "1. Compound A…" under Q8 are numbered sub-parts, not Q1.
            if num > last_q_num:
                return num
            return None

        for pattern in self.question_patterns[4:]:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                if num > last_q_num:
                    return num
                return None
        return None

    def _fallback_handwritten_questions(self, lines: List[str]) -> List[Dict]:
        """
        When OCR finds sub-parts (a), b) …) but no Question heading, build one
        parent question from the scan — common on single-page handwritten exams.
        """
        subs: List[Dict] = []
        current: Optional[Dict] = None
        for line in lines:
            if self._page_marker_re.match(line):
                continue
            lower = line.lower()
            if any(m in lower for m in self.gold_solution_markers):
                break
            marker = self._detect_sub_marker(
                line, sub_depth=0, last_q_num=0, has_roman_subs=False
            )
            if marker:
                _kind, label, text_after, _level = marker
                if current is not None:
                    self._flush_sub_buffer(current)
                    subs.append(current)
                current = self._new_sub_question(label, text_after)
            elif current is not None and line.strip():
                self._append_sub_content(current, line)
        if current is not None:
            self._flush_sub_buffer(current)
            subs.append(current)
        if not subs:
            return []
        for sub in subs:
            sub.pop("_buffer", None)
        return [{
            "number": 1,
            "text": "",
            "points": sum(s.get("points", 1) for s in subs),
            "gold_solution_steps": [],
            "sub_questions": subs,
            "page_num": 0,
        }]

    # ------------------------------------------------------------------
    # Sub-question helpers
    # ------------------------------------------------------------------

    def _has_mark(self, text: str) -> bool:
        return bool(_MARK_RE.search(text or ""))

    def _extract_points_from_text(self, text: str) -> Tuple[str, int]:
        pm = _MARK_RE.search(text or "")
        if pm:
            pts = int(pm.group(1))
            cleaned = _MARK_RE.sub("", text, count=1).strip()
            return cleaned, pts
        return (text or "").strip(), 1

    def _next_sub_label(self, siblings: List[Dict], proposed: str) -> str:
        """Avoid duplicate (a) labels when a scan has multiple figure groups."""
        used = {(s.get("label") or "").strip().lower() for s in siblings}
        label = proposed
        if label.lower() not in used:
            return label
        idx = len(siblings)
        while idx < 26:
            candidate = f"({chr(ord('a') + idx)})"
            if candidate.lower() not in used:
                return candidate
            idx += 1
        return proposed

    def _new_sub_question(self, label: str, text: str = "") -> Dict:
        text_clean, pts = self._extract_points_from_text(text)
        return {
            "label": label,
            "text": text_clean,
            "points": pts,
            "sub_questions": [],
            "gold_solution_steps": [],
        }

    def _is_sub_question_line(self, line: str) -> bool:
        return self._detect_sub_marker(line, sub_depth=0, last_q_num=0, has_roman_subs=False) is not None

    def _strip_sub_question_marker(self, line: str) -> str:
        marker = self._detect_sub_marker(line, sub_depth=0, last_q_num=0, has_roman_subs=False)
        if marker:
            return marker[2]
        return self._sub_q_re.sub("", line.strip(), count=1).strip()

    def _extract_sub_letter(self, line: str) -> str:
        m = re.match(r"^\s*\(?([a-z])\)?\s*", line.strip(), re.IGNORECASE)
        if m:
            return m.group(1).lower()
        marker = self._detect_sub_marker(line, sub_depth=0, last_q_num=0, has_roman_subs=False)
        if marker:
            return marker[1].lower()
        return ""

    def _looks_like_mc_option(self, line: str) -> bool:
        m = self._upper_letter_re.match(line)
        if not m:
            return False
        body = m.group(2).strip()
        if self._has_mark(body):
            return False
        if len(body) <= 80:
            return True
        return False

    def _parent_is_numeric_sub(self, sub: Optional[Dict]) -> bool:
        if not sub:
            return False
        label = str(sub.get("label") or "").strip().rstrip(".")
        return label.isdigit()

    def _detect_sub_marker(
        self,
        line: str,
        sub_depth: int,
        last_q_num: int,
        has_roman_subs: bool,
        parent_has_mark: bool = False,
    ) -> Optional[Tuple[str, str, str, int]]:
        """
        Returns (kind, label, text_after, outline_level) when line starts a sub-part.
        kind is 'roman', 'letter', 'lower', or 'numeric'.
        """
        m = self._roman_paren_re.match(line)
        if m:
            label = f"({m.group(1).lower()})"
            return ("roman", label, m.group(2).strip(), 2)

        m = self._roman_dot_re.match(line)
        if m:
            label = f"{m.group(1).lower()}."
            return ("roman", label, m.group(2).strip(), 2)

        m = self._lower_sub_re.match(line)
        if m:
            letter = (m.group(1) or m.group(2)).lower()
            text_after = m.group(3).strip()
            if letter in ("t", "l", "r") and re.search(r"\\", text_after):
                pass
            elif m.group(2) and letter > "j":
                pass
            else:
                return ("lower", f"({letter})", text_after, 2)

        m = re.match(r"^\s*([a-h])\)\s*$", line.strip(), re.IGNORECASE)
        if m:
            return ("lower", f"({m.group(1).lower()})", "", 2)

        if self._sub_q_re.match(line):
            text = self._strip_sub_question_marker(line)
            letter = self._extract_sub_letter(line)
            return ("lower", f"({letter})", text, 2)

        m = self._upper_letter_re.match(line)
        if m:
            label = m.group(1).upper()
            body = m.group(2).strip()
            has_own_mark = self._has_mark(body)
            if sub_depth == 0 and not has_roman_subs:
                return ("letter", label, body, 2)
            if has_roman_subs and sub_depth >= 1:
                if has_own_mark:
                    return ("letter", label, body, 3)
                if self._looks_like_mc_option(line):
                    return None
                return None
            if has_own_mark:
                return ("letter", label, body, 2)
            if self._looks_like_mc_option(line):
                return None
            return ("letter", label, body, 2)

        m = self._numeric_sub_re.match(line)
        if m:
            num = int(m.group(1))
            body = m.group(2).strip()
            if num <= last_q_num:
                level = 3 if sub_depth >= 1 else 2
                return ("numeric", str(num), body, level)
        return None

    def _append_sub_content(self, sub: Dict, line: str) -> None:
        if sub.get("_buffer") is None:
            sub["_buffer"] = []
        sub["_buffer"].append(line)

    def _flush_sub_buffer(self, sub: Dict) -> None:
        buf = sub.pop("_buffer", None)
        if not buf:
            return
        extra = "\n".join(buf).strip()
        if extra:
            sub["text"] = (sub.get("text") or "").strip()
            sub["text"] = f"{sub['text']}\n{extra}".strip() if sub["text"] else extra
            text_clean, pts = self._extract_points_from_text(sub["text"])
            sub["text"] = text_clean
            sub["points"] = pts

    def _finalize_sub_tree(self, subs: List[Dict]) -> List[Dict]:
        out = []
        for sub in subs:
            self._flush_sub_buffer(sub)
            sub.pop("_buffer", None)
            child_subs = self._finalize_sub_tree(sub.get("sub_questions") or [])
            if child_subs:
                sub["sub_questions"] = child_subs
                if sub.get("points", 1) <= 1:
                    child_pts = sum(self._question_points_total(c) for c in child_subs)
                    if child_pts > 1:
                        sub["points"] = child_pts
            out.append(sub)
        return out

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    def _is_step_line(self, line: str) -> bool:
        lower = line.lower()
        return (
            any(marker in lower for marker in self.step_markers)
            or bool(re.match(r"^\s*\d+[\.\)]\s*", line))
            or line.startswith("=")
        )

    def _parse_step(self, line: str, step_number: int) -> Dict:
        clean_line = re.sub(r"^(?:step\s*\d*[:\.]?\s*)", "", line, flags=re.IGNORECASE).strip()
        clean_line = re.sub(r"^\s*\d+[\.\)]\s*", "", clean_line).strip()

        points = 1
        if "&" in clean_line:
            left, right = clean_line.split("&", 1)
            clean_line = left.strip()
            loose_pts = re.search(r"(\d+)\s*(?:point|points|pts?|marks?)", right, re.I)
            if loose_pts:
                points = int(loose_pts.group(1))

        clean_line = re.sub(r"\s*&\s*$", "", clean_line).strip()
        clean_line = re.sub(r"\\quad\s*$", "", clean_line).strip()

        points_match = _MARK_RE.search(clean_line)
        if points_match:
            points = int(points_match.group(1))
            clean_line = _MARK_RE.sub("", clean_line, count=1).strip()
        elif points == 1:
            loose_pts = re.search(r"\((\d+)\s*(?:point|points|pts?|marks?)\)", clean_line, re.I)
            if loose_pts:
                points = int(loose_pts.group(1))
                clean_line = clean_line[: loose_pts.start()].strip()

        return {
            "step_number": step_number,
            "description": f"Step {step_number}",
            "expression": clean_line,
            "points": points,
            "required": step_number <= 3,
        }

    # ------------------------------------------------------------------
    # Core question extraction
    # ------------------------------------------------------------------

    def _extract_questions(self, lines: List[str]) -> List[Dict]:
        questions: List[Dict] = []
        current_question: Optional[Dict] = None
        current_section = "text"
        current_steps: List[Dict] = []

        current_sub: Optional[Dict] = None
        sub_parent: Optional[Dict] = None
        sub_depth = 0
        has_roman_subs = False

        current_sol_letter: str = ""
        current_sol_subs: Dict[str, List[str]] = {}

        current_page = 0
        last_q_num = 0
        gold_target: Optional[Dict] = None

        def flush_gold_steps_to_target():
            nonlocal current_steps, gold_target
            if gold_target is not None and current_steps:
                gold_target["gold_solution_steps"] = current_steps[:]
            current_steps = []
            gold_target = None

        def flush_current_sub():
            nonlocal current_sub, sub_depth, sub_parent
            if current_sub is None or current_question is None:
                current_sub = None
                sub_parent = None
                sub_depth = 0
                return

            self._flush_sub_buffer(current_sub)

            if sub_parent is not None:
                current_sub = sub_parent
                sub_parent = None
                sub_depth = 1
                return

            parent_list = current_question.setdefault("sub_questions", [])
            parent_list.append(current_sub)
            current_sub = None
            sub_depth = 0

        def flush_all_subs():
            while current_sub is not None:
                flush_current_sub()

        def finalize_question(q: Dict):
            nonlocal current_sol_subs, current_sol_letter, has_roman_subs

            flush_gold_steps_to_target()

            if current_sub is not None:
                flush_all_subs()

            q["sub_questions"] = self._finalize_sub_tree(q.get("sub_questions") or [])

            if current_sol_subs and q.get("sub_questions"):
                for i, sub_q in enumerate(q["sub_questions"]):
                    letter = chr(ord("a") + i)
                    if letter in current_sol_subs:
                        sol_raw = " ".join(current_sol_subs[letter]).strip()
                        sol_text, sol_pts = self._extract_points_from_text(sol_raw)
                        sub_q["gold_solution_steps"] = [{
                            "step_number": 1,
                            "description": "Solution",
                            "expression": sol_text,
                            "points": sol_pts,
                            "required": True,
                        }]
                if not q.get("gold_solution_steps"):
                    q["gold_solution_steps"] = []
                    for i, sub_q in enumerate(q["sub_questions"]):
                        letter = chr(ord("a") + i)
                        if letter in current_sol_subs:
                            sol_raw = " ".join(current_sol_subs[letter]).strip()
                            sol_text, sol_pts = self._extract_points_from_text(sol_raw)
                            q["gold_solution_steps"].append({
                                "step_number": i + 1,
                                "description": f"Part ({letter})",
                                "expression": sol_text,
                                "points": sol_pts,
                                "required": True,
                            })
            elif current_sol_subs:
                # Answer-key layout: (a)(b)(c) solutions without question sub-parts in the document.
                for letter in sorted(current_sol_subs.keys()):
                    sol_raw = " ".join(current_sol_subs[letter]).strip()
                    if not sol_raw:
                        continue
                    sol_text, sol_pts = self._extract_points_from_text(sol_raw)
                    q.setdefault("sub_questions", []).append(
                        {
                            "label": f"{letter}.",
                            "text": "",
                            "points": sol_pts,
                            "sub_questions": [],
                            "gold_solution_steps": [
                                {
                                    "step_number": 1,
                                    "description": "Solution",
                                    "expression": sol_text,
                                    "points": sol_pts,
                                    "required": True,
                                }
                            ],
                        }
                    )
            elif current_steps:
                q["gold_solution_steps"] = current_steps

            current_sol_subs = {}
            current_sol_letter = ""
            has_roman_subs = False

        i = 0
        while i < len(lines):
            line = lines[i]
            lower = line.lower()

            if self._page_marker_re.match(line):
                current_page += 1
                i += 1
                continue

            question_match = self._find_question_number(line, last_q_num=last_q_num, sub_depth=sub_depth)
            if question_match:
                if current_question is not None:
                    flush_gold_steps_to_target()
                    flush_all_subs()
                    finalize_question(current_question)
                    questions.append(current_question)

                last_q_num = question_match
                current_question = {
                    "number": question_match,
                    "text": "",
                    "points": 1,
                    "gold_solution_steps": [],
                    "sub_questions": [],
                    "page_num": current_page,
                }
                current_section = "text"
                current_steps = []
                current_sub = None
                sub_parent = None
                sub_depth = 0
                has_roman_subs = False
                current_sol_letter = ""
                current_sol_subs = {}

                text_part = re.sub(r"(?:question|q)\s*[:\.]?\s*\d+", "", line, flags=re.IGNORECASE).strip()
                text_part = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", text_part).strip()
                text_part = re.sub(r"^[:\s]+", "", text_part).strip()

                points_match = _MARK_RE.search(text_part)
                if points_match:
                    current_question["points"] = int(points_match.group(1))
                    text_part = _MARK_RE.sub("", text_part, count=1).strip()

                if text_part:
                    inline_paren = self._roman_paren_re.match(text_part)
                    inline_dot = self._roman_dot_re.match(text_part) if not inline_paren else None
                    if inline_paren:
                        label = f"({inline_paren.group(1).lower()})"
                        current_sub = self._new_sub_question(label, inline_paren.group(2).strip())
                        has_roman_subs = True
                        sub_depth = 1
                    elif inline_dot:
                        label = f"{inline_dot.group(1).lower()}."
                        current_sub = self._new_sub_question(label, inline_dot.group(2).strip())
                        has_roman_subs = True
                        sub_depth = 1
                    else:
                        current_question["text"] = text_part

            elif current_question is not None:
                if self._is_gold_marker_line(line):
                    if current_sub is not None:
                        self._flush_sub_buffer(current_sub)
                    else:
                        flush_all_subs()
                    flush_gold_steps_to_target()
                    gold_target = current_sub if current_sub is not None else current_question
                    current_section = "solution"
                    current_sol_letter = ""
                    _, gold_text = self._split_gold_marker_line(line)
                    if gold_text and not self._is_sub_question_line(gold_text):
                        current_steps = [self._parse_step(gold_text, 1)]
                    else:
                        current_steps = []

                elif current_section == "solution":
                    if self._is_sub_question_line(line) and not current_sol_letter:
                        text_after = self._strip_sub_question_marker(line)
                        looks_like_question = (
                            self._has_mark(text_after)
                            or bool(
                                re.search(
                                    r"(?i)\b(solve|find|evaluate|what is|explain|show|prove|calculate|describe)\b",
                                    text_after,
                                )
                            )
                        )
                        if looks_like_question:
                            flush_gold_steps_to_target()
                            current_section = "text"
                            marker = self._detect_sub_marker(
                                line, sub_depth=0, last_q_num=last_q_num, has_roman_subs=False
                            )
                            if marker:
                                _kind, label, sub_text, _level = marker
                                flush_current_sub()
                                siblings = current_question.setdefault("sub_questions", [])
                                label = self._next_sub_label(siblings, label)
                                current_sub = self._new_sub_question(label, sub_text)
                                sub_depth = 1
                            i += 1
                            continue

                    if self._is_sub_question_line(line):
                        letter = self._extract_sub_letter(line)
                        text_after = self._strip_sub_question_marker(line)
                        current_sol_letter = letter
                        if letter not in current_sol_subs:
                            current_sol_subs[letter] = []
                        if text_after:
                            current_sol_subs[letter].append(text_after)
                    elif current_sol_letter:
                        if line and not self._is_question_header(line):
                            current_sol_subs[current_sol_letter].append(line)
                    else:
                        is_new_step = (
                            self._is_step_line(line)
                            or bool(re.match(r"^(?:final\s+)?answer\s*[:=]", lower))
                            or (line.strip().startswith("=") and len(line.strip()) > 1)
                            or bool(re.match(r"^\s*\d+[\.\)]\s*\S", line))
                        )
                        if is_new_step:
                            step = self._parse_step(line, len(current_steps) + 1)
                            current_steps.append(step)
                        elif line and not self._is_question_header(line):
                            if current_steps:
                                current_steps[-1]["expression"] += " " + line
                            else:
                                current_steps.append(self._parse_step(line, 1))

                elif current_section == "text":
                    parent_has_mark = bool(current_sub and self._has_mark(current_sub.get("text", "")))
                    marker = self._detect_sub_marker(
                        line,
                        sub_depth=sub_depth,
                        last_q_num=last_q_num,
                        has_roman_subs=has_roman_subs,
                        parent_has_mark=parent_has_mark,
                    )

                    if marker:
                        kind, label, text_after, outline_level = marker
                        if kind in ("roman", "lower") and self._parent_is_numeric_sub(current_sub):
                            self._append_sub_content(current_sub, line)
                        elif kind == "roman":
                            has_roman_subs = True
                            flush_all_subs()
                            current_sub = self._new_sub_question(label, text_after)
                            sub_depth = 1
                        elif kind == "numeric":
                            if current_sub is not None and has_roman_subs:
                                if self._parent_is_numeric_sub(current_sub):
                                    self._flush_sub_buffer(current_sub)
                                    current_sub = sub_parent
                                    sub_parent = None
                                    sub_depth = 1
                                child = self._new_sub_question(label, text_after)
                                parent = current_sub
                                parent.setdefault("sub_questions", []).append(child)
                                sub_parent = parent
                                current_sub = child
                                sub_depth = 2
                            else:
                                flush_current_sub()
                                current_sub = self._new_sub_question(label, text_after)
                                sub_depth = 1
                        elif kind == "letter" and outline_level >= 3 and current_sub is not None:
                            child = self._new_sub_question(label, text_after)
                            parent = current_sub
                            parent.setdefault("sub_questions", []).append(child)
                            sub_parent = parent
                            current_sub = child
                            sub_depth = 2
                        else:
                            flush_current_sub()
                            siblings = current_question.setdefault("sub_questions", [])
                            if kind == "lower" and sub_depth == 0:
                                label = self._next_sub_label(siblings, label)
                            current_sub = self._new_sub_question(label, text_after)
                            sub_depth = 1
                    elif line:
                        if current_sub is not None:
                            self._append_sub_content(current_sub, line)
                        else:
                            pts_m = _MARK_RE.search(line)
                            if pts_m:
                                current_question["points"] = int(pts_m.group(1))
                                line = _MARK_RE.sub("", line, count=1).strip()
                            if line:
                                prev = (current_question.get("text") or "").strip()
                                current_question["text"] = f"{prev}\n{line}".strip() if prev else line

            i += 1

        if current_question is not None:
            flush_all_subs()
            finalize_question(current_question)
            questions.append(current_question)

        for q in questions:
            q["text"] = q["text"].strip()
            subs = q.get("sub_questions") or []
            if subs:
                q["points"] = sum(self._question_points_total(s) for s in subs)

            if not q["gold_solution_steps"]:
                q["gold_solution_steps"] = [{
                    "step_number": 1,
                    "description": "Solution",
                    "expression": "",
                    "points": q["points"],
                    "required": True,
                }]
            else:
                total_step_points = sum(s["points"] for s in q["gold_solution_steps"])
                if total_step_points > q["points"]:
                    q["points"] = total_step_points
                elif total_step_points < q["points"] and total_step_points > 0:
                    pts_each = q["points"] // len(q["gold_solution_steps"])
                    remainder = q["points"] % len(q["gold_solution_steps"])
                    for si, step in enumerate(q["gold_solution_steps"]):
                        step["points"] = pts_each + (1 if si < remainder else 0)

            self._normalize_sub_gold_steps(q.get("sub_questions") or [])

        return questions

    def _split_math_lines(self, text: str) -> List[str]:
        """Split OCR math into step lines (handles arrays expanded to one line in the parser)."""
        if not text:
            return []
        if "\n" in text:
            return [ln.strip() for ln in text.split("\n") if ln.strip()]
        if text.count("=") >= 2:
            parts = re.split(r"\s+(?=\d*\s*x\s*=)|\s+(?=x\s*=\s*\d)", text)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                return parts
        return [text.strip()]

    def _is_math_step_line(self, line: str) -> bool:
        s = (line or "").strip()
        if not s:
            return False
        return looks_like_equation_line(s) or looks_like_math_ocr(s)

    def _promote_math_to_gold_steps(self, questions: List[Dict]) -> None:
        """Move OCR math lines into gold_solution_steps when no explicit rubric was parsed."""
        for q in questions:
            self._promote_one_question_gold(q, keep_text=False)
            self._promote_sub_tree(q.get("sub_questions") or [])

    def _promote_sub_tree(self, subs: List[Dict]) -> None:
        for sub in subs:
            self._promote_one_question_gold(sub, keep_text=True)
            self._promote_sub_tree(sub.get("sub_questions") or [])

    def _promote_one_question_gold(self, q: Dict, *, keep_text: bool) -> None:
        steps = q.get("gold_solution_steps") or []
        if any((s.get("expression") or "").strip() for s in steps):
            return
        raw = (q.get("text") or "").strip()
        if not raw:
            return
        norm = normalize_exam_ocr_text(raw).strip().strip("$").strip()
        lines = self._split_math_lines(norm)
        math_lines = [ln for ln in lines if self._is_math_step_line(ln)]
        prose_lines = [ln for ln in lines if not self._is_math_step_line(ln)]
        if math_lines:
            q["gold_solution_steps"] = [
                self._parse_step(ln, idx) for idx, ln in enumerate(math_lines, start=1)
            ]
            if not keep_text and not prose_lines:
                q["text"] = ""
            elif prose_lines and not keep_text:
                q["text"] = " ".join(prose_lines).strip()
        elif prose_lines:
            q["gold_solution_steps"] = [{
                "step_number": 1,
                "description": "Solution",
                "expression": " ".join(prose_lines).strip(),
                "points": q.get("points", 1),
                "required": True,
            }]
            if not keep_text:
                q["text"] = " ".join(prose_lines).strip()

    def _normalize_sub_gold_steps(self, subs: List[Dict]) -> None:
        for sub_q in subs:
            if not sub_q.get("gold_solution_steps"):
                sub_q["gold_solution_steps"] = [{
                    "step_number": 1,
                    "description": "Solution",
                    "expression": "",
                    "points": sub_q.get("points", 1),
                    "required": True,
                }]
            child_subs = sub_q.get("sub_questions") or []
            if child_subs:
                sub_q["points"] = sum(self._question_points_total(c) for c in child_subs)
                self._normalize_sub_gold_steps(child_subs)
