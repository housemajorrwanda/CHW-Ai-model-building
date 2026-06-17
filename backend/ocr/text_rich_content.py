"""
Convert OCR / plain exam text (with $...$ / $$...$$) into TipTap JSON for the exam editor.
Preserves tables and multiple-choice option line breaks from uploaded PDFs.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .math_postprocess import latex_to_readable


def looks_like_equation_line(line: str) -> bool:
    """True when a line is mostly a math equation (used for titles and gold-step detection)."""
    return _looks_like_equation_line(line)


def looks_like_math_ocr(s: str) -> bool:
    """True when OCR output is LaTeX / math notation rather than plain prose."""
    if not s or not isinstance(s, str):
        return False
    if "$$" in s or re.search(r"(?<!\$)\$(?!\$)[^$\n]+?\$(?!\$)", s):
        return True
    lowered = s.lower()
    if any(tok in lowered for tok in ("\\begin{", "\\frac", "\\prime", "\\left", "\\right")):
        return True
    if s.count("\\") >= 2 and any(c in s for c in "{}^"):
        return True
    first = next((ln.strip() for ln in s.splitlines() if ln.strip()), s.strip())
    if _looks_like_equation_line(first):
        return True
    return False


def outline_preview_from_text(text: str, max_len: int = 52) -> str:
    """Human-readable sidebar label from OCR/LaTeX question text."""
    s = (text or "").strip()
    if not s:
        return ""
    if looks_like_math_ocr(s):
        s = normalize_exam_ocr_text(s)
        first = next((ln.strip() for ln in s.splitlines() if ln.strip()), s)
        s = first
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def normalize_exam_ocr_text(text: str) -> str:
    """
    Prepare handwriting/math OCR for exam parsing and the TipTap editor.

    Math OCR (Mathpix, TrOCR-math) often returns ``\\begin{array}{l} a \\\\ b``
    without question headings — expand those to plain lines the parser can use.
    """
    if not text or not str(text).strip():
        return text or ""

    s = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    s = _normalize_latex_command_spacing(s)

    # Drop stray opening $$ on its own line
    s = re.sub(r"^\$\$\s*\n?", "", s)
    s = re.sub(r"\n?\s*\$\$\s*$", "", s)

    # Close unclosed block delimiters so rich-content conversion works
    if s.count("$$") % 2 == 1:
        s = s.rstrip() + "\n$$"

    s = _expand_latex_array_blocks(s)
    s = _expand_latex_tabular_blocks(s)
    s = _wrap_bare_latex_environments(s)
    s = re.sub(r"\$\$\$\$+", "$$", s)

    return s


def _normalize_latex_command_spacing(text: str) -> str:
    """Collapse OCR spacing in LaTeX commands: ``\\begin { array } { l }`` → ``\\begin{array}{l}``."""
    text = re.sub(
        r"\\begin\s*\{\s*array\s*\}\s*\{\s*([^}]*)\s*\}",
        r"\\begin{array}{\1}",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\\end\s*\{\s*array\s*\}", r"\\end{array}", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\\begin\s*\{\s*tabular\s*\}\s*\{\s*([^}]*)\s*\}",
        r"\\begin{tabular}{\1}",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\\end\s*\{\s*tabular\s*\}", r"\\end{tabular}", text, flags=re.IGNORECASE)
    for cmd in ("left", "right", "frac", "sqrt"):
        text = re.sub(rf"\\{cmd}\s*\(", rf"\\{cmd}(", text)
        text = re.sub(rf"\\{cmd}\s*\)", rf"\\{cmd})", text)
        text = re.sub(rf"\\{cmd}\s*\{{", rf"\\{cmd}{{", text)
    return text


def _expand_latex_array_blocks(text: str) -> str:
    """Convert \\begin{array}...\\end{array} (or truncated) into readable lines."""

    def _rows_to_lines(body: str) -> List[str]:
        rows = [r.strip() for r in re.split(r"\\\\", body) if r.strip()]
        return rows

    def _full_repl(m: re.Match) -> str:
        lines = _rows_to_lines(m.group(1) or "")
        return "\n".join(lines) if lines else m.group(0)

    text = re.sub(
        r"\\begin\{array\}\{[^}]*\}(.*?)\\end\{array\}",
        _full_repl,
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Truncated OCR: \begin{array}{l} ... with no \end{array}
    m = re.search(r"\\begin\{array\}\{[^}]*\}(.*)", text, re.DOTALL | re.IGNORECASE)
    if m and "\\end{array}" not in (m.group(1) or ""):
        prefix = text[: m.start()].strip()
        lines = _rows_to_lines(m.group(1) or "")
        tail = "\n".join(lines) if lines else latex_to_readable(m.group(0))
        return f"{prefix}\n{tail}".strip() if prefix else (tail or text)

    return text


def _expand_latex_tabular_blocks(text: str) -> str:
    """Expand ``\\begin{tabular}...\\end{tabular}`` into plain step lines for the parser."""

    def _repl(m: re.Match) -> str:
        body = m.group(1) or ""
        rows = [r.strip() for r in re.split(r"\\\\", body) if r.strip()]
        cleaned: List[str] = []
        for row in rows:
            row = re.sub(r"\s*&\s*$", "", row).strip()
            if row:
                cleaned.append(row)
        return "\n".join(cleaned) if cleaned else m.group(0)

    text = re.sub(
        r"\\begin\s*\{\s*tabular\s*\}\s*\{[^}]*\}(.*?)\\end\s*\{\s*tabular\s*\}",
        _repl,
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r"\\begin\s*\{\s*tabular\s*\}\s*\{[^}]*\}",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\\end\s*\{\s*tabular\s*\}", "", text, flags=re.IGNORECASE)
    return text


def _wrap_bare_latex_environments(text: str) -> str:
    """Wrap bare \\begin{...} blocks in $$ for the rich-content converter."""
    envs = ("array", "align", "aligned", "cases", "matrix", "pmatrix", "bmatrix")
    for env in envs:
        pat = rf"(?<!\$)(\\begin\{{{env}\}}.*?\\end\{{{env}\}})(?!\$)"
        text = re.sub(pat, r"$$\1$$", text, flags=re.DOTALL | re.IGNORECASE)
    return text


def ocr_text_to_rich_content(text: str) -> Dict[str, Any]:
    """Build a TipTap doc from OCR text that may contain inline or block LaTeX."""
    if not text or not str(text).strip():
        return {"type": "doc", "content": []}

    s = normalize_exam_ocr_text(str(text).strip())
    s = _normalize_exam_plain_text(s)
    content: List[Dict[str, Any]] = []
    pos = 0

    while pos < len(s):
        block_start = s.find("$$", pos)
        if block_start == -1:
            tail = s[pos:].strip()
            if tail:
                content.extend(_blocks_from_plain_or_latex(tail))
            break
        if block_start > pos:
            prefix = s[pos:block_start].strip()
            if prefix:
                content.extend(_blocks_from_plain_or_latex(prefix))
        block_end = s.find("$$", block_start + 2)
        if block_end == -1:
            latex = s[block_start + 2 :].strip()
            if latex:
                content.append({"type": "blockMath", "attrs": {"latex": latex}})
            break
        latex = s[block_start + 2 : block_end].strip()
        if latex:
            content.append({"type": "blockMath", "attrs": {"latex": latex}})
        pos = block_end + 2

    if not content:
        content.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": s[:10000]}],
            }
        )
    return {"type": "doc", "content": content}


def _blocks_from_plain_or_latex(text: str) -> List[Dict[str, Any]]:
    """Plain paragraphs, or block math when the segment is bare LaTeX."""
    t = text.strip()
    if looks_like_math_ocr(t):
        latex = t.strip("$").strip()
        if latex:
            return [{"type": "blockMath", "attrs": {"latex": latex}}]
    return _blocks_from_plain(t)


def _normalize_exam_plain_text(text: str) -> str:
    """Improve readability of PDF-extracted exam text."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Put MC options on their own lines: "… is: A. foo B. bar" -> separate lines
    text = re.sub(r"(?<=[:\?])\s+([A-D])\.\s+", r"\n\1. ", text)
    text = re.sub(r"(?<=\))\s+([A-D])\.\s+", r"\n\1. ", text)
    text = re.sub(r"(?<=[a-z])\s+([A-D])\.\s+", r"\n\1. ", text)
    text = re.sub(r"\s+([A-D])\.\s+(?=[A-Za-z0-9])", r"\n\1. ", text)
    # Roman sub-parts on new lines when inline
    text = re.sub(r"\s+((?:i{1,3}|iv|vi{0,3}|ix|x)\.)\s+", r"\n\1 ", text, flags=re.I)
    return text


