"""
Convert OCR / plain exam text (with $...$ / $$...$$) into TipTap JSON for the exam editor.
Preserves tables and multiple-choice option line breaks from uploaded PDFs.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def ocr_text_to_rich_content(text: str) -> Dict[str, Any]:
    """Build a TipTap doc from OCR text that may contain inline or block LaTeX."""
    if not text or not str(text).strip():
        return {"type": "doc", "content": []}

    s = _normalize_exam_plain_text(str(text).strip())
    content: List[Dict[str, Any]] = []
    pos = 0

    while pos < len(s):
        block_start = s.find("$$", pos)
        if block_start == -1:
            tail = s[pos:].strip()
            if tail:
                content.extend(_blocks_from_plain(tail))
            break
        if block_start > pos:
            prefix = s[pos:block_start].strip()
            if prefix:
                content.extend(_blocks_from_plain(prefix))
        block_end = s.find("$$", block_start + 2)
        if block_end == -1:
            content.extend(_blocks_from_plain(s[block_start:].strip()))
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


def _blocks_from_plain(text: str) -> List[Dict[str, Any]]:
    """Split plain text into paragraphs and tables."""
    out: List[Dict[str, Any]] = []
    if not text.strip():
        return out

    table, rest_before, rest_after = _extract_inline_table(text)
    if table:
        if rest_before.strip():
            out.extend(_paragraphs_from_plain(rest_before))
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
