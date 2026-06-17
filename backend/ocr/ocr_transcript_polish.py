"""
Post-OCR cleanup and light algebraic normalization for display in the UI.

TrOCR / pipeline output is often noisy; this layer:
- strips obvious watermark / scanner tokens and long gibberish "words"
- picks the most math-like fragment from a long line of junk
- optionally parses a candidate expression with SymPy and returns standard form
  plus LaTeX suitable for KaTeX rendering

Does not replace the raw stored transcript — API adds parallel display fields.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html import unescape
from typing import Optional, Tuple

from ocr.math_postprocess import latex_to_readable

logger = logging.getLogger(__name__)

_JUNK_PAT = re.compile(
    r"(?i)\b(camscanner|adobe\s*scan|scanner\s*app|lens|watermark|qr\s*code)\b"
)
_CAPS_NOISE = re.compile(r"\b[A-Z]{4,}\b")


def _looks_like_html(s: str) -> bool:
    return bool(s and re.search(r"<\s*[a-zA-Z]", s))


def _strip_html(s: str) -> str:
    t = unescape(s)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</p>\s*<p>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _heuristic_clean(s: str) -> str:
    if not s:
        return ""
    t = _JUNK_PAT.sub(" ", s)
    t = _CAPS_NOISE.sub(" ", t)
    t = re.sub(r"[~@#§|\\]{1,}", " ", t)
    t = re.sub(r"[!?]{2,}", " ", t)
    t = re.sub(r"\b[A-Za-z]{8,}\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _fragment_score(p: str) -> float:
    if not p or len(p) < 2:
        return 0.0
    good = sum(
        1 for c in p if c.isdigit() or c in "+-*/=^.() " or c.lower() == "x"
    )
    letters = sum(1 for c in p if c.isalpha())
    bonus = 2.0 if any(c.isdigit() for c in p) else 0.0
    return good / max(1, len(p)) + bonus * 0.15 - 0.35 * (letters / max(1, len(p)))


def _best_math_fragment(s: str) -> str:
    parts = re.split(r"[\[\]|]+", s)
    best = ""
    best_sc = -1.0
    for p in parts:
        p = p.strip()
        if len(p) < 2:
            continue
        sc = _fragment_score(p)
        if sc > best_sc:
            best_sc = sc
            best = p
    return best if best_sc >= 0.25 else s


def _sympy_try(s: str) -> Tuple[Optional[str], Optional[str]]:
    if not s or len(s) > 220:
        return None, None
    try:
        from sympy import latex, simplify
        from sympy.parsing.sympy_parser import (
            implicit_multiplication_application,
            parse_expr,
            standard_transformations,
        )
    except ImportError:
        return None, None

    work = (
        s.replace("×", "*")
        .replace("·", "*")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
    )
    work = re.sub(r"[^0-9a-zA-Z+\-*/().^\s,]", " ", work)
    work = re.sub(r"\s+", " ", work).strip()
    if len(work) < 2:
        return None, None
    letters = sum(1 for c in work if c.isalpha())
    digits = sum(1 for c in work if c.isdigit())
    if not digits:
        if len(work) > 5:
            return None, None
        if not re.search(r"[\+\-\*/\=]", work):
            return None, None
    if letters > 8 and letters / max(1, len(work)) > 0.55:
        return None, None
    work2 = re.sub(r"\^(\d+)", r"**\1", work)
    work2 = re.sub(r"\^([a-zA-Z])", r"**\1", work2)
    work2 = re.sub(r"(\d)\(", r"\1*(", work2)
    work2 = re.sub(r"\)\(", r")*(", work2)

    trans = standard_transformations + (implicit_multiplication_application,)
    try:
        expr = parse_expr(work2, transformations=trans, evaluate=False)
        expr = simplify(expr)
        return str(expr), latex(expr)
    except Exception:
        return None, None


def _maybe_katex_from_latex(raw: str, max_len: int = 4000) -> Optional[str]:
    s = raw.strip().strip("$")
    if not s or len(s) > max_len:
        return None
    if sum(1 for c in s if ord(c) > 126) > len(s) * 0.25:
        return None
    return s


def _is_complex_latex(s: str) -> bool:
    return bool(re.search(r"\\begin\{|\\end\{|\\\\", s or ""))


@dataclass
class OcrDisplayPolish:
    display_plain: str
    math_latex: Optional[str]


def polish_ocr_for_submission_display(
    extracted_text: Optional[str],
    extracted_latex: Optional[str],
) -> OcrDisplayPolish:
    raw_text = (extracted_text or "").strip()
    raw_latex = (extracted_latex or "").strip()

    if not raw_text and not raw_latex:
        return OcrDisplayPolish("", None)

    math_latex: Optional[str] = None
    display = ""

    is_html = _looks_like_html(raw_text)
    plain_text = _strip_html(raw_text) if is_html else (raw_text or "")

    if plain_text and not is_html:
        cleaned = _heuristic_clean(plain_text)
        frag = _best_math_fragment(cleaned)
        p_t, l_t = _sympy_try(frag)
        if l_t:
            math_latex = l_t
        if p_t and "**" not in p_t:
            display = p_t
        elif len(frag) < len(plain_text) * 0.92 or _fragment_score(frag) >= 0.3:
            display = frag if frag.strip() else cleaned
        if not display:
            display = cleaned or plain_text

    if raw_latex:
        if _is_complex_latex(raw_latex):
            k = _maybe_katex_from_latex(raw_latex)
            if k:
                math_latex = k
                display = ""
        else:
            readable_l = latex_to_readable(raw_latex)
            p_l, l_l = _sympy_try(readable_l)
            if l_l:
                math_latex = math_latex or l_l
            if p_l and "**" not in p_l and (not display or len(p_l) < len(display)):
                display = p_l
            elif readable_l and not display:
                display = readable_l
            k = _maybe_katex_from_latex(raw_latex)
            if not math_latex and k and ("\\" in k or "^" in k or "_" in k or "frac" in k):
                math_latex = k

    if is_html and plain_text and not display:
        display = plain_text

    if not display:
        display = latex_to_readable(raw_latex) if raw_latex else ""

    return OcrDisplayPolish(display.strip(), math_latex)


def _extract_latex_from_html(html: str) -> Optional[str]:
    if not html:
        return None
    from html import unescape

    chunks = []
    for m in re.finditer(r'data-latex=(["\'])(.*?)\1', html, re.DOTALL):
        c = unescape(m.group(2)).strip()
        if c:
            chunks.append(c)
    if chunks:
        return "\n".join(chunks)
    return None


def _strip_step_noise(s: str) -> str:
    from html import unescape

    t = unescape(s or "")
    t = re.sub(r"<\s*br\s*/?>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"^\{\s*\d+\s*\}\s*", "", t.strip())
    t = re.sub(r"(^|\s)l\s*\(", r"\1\\left(", t, flags=re.I)
    t = re.sub(r"\)\s*\$\s*(?=[a-zA-Z(])", ") ", t)
    t = re.sub(
        r"\(\s*(\d+)\s*\$\s*(points?|pts?)\s*\$",
        r"(\1 \\text{ \2 })",
        t,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", t).strip()


def _normalize_spaced_latex(s: str) -> str:
    t = s
    t = t.replace("\\left", "\x00LEFT\x00")
    t = t.replace("\\right", "\x00RIGHT\x00")
    t = t.replace("\\frac", "\x00FRAC\x00")
    t = re.sub(r"\s*\^\s*\{\s*", "^{", t)
    t = re.sub(r"\s+\}", "}", t)
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    t = re.sub(r" +", " ", t).strip()
    t = t.replace("\x00LEFT\x00", "\\left")
    t = t.replace("\x00RIGHT\x00", "\\right")
    t = t.replace("\x00FRAC\x00", "\\frac")
    t = re.sub(r"\\left\s*\(\s*", r"\\left(", t)
    t = re.sub(r"\s*\\right\s*\)", r"\\right)", t)
    return t.strip()


def _latex_from_messy_step_text(t: str) -> Optional[str]:
    s = _strip_step_noise(t)
    if not s or s == "—":
        return None
    if re.search(r"\\(?:left|right|frac|sqrt|begin|sum|int)\b", s) or "$" in s:
        candidate = _normalize_spaced_latex(s.strip("$ "))
        return _maybe_katex_from_latex(candidate)
    m = re.search(r"\$([^$]+)\$", s)
    if m:
        return _maybe_katex_from_latex(_normalize_spaced_latex(m.group(1)))
    return None


def polish_step_snippet(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Returns (cleaner plain, optional LaTeX) for a step cell; plain None if no gain."""
    t = (text or "").strip()
    if not t:
        return None, None

    messy_latex = _latex_from_messy_step_text(t)
    if messy_latex:
        return None, messy_latex

    if _looks_like_html(t):
        plain = _strip_html(t)
        latex = _extract_latex_from_html(t)
        if latex and _is_complex_latex(latex):
            return None, _maybe_katex_from_latex(latex)
        p, l = _sympy_try(plain or latex or "")
        return (p or None, l or (_maybe_katex_from_latex(latex) if latex else None))
    if "\\" in t or "$" in t:
        m = re.search(r"\$([^$]+)\$", t)
        if m:
            k = _maybe_katex_from_latex(m.group(1))
            if k:
                return None, k
        k = _maybe_katex_from_latex(t.strip("$ "))
        if k:
            return None, k
    cleaned = _heuristic_clean(t)
    frag = _best_math_fragment(cleaned)
    p, l = _sympy_try(frag)
    if p:
        return p, l
    if frag != t and len(frag) < len(t) * 0.92:
        return frag.strip(), l
    return None, l
