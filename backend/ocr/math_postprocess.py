"""
Math notation post-processing for handwriting OCR.

TrOCR is trained on prose handwriting (IAM dataset) and routinely misses the
small marks that change Boolean algebra meaning:
- primes (`A'` → reads as `A`)
- overlines (`Ā` → reads as `A`)

This module rescues those marks directly from the original line image, then
edits the OCR text in-place. It uses only OpenCV / NumPy, so it works
offline without any extra ML deps.

It also accepts an optional LaTeX string from a separate math model
(`pix2tex`) and converts it to readable Unicode that lines up with the rest
of the recognised text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# ── LaTeX → readable Unicode ─────────────────────────────────────────────────


_LATEX_SIMPLE_SUBS = (
    (r"\\overline\{([A-Za-z])\}", lambda m: f"{m.group(1)}\u0305"),  # A → A̅
    (r"\\bar\{([A-Za-z])\}", lambda m: f"{m.group(1)}\u0305"),
    (r"\\widetilde\{([A-Za-z])\}", lambda m: f"{m.group(1)}\u0303"),
    (r"\\tilde\{([A-Za-z])\}", lambda m: f"{m.group(1)}\u0303"),
    (r"\\cdot", " · "),
    (r"\\times", " × "),
    (r"\\oplus", " ⊕ "),
    (r"\\wedge", " ∧ "),
    (r"\\land", " ∧ "),
    (r"\\vee", " ∨ "),
    (r"\\lor", " ∨ "),
    (r"\\neg", " ¬ "),
    (r"\\lnot", " ¬ "),
    (r"\\sum", " Σ "),
    (r"\\prod", " Π "),
    (r"\\leq", " ≤ "),
    (r"\\geq", " ≥ "),
    (r"\\neq", " ≠ "),
    (r"\\rightarrow", " → "),
    (r"\\to", " → "),
    (r"\\Rightarrow", " ⇒ "),
    (r"\\Leftarrow", " ⇐ "),
    (r"\\equiv", " ≡ "),
    (r"\\pm", " ± "),
    (r"\\infty", "∞"),
    (r"\\alpha", "α"),
    (r"\\beta", "β"),
    (r"\\gamma", "γ"),
    (r"\\delta", "δ"),
    (r"\\theta", "θ"),
    (r"\\pi", "π"),
    (r"\\sigma", "σ"),
    (r"\\phi", "φ"),
    (r"\\omega", "ω"),
)


def latex_to_readable(latex: str) -> str:
    """
    Convert a LaTeX expression (e.g. from pix2tex) into a readable string we
    can drop alongside TrOCR text. Best-effort — keeps unknown tokens as-is.
    """
    if not latex:
        return ""
    s = latex.strip()
    s = s.replace("$$", "").replace("$", "")
    s = re.sub(r"\^\{?\\prime\}?", "'", s)  # A^{\prime} → A'
    s = re.sub(r"([A-Za-z0-9])'", r"\1'", s)
    for pat, rep in _LATEX_SIMPLE_SUBS:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", s)
    s = re.sub(r"\\(left|right)", "", s)
    s = re.sub(r"\\([A-Za-z]+)", "", s)  # drop any remaining tex commands
    s = re.sub(r"\{|\}", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ── Image-level prime / overline detection ──────────────────────────────────


@dataclass
class _CharMark:
    """A small ink blob on a text line; used to find primes and overlines."""

    x: int  # left
    y: int  # top
    w: int
    h: int
    base_top: int  # y of the dominant ink band
    base_bottom: int


def _binarise_line(crop: Image.Image) -> np.ndarray:
    arr = np.array(crop.convert("L"))
    blur = cv2.GaussianBlur(arr, (3, 3), 0)
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return bw


def _dominant_text_band(bw: np.ndarray) -> Tuple[int, int]:
    """
    Returns (band_top, band_bottom): the central horizontal stripe of the line
    that holds the bulk of ink (i.e. the actual letters, not the overline
    bars above or descenders below).
    """
    rows = (bw > 0).sum(axis=1)
    if rows.sum() == 0:
        return 0, bw.shape[0]
    # Keep rows above 25% of peak intensity.
    peak = rows.max()
    threshold = max(1, int(peak * 0.25))
    band = np.where(rows >= threshold)[0]
    if band.size == 0:
        return 0, bw.shape[0]
    return int(band[0]), int(band[-1])


def _find_marks(bw: np.ndarray) -> List[_CharMark]:
    band_top, band_bottom = _dominant_text_band(bw)
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: List[_CharMark] = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        out.append(_CharMark(x=x, y=y, w=w, h=h, base_top=band_top, base_bottom=band_bottom))
    return out


def _detect_overline_strips(bw: np.ndarray) -> List[Tuple[int, int]]:
    """
    Detect horizontal-bar strokes above the main text band — overlines.
    Returns list of (x_start, x_end) ranges for each detected overline.
    """
    band_top, _ = _dominant_text_band(bw)
    if band_top <= 4:
        return []
    above = bw[: max(1, band_top - 1), :]
    if above.size == 0:
        return []
    # Horizontal closing emphasises continuous bars
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(5, above.shape[1] // 80), 1))
    closed = cv2.morphologyEx(above, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    strips: List[Tuple[int, int]] = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        # Real overlines: wide-and-short stroke
        if w < max(12, above.shape[1] // 60) or h > max(8, above.shape[0]):
            continue
        if w / max(1, h) < 3:  # bars are wide
            continue
        strips.append((x, x + w))
    strips.sort()
    return strips


def _detect_prime_marks(bw: np.ndarray) -> List[int]:
    """
    Detect short upward strokes attached to the top-right of letters — primes.
    Returns x-coordinates of detected prime marks (top-right anchors).

    Conservative: rejects letter ascenders (h, k, b, d, l, t, i-dots) by
    requiring the stroke to sit **above** the dominant ink band, not inside it,
    and to be clearly detached from neighbouring contours.
    """
    band_top, band_bottom = _dominant_text_band(bw)
    if band_top is None:
        return []
    band_height = max(1, band_bottom - band_top)
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    marks: List[int] = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        # Reject anything that overlaps the main text band — that's a letter,
        # not a prime. Prime strokes float above the band.
        if y + h > band_top + 2:
            continue
        # Prime strokes are small, but not micro-noise.
        if w < 2 or h < max(4, int(band_height * 0.25)):
            continue
        if w > band_height * 0.35 or h > band_height * 0.9:
            continue
        # Definitely taller than wide.
        if h / max(1, w) < 1.8:
            continue
        # Must sit well above the band — no overlap.
        if y > band_top - 2:
            continue
        marks.append(x)
    marks.sort()
    return marks


def _find_letters(text: str) -> List[Tuple[int, str]]:
    """All letter positions (and the letter) in the OCR text."""
    return [(i, ch) for i, ch in enumerate(text) if ch.isalpha()]


def annotate_line_with_marks(crop: Image.Image, text: str) -> str:
    """
    Detect primes and overlines in `crop` and edit `text` so the marks are
    represented. Best-effort and conservative — if detection is uncertain we
    leave `text` alone rather than introduce spurious primes.
    """
    if not text:
        return text
    try:
        bw = _binarise_line(crop)
    except Exception:
        return text

    line_width = bw.shape[1]
    overline_strips = _detect_overline_strips(bw)
    prime_anchors = _detect_prime_marks(bw)

    if not overline_strips and not prime_anchors:
        return text

    letter_positions = _find_letters(text)
    if not letter_positions:
        return text

    # Hard cap so a noisy crop can't sprinkle primes on every letter.
    # Two primes per ~6 letters is plenty for Boolean-algebra answers
    # ("A'B + AB' = …"). Anything beyond that is almost certainly noise.
    max_primes = max(1, min(4, len(letter_positions) // 3 + 1))
    prime_anchors = prime_anchors[:max_primes]
    max_overlines = max(1, min(4, len(letter_positions) // 3 + 1))
    overline_strips = overline_strips[:max_overlines]

    # Map each letter to an approximate x-pixel in the crop.
    n = len(letter_positions)
    x_per_letter = line_width / float(max(1, n))

    chars: List[str] = list(text)

    # Apply overlines: combining-overline (U+0305) is placed AFTER the base char.
    # Only annotate one letter per overline strip to avoid runaway diacritics.
    used_overline_letters: set[int] = set()
    for (sx, ex) in overline_strips:
        center = (sx + ex) / 2.0
        best_idx = None
        best_dist = 1e9
        for li, (text_idx, ch) in enumerate(letter_positions):
            if li in used_overline_letters:
                continue
            approx_x = (li + 0.5) * x_per_letter
            d = abs(approx_x - center)
            if d < best_dist:
                best_dist = d
                best_idx = li
        if best_idx is None:
            continue
        if best_dist > x_per_letter * 1.5:
            continue
        target_text_idx = letter_positions[best_idx][0]
        # Don't double-mark
        if (
            target_text_idx + 1 < len(chars)
            and chars[target_text_idx + 1] == "\u0305"
        ):
            continue
        chars.insert(target_text_idx + 1, "\u0305")
        used_overline_letters.add(best_idx)
        # Adjust subsequent letter_positions text indices
        letter_positions = [
            (idx + 1 if pos_idx > best_idx else idx, ch)
            for pos_idx, (idx, ch) in enumerate(letter_positions)
        ]

    # Apply primes: insert "'" immediately after the closest letter.
    used_prime_letters: set[int] = set()
    for px in prime_anchors:
        best_idx = None
        best_dist = 1e9
        for li, (text_idx, ch) in enumerate(letter_positions):
            if li in used_prime_letters:
                continue
            approx_x = (li + 0.9) * x_per_letter  # primes attach to right side
            d = abs(approx_x - px)
            if d < best_dist:
                best_dist = d
                best_idx = li
        if best_idx is None:
            continue
        if best_dist > x_per_letter * 1.4:
            continue
        target_text_idx = letter_positions[best_idx][0]
        # Don't double-mark
        if (
            target_text_idx + 1 < len(chars)
            and chars[target_text_idx + 1] == "'"
        ):
            continue
        chars.insert(target_text_idx + 1, "'")
        used_prime_letters.add(best_idx)
        letter_positions = [
            (idx + 1 if pos_idx > best_idx else idx, ch)
            for pos_idx, (idx, ch) in enumerate(letter_positions)
        ]

    return "".join(chars)


__all__ = ["annotate_line_with_marks", "latex_to_readable"]