def _looks_like_equation_line(line: str) -> bool:
    s = (line or "").strip()
    if not s or len(s) < 3:
        return False
    if "=" not in s and not re.search(r"\\frac|\\sqrt|[\^]", s):
        return False
    return bool(re.search(r"[0-9a-zA-Z]", s))


def _blocks_from_plain(text: str) -> List[Dict[str, Any]]:
    """Split plain text into paragraphs, tables, or equation block math."""
    out: List[Dict[str, Any]] = []
    if not text.strip():
        return out

    table, rest_before, rest_after = _extract_inline_table(text)
    if table:
        if rest_before.strip():
            out.extend(_blocks_from_plain(rest_before))
        out.append(table)
        if rest_after.strip():
            out.extend(_blocks_from_plain(rest_after))
        return out

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        row_table = _table_from_spaced_line(line)
        if row_table:
            out.append(row_table)
            continue
        if _looks_like_equation_line(line):
            out.append({"type": "blockMath", "attrs": {"latex": line}})
            continue
        nodes = _inline_nodes_from_line(line)
        if nodes:
            out.append({"type": "paragraph", "content": nodes})
    return out


def _extract_inline_table(text: str) -> Tuple[Optional[Dict[str, Any]], str, str]:
    """
    Detect mass-spec style inline tables:
    '... below: m/z 24 25 26 Relative intensity 1 0.127 0.139'
    """
    m = re.search(
        r"(m/z)\s+([\d.\s]+?)\s+(Relative intensity)\s+([\d.\s]+)",
        text,
        re.I,
    )
    if not m:
        return None, text, ""

    cols = [c for c in re.split(r"\s{2,}|\s+", m.group(2).strip()) if c]
    vals = [c for c in re.split(r"\s{2,}|\s+", m.group(4).strip()) if c]
    if len(cols) < 2 or len(vals) < 2:
        return None, text, ""

    header_row = ["", m.group(1)] + cols
    data_row = ["", m.group(3)] + vals
    while len(data_row) < len(header_row):
        data_row.append("")
    table = _make_table([header_row, data_row[: len(header_row)]])

    before = text[: m.start()].strip()
    after = text[m.end() :].strip()
    return table, before, after


