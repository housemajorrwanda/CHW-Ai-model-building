import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ExamParser:
    """
    Parses exam uploads following the official EXAM UPLOAD TEMPLATE:
    - EXAM TITLE: / Exam Title: for title
    - DESCRIPTION: / Description: for description
    - Question N: or Q N or N. for questions
    - [X points] or [X pts] for points
    - Sub-questions: (a), (b), (c) or (i), (ii) or a), b) or Part (a): within a question become nested sub_questions
    - Gold Solution:, Model Answer:, Solution:, Expected Answer:, Correct Answer:, Answer Key:
    - Step 1:, Step 2: or 1. step or = expression for solution steps
    - Sub-question solutions (a), (b), (c) in solution section are matched to corresponding sub-questions
    """
    def __init__(self):
        # Template: "Question 1:", "Q 1", "1. text", "Question 1 (10 marks)" - order matters for matching
        self.question_patterns = [
            r'(?:question|q)\s*[:\.]?\s*(\d+)',
            r'(?:question|q)\s+(\d+)',
            r'question\s*(\d+)\s*[\[\(]',
            r'^\s*(\d+)\s*[\.\)]\s*',
            r'^\s*(\d+)\s*:\s*',
            r'problem\s*(\d+)',
            r'question\s*(\d+)',
        ]
        
        # Template gold solution markers - longest first so "Expected Answer:" matches before "Answer:"
        self.gold_solution_markers = [
            'gold solution:',
            'model answer:',
            'expected answer:',
            'correct answer:',
            'answer key:',
            'solution:',
            'answer:',
            'answers:',
            'key:',
            'gold solution',
            'model answer',
            'worked solution',
        ]
        
        # Template: "Step 1:", "Step 2:", "1. step", "= expression"
        self.step_markers = [
            'step', 'solution step', 'working', 'final answer', 'answer ='
        ]
        
        # Template: "EXAM TITLE:" or "Exam Title:" (case-insensitive)
        self.title_markers = ['exam title:', 'title:', 'exam name:', 'name:']
        # Template: "DESCRIPTION:" or "Description:" (case-insensitive)
        self.description_markers = ['description:', 'instructions:', 'instruction:', 'directions:']

        # Sub-question markers: (a), (b), (c); (i), (ii); a), b); Part (a):, etc.
        self._sub_q_re = re.compile(
            r'^\s*(?:'
            r'\([a-z]\)\s*'               # (a) (b) (c)
            r'|\([ivx]+\)\s*'              # (i) (ii) (iii)
            r'|[a-z]\)\s+'                 # a)  b)  c)  (must have space after)
            r'|(?:part\s+)?\([a-z]\)\s*:' # Part (a): or (a):
            r')',
            re.IGNORECASE
        )

        # Page marker patterns:
        #   "-- 1 of 3 --"  (typed in PDF content)
        #   "<<PAGEBREAK>>"  (injected by _extract_text_from_pdf_bytes)
        self._page_marker_re = re.compile(
            r'^(?:-+\s*\d+\s+of\s+\d+\s*-+|<<PAGEBREAK>>)$',
            re.IGNORECASE
        )

    # ------------------------------------------------------------------
    # Text normalisation helpers
    # ------------------------------------------------------------------

    def _normalize_ocr_text(self, text: str) -> str:
        """Fix common OCR glitches and merge broken question headers."""
        if not text:
            return text
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'\n\s*\n', '\n\n', text)
        replacements = [
            (r'Quest1on', 'Question'),
            (r'quest1on', 'question'),
            (r'Q1estion', 'Question'),
            (r'Gold\s*S0lution', 'Gold Solution'),
            (r'gold\s*s0lution', 'gold solution'),
            (r'S0lution', 'Solution'),
        ]
        for old, new in replacements:
            text = re.sub(old, new, text, flags=re.IGNORECASE)
        return text

    def _ensure_question_line_breaks(self, text: str) -> str:
        """Ensure question markers start on a new line so the parser can detect them."""
        if not text or not text.strip():
            return text
        # Normalize "Question1" or "Question 1" (ensure space before number)
        text = re.sub(r'(?i)(Question|Q)\s*(\d+)', r'\1 \2', text)
        # Insert newline before "Question N" or "Q N" / "Q: N" when not already at line start
        text = re.sub(r'(?<!\n)(\s*)((?:Question|Q)\s*[:\.]?\s*\d+)', r'\n\2', text, flags=re.IGNORECASE)
        # Insert newline before standalone "N." or "N)" that start a question
        text = re.sub(r'(\.|\?)\s+(\d+)\s*[\.\)]\s+', r'\1\n\2.\ ', text)
        # Insert newline before solution markers
        text = re.sub(
            r'(?<!\n)(\s*)((?:Gold\s+Solution|Model\s+Answer|Answer\s+Key|Expected\s+Answer|Correct\s+Answer|Solution:)[\s:]*)',
            r'\n\2',
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def parse_exam(self, text: str) -> Dict:
        text = self._normalize_ocr_text(text)
        text = self._ensure_question_line_breaks(text)
        raw_lines = [line.strip() for line in text.split('\n') if line.strip()]
        lines = []
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            if i + 1 < len(raw_lines) and re.match(r'^(?:question|q)\s*$', line, re.IGNORECASE):
                next_line = raw_lines[i + 1]
                if re.match(r'^\d+\s*[\.\):]', next_line):
                    line = line + ' ' + next_line
                    i += 1
            lines.append(line)
            i += 1

        title = self._extract_title(lines)
        description = self._extract_description(lines)
        questions = self._extract_questions(lines)

        total_points = sum(q['points'] for q in questions)

        return {
            'title': title,
            'description': description,
            'questions': questions,
            'total_points': total_points
        }

    # ------------------------------------------------------------------
    # Title / description extraction
    # ------------------------------------------------------------------

    def _extract_title(self, lines: List[str]) -> str:
        for line in lines[:20]:
            lower = line.lower().strip()
            for marker in self.title_markers:
                if marker in lower:
                    idx = lower.find(marker)
                    after_marker = line[idx + len(marker):].strip()
                    if after_marker.startswith(':'):
                        after_marker = after_marker[1:].strip()
                    elif ':' in after_marker:
                        after_marker = after_marker.split(':', 1)[-1].strip()
                    if after_marker and len(after_marker) > 2:
                        return after_marker
            if any(word in lower for word in ['exam', 'test', 'quiz', 'assessment']) and not self._is_question_header(line) and len(line.strip()) > 3:
                return line.strip()
        for line in lines[:10]:
            s = line.strip()
            if s and s != '=' and len(s) > 1 and not re.match(r'^\d+[\.\)]\s*$', s) and not re.match(r'^(?:question|q)\s*\d+', s, re.I):
                return s
        return lines[0].strip() if lines else "Imported Exam"

    def _extract_description(self, lines: List[str]) -> str:
        desc_lines = []
        in_desc = False

        for line in lines:
            lower = line.lower().strip()
            for marker in self.description_markers:
                if marker in lower:
                    in_desc = True
                    after = line.split(':', 1)[-1].strip() if ':' in line else ''
                    if after:
                        desc_lines.append(after)
                    break
            else:
                if in_desc:
                    if self._is_question_header(line) or any(m in lower for m in self.gold_solution_markers):
                        break
                    desc_lines.append(line)

        result = ' '.join(desc_lines).strip()
        if result:
            return result
        intro = []
        for line in lines[:30]:
            if self._is_question_header(line):
                break
            s = line.strip()
            if not s or s == '=' or len(s) < 2:
                continue
            if re.match(r'^(?:exam\s+)?title\s*:', s, re.I) or re.match(r'^\d+[\.\)]\s*$', s):
                continue
            intro.append(s)
        if intro and len(' '.join(intro)) < 600:
            return ' '.join(intro).strip()
        return "Imported exam"

    # ------------------------------------------------------------------
    # Question-header detection
    # ------------------------------------------------------------------

    def _is_question_header(self, line: str) -> bool:
        lower = line.lower()
        for pattern in self.question_patterns:
            if re.search(pattern, lower, re.IGNORECASE):
                return True
        return False

    def _find_question_number(self, line: str) -> Optional[int]:
        for pattern in self.question_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    # ------------------------------------------------------------------
    # Sub-question helpers
    # ------------------------------------------------------------------

    def _is_sub_question_line(self, line: str) -> bool:
        """True if line starts with (a), (b), a) , b) , etc."""
        return bool(self._sub_q_re.match(line.strip()))

    def _strip_sub_question_marker(self, line: str) -> str:
        """Return the line content after the (a), (b), etc. marker."""
        return self._sub_q_re.sub('', line.strip(), count=1).strip()

    def _extract_sub_letter(self, line: str) -> str:
        """Extract the letter from a sub-question line: 'a) text' -> 'a'."""
        m = re.match(r'^\s*\(?([a-z])\)?\s*', line.strip(), re.IGNORECASE)
        if m:
            return m.group(1).lower()
        return ''

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    def _is_step_line(self, line: str) -> bool:
        lower = line.lower()
        return (
            any(marker in lower for marker in self.step_markers)
            or bool(re.match(r'^\s*\d+[\.\)]\s*', line))
            or line.startswith('=')
        )

    def _parse_step(self, line: str, step_number: int) -> Dict:
        clean_line = re.sub(r'^(?:step\s*\d*[:\.]?\s*)', '', line, flags=re.IGNORECASE).strip()
        clean_line = re.sub(r'^\s*\d+[\.\)]\s*', '', clean_line).strip()

        points = 1
        points_match = re.search(r'[\[\(](\d+)\s*(?:points?|pts?|marks?)[\]\)]', clean_line, re.IGNORECASE)
        if points_match:
            points = int(points_match.group(1))
            clean_line = re.sub(r'[\[\(]\d+\s*(?:points?|pts?|marks?)[\]\)]', '', clean_line, flags=re.IGNORECASE).strip()

        return {
            'step_number': step_number,
            'description': f'Step {step_number}',
            'expression': clean_line,
            'points': points,
            'required': step_number <= 3
        }

    # ------------------------------------------------------------------
    # Core question extraction
    # ------------------------------------------------------------------

    def _extract_questions(self, lines: List[str]) -> List[Dict]:
        questions: List[Dict] = []
        current_question: Optional[Dict] = None
        current_section = 'text'
        current_steps: List[Dict] = []

        # Sub-question text tracking
        current_sub_text: List[str] = []

        # Solution sub-part tracking (for a), b), c) format gold solutions)
        current_sol_letter: str = ''
        current_sol_subs: Dict[str, List[str]] = {}  # letter -> text parts

        # Page tracking
        current_page = 0

        def _extract_points_from_text(text: str):
            """Returns (cleaned_text, points)."""
            pm = re.search(r'[\[\(](\d+)\s*(?:points?|pts?|marks?)[\]\)]', text, re.IGNORECASE)
            if pm:
                pts = int(pm.group(1))
                cleaned = re.sub(r'[\[\(]\d+\s*(?:points?|pts?|marks?)[\]\)]', '', text, flags=re.IGNORECASE).strip()
                return cleaned, pts
            return text, 1

        def flush_current_sub():
            nonlocal current_sub_text
            if current_sub_text and current_question is not None:
                raw = ' '.join(current_sub_text).strip()
                if raw:
                    text_clean, pts = _extract_points_from_text(raw)
                    if 'sub_questions' not in current_question:
                        current_question['sub_questions'] = []
                    current_question['sub_questions'].append({
                        'text': text_clean,
                        'points': pts,
                        'gold_solution_steps': []
                    })
            current_sub_text = []

        def finalize_question(q: Dict):
            """Attach collected steps / solution sub-parts to the question before appending."""
            nonlocal current_sol_subs, current_sol_letter

            if current_sol_subs and q.get('sub_questions'):
                # Match solution sub-parts (a, b, c, …) to question sub-questions
                for i, sub_q in enumerate(q['sub_questions']):
                    letter = chr(ord('a') + i)
                    if letter in current_sol_subs:
                        sol_raw = ' '.join(current_sol_subs[letter]).strip()
                        sol_text, sol_pts = _extract_points_from_text(sol_raw)
                        sub_q['gold_solution_steps'] = [{
                            'step_number': 1,
                            'description': 'Solution',
                            'expression': sol_text,
                            'points': sol_pts,
                            'required': True,
                        }]
                # Also build parent gold steps as a summary
                if not q.get('gold_solution_steps'):
                    q['gold_solution_steps'] = []
                    for i, sub_q in enumerate(q['sub_questions']):
                        letter = chr(ord('a') + i)
                        if letter in current_sol_subs:
                            sol_raw = ' '.join(current_sol_subs[letter]).strip()
                            sol_text, sol_pts = _extract_points_from_text(sol_raw)
                            q['gold_solution_steps'].append({
                                'step_number': i + 1,
                                'description': f'Part ({letter})',
                                'expression': sol_text,
                                'points': sol_pts,
                                'required': True,
                            })
            elif current_steps:
                q['gold_solution_steps'] = current_steps

            current_sol_subs = {}
            current_sol_letter = ''

        i = 0
        while i < len(lines):
            line = lines[i]
            lower = line.lower()

            # --- Skip page markers like "-- 1 of 3 --" and advance page counter ---
            if self._page_marker_re.match(line):
                current_page += 1
                i += 1
                continue

            # --- New question ---
            question_match = self._find_question_number(line)
            if question_match:
                if current_question is not None:
                    flush_current_sub()
                    finalize_question(current_question)
                    questions.append(current_question)

                current_question = {
                    'number': question_match,
                    'text': '',
                    'points': 1,
                    'gold_solution_steps': [],
                    'sub_questions': [],
                    'page_num': current_page,
                }
                current_section = 'text'
                current_steps = []
                current_sub_text = []
                current_sol_letter = ''
                current_sol_subs = {}

                text_part = re.sub(r'(?:question|q)\s*[:\.]?\s*\d+', '', line, flags=re.IGNORECASE).strip()
                text_part = re.sub(r'^\s*\d+\s*[\.\)]\s*', '', text_part).strip()
                text_part = re.sub(r'^[:\s]+', '', text_part).strip()

                points_match = re.search(r'[\[\(](\d+)\s*(?:points?|pts?|marks?)[\]\)]', text_part, re.IGNORECASE)
                if points_match:
                    current_question['points'] = int(points_match.group(1))
                    text_part = re.sub(r'[\[\(]\d+\s*(?:points?|pts?|marks?)[\]\)]', '', text_part, flags=re.IGNORECASE).strip()

                if text_part:
                    current_question['text'] = text_part

            elif current_question is not None:

                # --- Gold solution marker ---
                if any(marker in lower for marker in self.gold_solution_markers):
                    flush_current_sub()
                    current_section = 'solution'
                    current_sol_letter = ''
                    # Anything after the marker on the same line
                    gold_text = re.split('|'.join(re.escape(m) for m in self.gold_solution_markers), lower)[0]
                    gold_text = re.split('|'.join(re.escape(m) for m in self.gold_solution_markers), line, flags=re.IGNORECASE)[-1].strip()
                    if gold_text and not self._is_sub_question_line(gold_text):
                        step = self._parse_step(gold_text, len(current_steps) + 1)
                        current_steps.append(step)

                # --- Solution section ---
                elif current_section == 'solution':
                    if self._is_sub_question_line(line):
                        # Sub-part of gold solution: a)  Carbon dioxide gas. [2 points]
                        letter = self._extract_sub_letter(line)
                        text_after = self._strip_sub_question_marker(line)
                        current_sol_letter = letter
                        if letter not in current_sol_subs:
                            current_sol_subs[letter] = []
                        if text_after:
                            current_sol_subs[letter].append(text_after)
                    elif current_sol_letter:
                        # Continuation of the current solution sub-part
                        if line and not self._is_question_header(line):
                            current_sol_subs[current_sol_letter].append(line)
                    else:
                        # Regular step format (Step 1:, Step 2:, =, numbered)
                        is_new_step = (
                            self._is_step_line(line)
                            or bool(re.match(r'^(?:final\s+)?answer\s*[:=]', lower))
                            or (line.strip().startswith('=') and len(line.strip()) > 1)
                            or bool(re.match(r'^\s*\d+[\.\)]\s*\S', line))
                        )
                        if is_new_step:
                            step = self._parse_step(line, len(current_steps) + 1)
                            current_steps.append(step)
                        elif line and not self._is_question_header(line):
                            if current_steps:
                                current_steps[-1]['expression'] += ' ' + line
                            else:
                                current_steps.append(self._parse_step(line, 1))

                # --- Question text section ---
                elif current_section == 'text':
                    if self._is_sub_question_line(line):
                        flush_current_sub()
                        part_text = self._strip_sub_question_marker(line)
                        current_sub_text = [part_text] if part_text else []
                    elif line:
                        if current_sub_text:
                            current_sub_text.append(line)
                        else:
                            pts_m = re.search(r'[\[\(](\d+)\s*(?:points?|pts?|marks?)[\]\)]', lower)
                            if pts_m:
                                current_question['points'] = int(pts_m.group(1))
                                line = re.sub(r'[\[\(]\d+\s*(?:points?|pts?|marks?)[\]\)]', '', line, flags=re.IGNORECASE).strip()
                            if line:
                                current_question['text'] += ' ' + line

            i += 1

        # Finalize last question
        if current_question is not None:
            flush_current_sub()
            finalize_question(current_question)
            questions.append(current_question)

        # Renumber 1, 2, 3, … and fill in default gold steps
        for idx, q in enumerate(questions, start=1):
            q['number'] = idx
            q['text'] = q['text'].strip()

            if not q['gold_solution_steps']:
                q['gold_solution_steps'] = [{
                    'step_number': 1,
                    'description': 'Solution',
                    'expression': '',
                    'points': q['points'],
                    'required': True
                }]
            else:
                total_step_points = sum(s['points'] for s in q['gold_solution_steps'])
                if total_step_points > q['points']:
                    q['points'] = total_step_points
                elif total_step_points < q['points'] and total_step_points > 0:
                    pts_each = q['points'] // len(q['gold_solution_steps'])
                    remainder = q['points'] % len(q['gold_solution_steps'])
                    for si, step in enumerate(q['gold_solution_steps']):
                        step['points'] = pts_each + (1 if si < remainder else 0)

            # Same normalisation for sub-question gold steps
            for sub_q in q.get('sub_questions', []):
                if not sub_q.get('gold_solution_steps'):
                    sub_q['gold_solution_steps'] = [{
                        'step_number': 1,
                        'description': 'Solution',
                        'expression': '',
                        'points': sub_q['points'],
                        'required': True,
                    }]

        return questions
