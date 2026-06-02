"""
Heuristic grading for handwritten graphs, diagrams, and shapes in answer scans.

Compares OpenCV-detected structure (axes, lines, circles, contours) against
reference graph/shape specs stored in question embedded content or TipTap JSON.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def _decode_image(image_bytes: bytes) -> Optional[np.ndarray]:
    if not image_bytes:
        return None
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def extract_visual_features(image_bytes: bytes) -> Dict[str, Any]:
    """Detect structural features in a handwritten diagram / graph sketch."""
    img = _decode_image(image_bytes)
    if img is None:
        return {}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)

    h, w = gray.shape[:2]
    min_line = max(30, int(min(h, w) * 0.08))

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=60, minLineLength=min_line, maxLineGap=15
    )
    line_count = 0 if lines is None else len(lines)

    horiz, vert = 0, 0
    if lines is not None:
        for ln in lines:
            x1, y1, x2, y2 = ln[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 20 or angle > 160:
                horiz += 1
            elif 70 < angle < 110:
                vert += 1

    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=30,
        param1=100,
        param2=35,
        minRadius=8,
        maxRadius=min(h, w) // 3,
    )
    circle_count = 0 if circles is None else circles.shape[1]

    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    sig_contours = [
        c for c in contours if cv2.contourArea(c) > (h * w * 0.002)
    ]

    return {
        "line_count": line_count,
        "horizontal_lines": horiz,
        "vertical_lines": vert,
        "circle_count": circle_count,
        "contour_count": len(sig_contours),
        "has_axes": horiz >= 1 and vert >= 1,
        "width": w,
        "height": h,
    }


def _visual_specs_from_question(question) -> List[Dict[str, Any]]:
    """Collect expected graph/shape specs from embedded content and rich_content."""
    specs: List[Dict[str, Any]] = []

    for ec in getattr(question, "embedded_content", None) or []:
        ctype = (getattr(ec, "content_type", "") or "").lower()
        raw = getattr(ec, "content_data", None)
        try:
            data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            data = {}
        if ctype in ("graph", "chart"):
            specs.append({"kind": "graph", **data})
        elif ctype == "shape":
            specs.append({"kind": "shape", **data})

    rich = getattr(question, "rich_content", None)
    if rich:
        try:
            doc = json.loads(rich) if isinstance(rich, str) else rich
        except Exception:
            doc = None
        if isinstance(doc, dict):
            specs.extend(_walk_rich_for_visuals(doc))
    return specs


def _walk_rich_for_visuals(node: dict) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(node, dict):
        return out
    ntype = node.get("type", "")
    if ntype == "graph":
        attrs = node.get("attrs") or {}
        out.append({"kind": "graph", **attrs})
    elif ntype == "image":
        src = (node.get("attrs") or {}).get("src", "")
        if src.startswith("data:image/svg"):
            out.append({"kind": "shape", "src": src})
    for child in node.get("content") or []:
        if isinstance(child, dict):
            out.extend(_walk_rich_for_visuals(child))
    return out


def _score_graph_sketch(features: Dict[str, Any], spec: Dict[str, Any]) -> Tuple[float, str]:
    """Score a student sketch against a reference graph spec."""
    graph_type = (spec.get("graphType") or spec.get("graph_type") or "line").lower()
    data = spec.get("data") or []
    expected_points = len(data) if isinstance(data, list) else 0

    score = 0.0
    notes: List[str] = []

    if features.get("has_axes"):
        score += 0.35
        notes.append("axes detected")
    elif features.get("horizontal_lines", 0) + features.get("vertical_lines", 0) >= 1:
        score += 0.15
        notes.append("partial axis structure")

    lc = features.get("line_count", 0)
    cc = features.get("contour_count", 0)

    if graph_type == "pie":
        circles = features.get("circle_count", 0)
        if circles >= 1:
            score += 0.45
            notes.append("circular shape detected")
        if cc >= 2:
            score += 0.15
    elif graph_type == "bar":
        # Bars often appear as vertical strokes or rectangular contours
        bars_guess = max(features.get("vertical_lines", 0), cc // 2)
        if expected_points and bars_guess >= max(1, expected_points - 1):
            score += 0.45
            notes.append(f"~{bars_guess} bar-like features")
        elif bars_guess >= 2:
            score += 0.25
            notes.append("multiple bar-like strokes")
    else:
        # line / default
        if lc >= 2:
            score += 0.35
            notes.append(f"{lc} lines detected")
        if expected_points >= 2 and lc >= expected_points:
            score += 0.2
            notes.append("enough segments for data points")

    if cc >= 3:
        score += 0.1

    score = min(1.0, score)
    if score < 0.2 and lc + cc < 2:
        return 0.0, "No clear graph structure detected in the scan"
    return score, "; ".join(notes) if notes else "visual structure compared"


def _score_shape_sketch(features: Dict[str, Any], spec: Dict[str, Any]) -> Tuple[float, str]:
    cc = features.get("contour_count", 0)
    circles = features.get("circle_count", 0)
    src = (spec.get("src") or "").lower()
    if "circle" in src or "ellipse" in src:
        if circles >= 1:
            return 0.85, "Circle-like shape detected"
        return 0.2, "Expected circular shape — not clearly detected"
    if cc >= 1:
        return 0.65, f"Hand-drawn shape detected ({cc} regions)"
    return 0.0, "No shape detected in scan"


def grade_visual_answer(
    image_bytes: bytes,
    question,
    ocr_text: str = "",
) -> Optional[Dict[str, Any]]:
    """
    If the question expects a graph/shape, score the student's scanned drawing.

    Returns None when the question has no visual reference (text-only grading).
    """
    specs = _visual_specs_from_question(question)
    if not specs and not _question_mentions_visual(question, ocr_text):
        return None

    features = extract_visual_features(image_bytes)
    if not features:
        return None

    best = 0.0
    best_note = ""
    for spec in specs:
        kind = spec.get("kind", "graph")
        if kind == "shape":
            sc, note = _score_shape_sketch(features, spec)
        else:
            sc, note = _score_graph_sketch(features, spec)
        if sc > best:
            best = sc
            best_note = note

    if not specs and _question_mentions_visual(question, ocr_text):
        # Generic diagram question without stored spec — reward clear structure
        if features.get("has_axes") or features.get("line_count", 0) >= 3:
            best = 0.55
            best_note = "Diagram with axes or multiple lines detected"
        elif features.get("contour_count", 0) >= 2:
            best = 0.4
            best_note = "Hand-drawn diagram regions detected"

    if best <= 0:
        return {
            "score_ratio": 0.0,
            "feedback": best_note or "Could not verify diagram/graph in submission",
            "features": features,
        }

    return {
        "score_ratio": best,
        "feedback": best_note,
        "features": features,
    }


def _question_mentions_visual(question, ocr_text: str) -> bool:
    blob = " ".join(
        [
            getattr(question, "text", "") or "",
            ocr_text or "",
        ]
    ).lower()
    keywords = (
        "graph", "plot", "sketch", "diagram", "draw", "chart", "axes",
        "axis", "curve", "shape", "triangle", "circle", "rectangle",
    )
    return any(k in blob for k in keywords)


def merge_visual_score(
    text_score: float,
    text_max: float,
    visual: Optional[Dict[str, Any]],
    visual_weight: float = 0.35,
) -> Tuple[float, str]:
    """
    Blend text/step score with visual score when a diagram was expected.
    visual_weight = fraction of points that come from the drawing (rest from steps/text).
    """
    if not visual or text_max <= 0:
        return text_score, ""

    ratio = float(visual.get("score_ratio") or 0.0)
    visual_pts = text_max * visual_weight * ratio
    text_pts = text_score * (1.0 - visual_weight)
    combined = round(text_pts + visual_pts, 2)
    note = visual.get("feedback") or ""
    extra = f" Visual: {note} ({ratio:.0%})." if note else ""
    return combined, extra