def _table_from_spaced_line(line: str) -> Optional[Dict[str, Any]]:
    """Detect a two-row table split across consecutive spaced columns in one line."""
    if "m/z" not in line.lower():
        return None
    return None


def _make_table(rows: List[List[str]]) -> Dict[str, Any]:
    table_rows = []
    for r_idx, row in enumerate(rows):
        cells = []
        for cell in row:
            cell_type = "tableHeader" if r_idx == 0 else "tableCell"
            cells.append(
                {
                    "type": cell_type,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": cell or " "}],
                        }
                    ],
                }
            )
        table_rows.append({"type": "tableRow", "content": cells})
    return {"type": "table", "content": table_rows}


def _paragraphs_from_plain(text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        nodes = _inline_nodes_from_line(line)
        if nodes:
            out.append({"type": "paragraph", "content": nodes})
    return out


def _inline_nodes_from_line(line: str) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    pos = 0
    while pos < len(line):
        match = re.search(r"\$([^$\n]+?)\$", line[pos:])
        if not match:
            rest = line[pos:]
            if rest:
                nodes.append({"type": "text", "text": rest})
            break
        start = pos + match.start()
        if start > pos:
            nodes.append({"type": "text", "text": line[pos:start]})
        latex = match.group(1).strip()
        if latex:
            nodes.append({"type": "inlineMath", "attrs": {"latex": latex}})
        pos = start + len(match.group(0))
    return nodes
