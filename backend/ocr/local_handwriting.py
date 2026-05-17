"""
Local handwriting OCR using a free, on-device ensemble:

- microsoft/trocr-small-handwritten (default) or base  → English prose
- fhswf/TrOCR_Math_handwritten  → handwritten formulas → LaTeX → readable Unicode
- pix2tex (LaTeX-OCR, optional, USE_PIX2TEX=1)  → second math opinion

Live PDF preview (`fast=True`) runs prose on every line and **math TrOCR** on a
budget of math-like lines (PREVIEW_MATH_TR) so quadratics and calculus are not
left to the prose-only model, which misreads x², fractions, and f(x).

Full submission OCR (`fast=False`) runs **fhswf math TrOCR on every line** by
default (alongside prose, plus optional pix2tex when USE_PIX2TEX=1); ensemble
scoring picks the best read. Set OCR_MATH_HEURISTIC_ONLY=1 to restore the older
cheaper path (math model only when heuristics say the line is mathy or prose is
noisy).

LaTeX outputs are normalised (A̅, A′, Σ m(...)) for the review UI.

OpenCV line detection slices each page before OCR.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import threading
import time
from collections import Counter, OrderedDict
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# ── Optional Torch / Transformers ───────────────────────────────────────────

try:
    import torch  # type: ignore
    import transformers  # type: ignore
    from transformers import (  # type: ignore
        AutoProcessor,
        TrOCRProcessor,
        VisionEncoderDecoderModel,
    )
    _TROCR_AVAILABLE = True
    # Transformers prints noisy `[transformers] Both max_new_tokens and max_length…`
    # for every line, plus weight-load reports. Mute those so submission logs stay
    # readable; we still surface errors via our own logger.
    try:
        transformers.logging.set_verbosity_error()
    except Exception:
        pass
except Exception:  # pragma: no cover - optional deps
    torch = None  # type: ignore
    transformers = None  # type: ignore
    AutoProcessor = None  # type: ignore
    TrOCRProcessor = None  # type: ignore
    VisionEncoderDecoderModel = None  # type: ignore
    _TROCR_AVAILABLE = False


def _pix2tex_opt_in() -> bool:
    """
    pix2tex weights and timm/torchvision imports are heavy (~80MB + 2-4s per
    math line on CPU). It overlaps almost entirely with the fhswf math TrOCR,
    so we keep it OFF by default and let operators opt in with USE_PIX2TEX=1.
    """
    return os.getenv("USE_PIX2TEX", "").strip().lower() in ("1", "true", "yes", "on")


# Optional: free local math model (pix2tex / LaTeX-OCR). Install with
#   pip install pix2tex
# It is *not* a hard dependency — when missing we still run the image-level
# prime/overline detector to recover Boolean-algebra marks.
if _pix2tex_opt_in():
    try:
        from pix2tex.cli import LatexOCR  # type: ignore
        _PIX2TEX_AVAILABLE = True
    except Exception:  # pragma: no cover - optional package
        LatexOCR = None  # type: ignore
        _PIX2TEX_AVAILABLE = False
else:
    LatexOCR = None  # type: ignore
    _PIX2TEX_AVAILABLE = False


from .math_postprocess import annotate_line_with_marks, latex_to_readable


def trocr_runtime_available() -> bool:
    """True iff the import succeeded (deps installed in the venv)."""
    return _TROCR_AVAILABLE


# ── Line detection (OpenCV) ─────────────────────────────────────────────────


def _enhance_page_for_line_layout(page_pil: Image.Image) -> Image.Image:
    """
    Denoise + CLAHE before line finding so faint pencil / uneven lighting still
    forms solid blobs for dilation / projection.
    """
    gray = np.array(page_pil.convert("L"), dtype=np.uint8)
    gray = cv2.fastNlMeansDenoising(gray, None, h=6, templateWindowSize=7, searchWindowSize=21)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    return Image.fromarray(gray, mode="L").convert("RGB")


def _merge_vertical_boxes(
    boxes: List[Tuple[int, int, int, int]],
    max_gap_px: int,
    max_lines: int,
) -> List[Tuple[int, int, int, int]]:
    """Merge boxes separated by a small vertical gap (split ascenders / descenders)."""
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    merged: List[Tuple[int, int, int, int]] = []
    for box in boxes:
        if not merged:
            merged.append(box)
            continue
        last = merged[-1]
        gap = box[1] - (last[1] + last[3])
        same_col = abs(box[0] - last[0]) < max(box[2], last[2]) * 0.35
        if same_col and 0 <= gap <= max_gap_px:
            x1 = min(last[0], box[0])
            y1 = min(last[1], box[1])
            x2 = max(last[0] + last[2], box[0] + box[2])
            y2 = max(last[1] + last[3], box[1] + box[3])
            merged[-1] = (x1, y1, x2 - x1, y2 - y1)
        else:
            merged.append(box)
    return merged[:max_lines]


def _detect_line_boxes(
    page_pil: Image.Image,
    min_line_height_px: int = 18,
    min_line_width_px: int = 60,
    max_lines: int = 200,
) -> List[Tuple[int, int, int, int]]:
    """
    Find handwritten line bounding boxes on a page using horizontal dilation
    followed by contour detection. Returns a list of (x, y, w, h) sorted
    top-to-bottom.
    """
    img = np.array(page_pil.convert("L"))
    h, w = img.shape

    # Mild blur + Otsu — keeps strokes intact
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Horizontal dilation merges characters of one line into a single blob.
    # Kernel width scales with page width so it works at any DPI.
    kernel_width = max(15, w // 60)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 3))
    dilated = cv2.dilate(binary, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: List[Tuple[int, int, int, int]] = []
    for c in contours:
        x, y, ww, hh = cv2.boundingRect(c)
        if ww < min_line_width_px or hh < min_line_height_px:
            continue
        if hh > h * 0.4:  # likely the whole page; skip
            continue
        boxes.append((x, y, ww, hh))

    boxes.sort(key=lambda b: (b[1], b[0]))

    # Merge close-by boxes on the same row (broken handwriting tails)
    merged: List[Tuple[int, int, int, int]] = []
    for box in boxes:
        if not merged:
            merged.append(box)
            continue
        last = merged[-1]
        same_row = abs(box[1] - last[1]) < max(box[3], last[3]) * 0.5
        if same_row:
            x1 = min(last[0], box[0])
            y1 = min(last[1], box[1])
            x2 = max(last[0] + last[2], box[0] + box[2])
            y2 = max(last[1] + last[3], box[1] + box[3])
            merged[-1] = (x1, y1, x2 - x1, y2 - y1)
        else:
            merged.append(box)

    return merged[:max_lines]


def _detect_line_boxes_horizontal_projection(
    page_pil: Image.Image,
    min_line_height_px: int = 14,
    min_line_width_px: int = 80,
    max_lines: int = 120,
) -> List[Tuple[int, int, int, int]]:
    """
    Classic ink horizontal-projection line splitter. Works when contour dilation
    merges too much / too little (sparse math homework, wide equations).
    """
    img = np.array(page_pil.convert("L"))
    h, w = img.shape
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    row_ink = np.sum(bw == 255, axis=1).astype(np.float32)
    if row_ink.max() <= 1:
        return []
    med = float(np.median(row_ink))
    peak = float(row_ink.max())
    thresh = max(med * 0.45, peak * 0.06)
    active = row_ink > thresh
    boxes: List[Tuple[int, int, int, int]] = []
    i = 0
    while i < h:
        if not active[i]:
            i += 1
            continue
        j = i
        while j < h and active[j]:
            j += 1
        hh = j - i
        if hh >= min_line_height_px:
            boxes.append((0, i, w, hh))
        i = j
    boxes = _merge_vertical_boxes(boxes, max_gap_px=10, max_lines=max_lines * 2)
    boxes = [b for b in boxes if b[2] >= min_line_width_px and b[3] >= min_line_height_px]
    return boxes[:max_lines]


def _pick_line_boxes(
    page_rgb: Image.Image,
    max_lines: int,
) -> List[Tuple[int, int, int, int]]:
    """
    Contour-based boxes first; fall back to horizontal projection when the page
    is tall but we only got a couple of giant blobs (common on scans).
    """
    layout = _enhance_page_for_line_layout(page_rgb)
    contour_boxes = _detect_line_boxes(layout, max_lines=max_lines)
    long_side = max(page_rgb.width, page_rgb.height)
    # Too few lines on a worksheet-sized page → try projection
    if long_side >= 900 and len(contour_boxes) < 4:
        proj = _detect_line_boxes_horizontal_projection(layout, max_lines=max_lines)
        if len(proj) > len(contour_boxes):
            return proj
    if contour_boxes:
        return contour_boxes
    return _detect_line_boxes_horizontal_projection(layout, max_lines=max_lines)


def _enhance_crop_for_trocr(crop: Image.Image) -> Image.Image:
    """Per-line mild sharpen + CLAHE; upsample tiny crops so strokes have enough pixels."""
    gray = np.array(crop.convert("L"), dtype=np.uint8)
    h, w = gray.shape
    scale = 1.0
    if min(h, w) < 36:
        scale = max(36 / float(min(h, w)), 1.6)
    if scale > 1.0:
        nw, nh = int(w * scale), int(h * scale)
        gray = cv2.resize(gray, (nw, nh), interpolation=cv2.INTER_CUBIC)
    gray = cv2.fastNlMeansDenoising(gray, None, h=4, templateWindowSize=5, searchWindowSize=15)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(4, 4))
    gray = clahe.apply(gray)
    return Image.fromarray(gray, mode="L").convert("RGB")


# ── TrOCR engine ────────────────────────────────────────────────────────────


class _Pix2TexEngine:
    """Lazy wrapper around the free pix2tex LaTeX-OCR model."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model = None
        self._load_failed = False

    def available(self) -> bool:
        return _PIX2TEX_AVAILABLE and not self._load_failed

    def _ensure_loaded(self) -> bool:
        if not _PIX2TEX_AVAILABLE or self._load_failed:
            return False
        if self._model is not None:
            return True
        with self._lock:
            if self._model is not None:
                return True
            try:
                logger.info("Loading pix2tex math OCR model (first call downloads weights).")
                self._model = LatexOCR()  # type: ignore[misc]
                return True
            except Exception as ex:  # pragma: no cover - network/disk errors
                logger.warning("pix2tex load failed: %s", ex)
                self._load_failed = True
                return False

    def read_line(self, crop: Image.Image) -> str:
        if not self._ensure_loaded() or self._model is None:
            return ""
        try:
            latex = self._model(crop.convert("RGB"))  # type: ignore[misc]
        except Exception as ex:
            logger.debug("pix2tex inference failed: %s", ex)
            return ""
        return latex_to_readable(latex or "")


class _BaseTrOCREngine:
    """Shared lazy-loader for any VisionEncoderDecoder TrOCR model on HuggingFace."""

    def __init__(self, model_name: str, label: str) -> None:
        self.model_name = model_name
        self.label = label
        self._lock = threading.Lock()
        self._processor: Optional["TrOCRProcessor"] = None  # type: ignore[name-defined]
        self._model: Optional["VisionEncoderDecoderModel"] = None  # type: ignore[name-defined]
        self._ready = False
        self._load_failed = False

    def is_ready(self) -> bool:
        return self._ready

    def load_failed(self) -> bool:
        return self._load_failed

    def available(self) -> bool:
        return _TROCR_AVAILABLE and not self._load_failed

    def _ensure_loaded(self) -> bool:
        if self._ready:
            return True
        if self._load_failed or not _TROCR_AVAILABLE:
            return False
        with self._lock:
            if self._ready:
                return True
            try:
                logger.info(
                    "Loading %s (%s). First call downloads weights to HF cache.",
                    self.label,
                    self.model_name,
                )
                proc = None
                try:
                    proc = TrOCRProcessor.from_pretrained(self.model_name)  # type: ignore[union-attr]
                except Exception as ex1:
                    # Some math TrOCR fine-tunes ship via AutoProcessor only.
                    logger.debug(
                        "TrOCRProcessor.from_pretrained failed for %s (%s); "
                        "falling back to AutoProcessor.",
                        self.model_name,
                        ex1,
                    )
                    if AutoProcessor is None:
                        raise
                    proc = AutoProcessor.from_pretrained(self.model_name)  # type: ignore[union-attr]
                self._processor = proc
                self._model = VisionEncoderDecoderModel.from_pretrained(self.model_name)  # type: ignore[union-attr]
                self._model.eval()  # type: ignore[union-attr]
                self._ready = True
                logger.info("%s ready (CPU).", self.label)
                return True
            except Exception as ex:  # pragma: no cover - network/disk errors
                logger.warning("%s load failed: %s", self.label, ex)
                self._load_failed = True
                return False

    def read_line(self, crop: Image.Image, max_new_tokens: int = 96) -> str:
        if not self._ensure_loaded() or self._processor is None or self._model is None:
            return ""
        try:
            pixel_values = self._processor(  # type: ignore[union-attr]
                images=crop.convert("RGB"), return_tensors="pt"
            ).pixel_values
            with torch.no_grad():  # type: ignore[union-attr]
                # Force max_new_tokens to win silently by clearing max_length.
                ids = self._model.generate(  # type: ignore[union-attr]
                    pixel_values,
                    max_new_tokens=max_new_tokens,
                    max_length=None,
                    num_beams=1,
                    do_sample=False,
                )
            text = self._processor.batch_decode(ids, skip_special_tokens=True)[0]  # type: ignore[union-attr]
            return (text or "").strip()
        except Exception as ex:
            logger.debug("%s line decode failed: %s", self.label, ex)
            return ""


def _resolve_prose_model() -> str:
    """
    Default to the small TrOCR variant (~61M params) — about 4× faster on CPU
    than the base model with the same handwriting target. Override with
    TROCR_PROSE_MODEL=microsoft/trocr-base-handwritten on machines with more
    RAM/CPU budget.
    """
    raw = os.getenv("TROCR_PROSE_MODEL", "").strip()
    if raw:
        return raw
    return "microsoft/trocr-small-handwritten"


def _resolve_math_model() -> str:
    raw = os.getenv("TROCR_MATH_MODEL", "").strip()
    if raw:
        return raw
    return "fhswf/TrOCR_Math_handwritten"


class _PageCache:
    """Tiny LRU keyed on PNG-bytes hash + mode flags. Lives in-process."""

    def __init__(self, capacity: int = 32) -> None:
        self._cap = capacity
        self._data: "OrderedDict[str, str]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
            return None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self._cap:
                self._data.popitem(last=False)


class LocalTrOCRReader:
    """
    Page-level handwriting reader. Ensembles:
    - prose TrOCR (default: microsoft/trocr-small-handwritten; base via env)
    - math TrOCR (fhswf/TrOCR_Math_handwritten) — LaTeX output
    - pix2tex LatexOCR (optional install, opt-in) — second math opinion

    Lazy-init throughout; the heavy work only happens when a real handwritten
    page is processed.
    """

    PROSE_MODEL = _resolve_prose_model()
    MATH_MODEL = _resolve_math_model()

    # Retained for back-compat with callers that read this attribute.
    MODEL_NAME = PROSE_MODEL

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._prose = _BaseTrOCREngine(self.PROSE_MODEL, "TrOCR (prose)")
        self._math_trocr = _BaseTrOCREngine(self.MATH_MODEL, "TrOCR (math, fhswf MathWriting)")
        self._math_pix2tex: _Pix2TexEngine = _Pix2TexEngine()
        self._page_cache = _PageCache(capacity=64)
        self._ready = False
        self._load_failed = False
        # Expose the same fields older code expected on the prose engine.
        self._processor = None
        self._model = None

    def is_ready(self) -> bool:
        # Ready as long as at least the prose engine has loaded once.
        return self._prose.is_ready()

    def load_failed(self) -> bool:
        return self._prose.load_failed() and self._math_trocr.load_failed()

    def _ensure_loaded(self) -> bool:
        # Bootstrap prose model (required); math models are lazily loaded on demand
        return self._prose._ensure_loaded()

    def _read_line(self, crop: Image.Image) -> str:
        """Back-compat helper: prose-only line read."""
        return self._prose.read_line(crop)

    def _read_line_ensemble(
        self,
        crop: Image.Image,
        *,
        fast: bool,
        math_slots: Optional[List[int]] = None,
    ) -> str:
        """
        Per-line ensemble: prose TrOCR + optional math TrOCR (+ pix2tex when not fast).

        In `fast` mode (PDF routing preview), we still run **math TrOCR** when the
        line looks like an equation or the prose read is weak — prose-only TrOCR
        cannot reliably read handwritten `x^2`, fractions, etc.  A small per-page
        budget (`math_slots`) keeps latency bounded on worksheets with many lines.
        """
        prose_text = self._prose.read_line(crop)

        if not fast:
            # Full grading (`fast=False`): run fhswf math TrOCR on every line so
            # expressions are not missed when prose TrOCR looks "confident" but is
            # wrong. Ensemble scoring still prefers prose on clearly non-math lines.
            # Set OCR_MATH_HEURISTIC_ONLY=1 to restore the old cheaper path (math
            # model only when the line looks mathy or prose looks like OCR junk).
            heuristic_only = os.getenv("OCR_MATH_HEURISTIC_ONLY", "").strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            run_math = _should_run_math_models(prose_text) if heuristic_only else True
            candidates: List[Tuple[str, str]] = []
            if prose_text:
                candidates.append(("prose", prose_text))
            if run_math:
                if self._math_trocr.available():
                    latex = self._math_trocr.read_line(crop)
                    math_text = latex_to_readable(latex) if latex else ""
                    if math_text:
                        candidates.append(("trocr-math", math_text))
                if self._math_pix2tex.available():
                    pix_text = self._math_pix2tex.read_line(crop)
                    if pix_text:
                        candidates.append(("pix2tex", pix_text))
            if not candidates:
                return ""
            if len(candidates) == 1:
                return candidates[0][1]
            prefer_math = _ensemble_prefer_math(prose_text)
            return _pick_best_candidate(candidates, prefer_math=prefer_math)

        # ── fast preview: prose + selective math TrOCR (no pix2tex) ───────────
        if not self._math_trocr.available():
            return prose_text
        if math_slots is not None and math_slots[0] <= 0:
            return prose_text

        need_math = False
        s = (prose_text or "").strip()
        if not s:
            need_math = True
        elif _line_looks_mathy(prose_text) or _prose_looks_like_weak_ocr(prose_text):
            need_math = True

        if not need_math:
            return prose_text

        if math_slots is not None:
            math_slots[0] -= 1

        candidates = []
        if prose_text:
            candidates.append(("prose", prose_text))
        latex = self._math_trocr.read_line(crop)
        math_text = latex_to_readable(latex) if latex else ""
        if math_text:
            candidates.append(("trocr-math", math_text))
        if not candidates:
            return ""
        if len(candidates) == 1:
            return candidates[0][1]
        prefer_math = _ensemble_prefer_math(prose_text or math_text)
        return _pick_best_candidate(candidates, prefer_math=prefer_math)

    @staticmethod
    def _page_hash(page_pil: Image.Image, fast: bool, max_lines: int) -> str:
        """Stable key for the page-result cache."""
        buf = io.BytesIO()
        page_pil.convert("RGB").save(buf, format="PNG", optimize=False, compress_level=1)
        h = hashlib.sha1(buf.getvalue()).hexdigest()
        return f"{h}:{int(bool(fast))}:{max_lines}:v3fullmath"

    def read_page(
        self,
        page_pil: Image.Image,
        max_lines: int = 80,
        max_long_side_px: int = 2880,
        *,
        fast: bool = False,
    ) -> str:
        """
        Detect line bounding boxes on the page and run TrOCR on each crop.
        Returns lines joined with newlines, top-to-bottom.

        `fast=True` is meant for the live PDF-routing preview:
          - prose TrOCR on every line; **math TrOCR** (fhswf) on up to
            ``PREVIEW_MATH_TR lines`` per page when the line looks like math or
            the prose read is noisy — handwritten quadratics need the math model.
          - capped at ``max_lines`` (default 18 in fast mode).

        `fast=False` (submission grading): by default runs **math TrOCR on every
        line** together with prose (and pix2tex when enabled), unless
        ``OCR_MATH_HEURISTIC_ONLY=1`` restores the lighter heuristic path.
        """
        if not self._ensure_loaded():
            return ""

        try:
            raw = os.getenv("TROCR_MAX_LONG_SIDE", "2400").strip()
            cap = int(raw) if raw else 2400
        except ValueError:
            cap = 2400
        cap = min(cap, max_long_side_px)
        cap = max(1400, min(cap, 4000))

        page = page_pil.convert("RGB")
        long_side = max(page.width, page.height)
        if long_side > cap:
            scale = cap / float(long_side)
            page = page.resize(
                (int(page.width * scale), int(page.height * scale)),
                Image.Resampling.LANCZOS,
            )

        if fast:
            try:
                cap_lines = int(os.getenv("TROCR_PREVIEW_MAX_LINES", "18").strip() or "18")
            except ValueError:
                cap_lines = 18
            cap_lines = max(10, min(cap_lines, 28))
            max_lines = min(max_lines, cap_lines)
            try:
                math_budget = int(os.getenv("PREVIEW_MATH_TR", "12").strip() or "12")
            except ValueError:
                math_budget = 12
            math_budget = max(4, min(math_budget, 24))
            math_slots: Optional[List[int]] = [math_budget]
        else:
            math_slots = None

        cache_key = self._page_hash(page, fast=fast, max_lines=max_lines)
        cached = self._page_cache.get(cache_key)
        if cached is not None:
            logger.debug("TrOCR page cache hit (fast=%s)", fast)
            return cached

        boxes = _pick_line_boxes(page, max_lines=max_lines)
        if not boxes:
            self._page_cache.set(cache_key, "")
            return ""
        boxes = boxes[:max_lines]

        t0 = time.perf_counter()
        outputs: List[str] = []
        for (x, y, w, h) in boxes:
            # Small padding helps the model see ascenders / descenders. We add
            # extra space on top so overline bars sit inside the crop instead
            # of being clipped off — TrOCR otherwise just doesn't see them.
            pad_top = max(6, h // 3)
            pad_y = max(2, h // 6)
            pad_x = max(2, w // 50)
            x0 = max(0, x - pad_x)
            y0 = max(0, y - pad_top)
            x1 = min(page.width, x + w + pad_x)
            y1 = min(page.height, y + h + pad_y)
            crop = page.crop((x0, y0, x1, y1))
            crop_ml = _enhance_crop_for_trocr(crop)
            line_text = self._read_line_ensemble(
                crop_ml, fast=fast, math_slots=math_slots
            )
            if not line_text:
                continue
            # Image-level prime / overline rescue. Only run on lines that
            # already look math-y (Boolean algebra, equations) — running it on
            # prose turns letter ascenders / i-dots into prime spam (`camscanner`
            # → `c'a'n'n'e'r`). For prose lines we trust TrOCR's output.
            if _line_should_get_mark_rescue(line_text):
                try:
                    line_text = annotate_line_with_marks(crop_ml, line_text)
                except Exception as ex:  # pragma: no cover - defensive
                    logger.debug("math post-process failed: %s", ex)
            outputs.append(line_text)

        text = "\n".join(outputs).strip()
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "TrOCR page done: lines=%d/%d, fast=%s, model=%s, %dms",
            len(outputs),
            len(boxes),
            fast,
            self.PROSE_MODEL.rsplit("/", 1)[-1],
            elapsed_ms,
        )
        self._page_cache.set(cache_key, text)
        return text


def _line_should_get_mark_rescue(text: str) -> bool:
    """
    Gate image-level prime / overline rescue. Only run on lines that already
    look like math — running it on prose lines turns letter ascenders, i-dots
    and watermark text into prime spam (e.g. `camscanner` → `c'amscanner`).
    """
    s = (text or "").strip()
    if not s:
        return False
    # Skip clearly-watermark / scan-app lines outright.
    if re.search(
        r"(?i)(camscanner|scanned\s*with|adobe\s*scan|tiny\s*scanner|"
        r"microsoft\s*lens|genius\s*scan)",
        s,
    ):
        return False
    n = len(s)
    if n < 2:
        return False
    letters = sum(1 for c in s if c.isalpha())
    if letters == 0:
        return False
    lowers = sum(1 for c in s if c.islower())
    uppers = sum(1 for c in s if c.isupper())
    digits = sum(1 for c in s if c.isdigit())
    math_chars = sum(1 for c in s if c in "=+-*/()<>≤≥≠∑∏∫·×÷^_")
    primes_already = s.count("'") + s.count("\u0305") + s.count("\u0303")
    # Strong math signals → rescue marks
    if "=" in s or primes_already >= 1 or math_chars >= 2:
        return True
    if digits >= 2 and uppers >= 1:
        return True
    # Many lowercase letters in a row → it's prose, not math
    if lowers >= max(4, letters * 0.55):
        return False
    if re.search(r"[a-z]{4,}", s):
        return False
    # Mostly capitals (A, B, X, Y …) → likely Boolean variables
    if uppers >= 3 and uppers >= letters * 0.7:
        return True
    return False


def _prose_looks_like_weak_ocr(s: str) -> bool:
    """
    True when prose TrOCR output looks like a mis-read (consonant soup, symbol
    spam, extreme repetition). In that case we still run math TrOCR / pix2tex.
    """
    t = (s or "").strip()
    if not t or len(t) < 4:
        return False
    n = len(t)
    letters = [c for c in t if c.isalpha()]
    lc = len(letters)
    digits = sum(1 for c in t if c.isdigit())
    letter_ratio = lc / max(1, n)
    vowels = sum(1 for c in t.lower() if c in "aeiouy")
    vow_ratio = vowels / max(1, lc)
    caps = len(re.findall(r"[A-Z]", t))
    if n >= 8:
        top = Counter(t.lower()).most_common(1)[0][1]
        if top / n > 0.42:
            return True
    if lc >= 10 and letter_ratio > 0.5 and vow_ratio < 0.11:
        return True
    if letter_ratio < 0.22 and n >= 10:
        return True
    if caps >= 2 and (digits >= 1 or "(" in t or "[" in t):
        return True
    punct = sum(1 for c in t if c in "[](){}+=*/-_")
    if n >= 6 and punct >= 3 and punct / n > 0.2:
        return True
    return False


def _should_run_math_models(prose_text: str) -> bool:
    if not prose_text or not prose_text.strip():
        return True
    s = prose_text.strip()
    if _line_looks_mathy(s):
        return True
    return _prose_looks_like_weak_ocr(s)


def _ensemble_prefer_math(prose_text: str) -> bool:
    """Scoring tilt: math lines vs readable prose."""
    if not prose_text or not prose_text.strip():
        return True
    s = prose_text.strip()
    if _line_looks_mathy(s):
        return True
    if _prose_looks_like_weak_ocr(s):
        return True
    return False


def _line_looks_mathy(text: str) -> bool:
    """Heuristic: spend math-model inference on lines that look like math."""
    if not text:
        return True
    s = text.strip()
    if len(s) < 2:
        return False
    sl = s.lower()
    # Calculus / algebra: f(x), g(t), implicit differentiation labels
    if re.search(r"(?i)\b[a-z]\s*\(", s):
        return True
    # Letter touching digit — handwriting often loses superscripts (x^2 → x2)
    if re.search(r"[A-Za-z]\d|\d[A-Za-z]", s):
        return True
    # Binary operator between letter-words: AB + CD, ade + ABC, a + b
    if re.search(r"[A-Za-z]{1,6}\s*[+\-*/]\s*[A-Za-z]{1,6}", s):
        return True
    if re.search(r"\d", s):
        return True
    math_chars = sum(1 for c in s if c in "=+-*/()<>≤≥≠∑∏∫∞·×÷^_")
    primes = s.count("'") + s.count("’")
    has_eq = "=" in s
    caps = len(re.findall(r"[A-Z]", s))
    short_caps = len(re.findall(r"\b[A-Z]\b", s))
    # heuristics tuned for Boolean algebra / short math expressions
    return (
        has_eq
        or primes >= 1
        or math_chars >= 2
        or short_caps >= 3
        or caps >= 3
        or any(
            tok in sl
            for tok in (
                "\\sum",
                "\\frac",
                "\\bar",
                "overline",
                "sqrt",
                "cdot",
                "times",
                "m(",
                "m ",
                "diff",
                "d/d",
                "dx",
                "dy",
            )
        )
        or any(ch in s for ch in "∨∧⊕¬⊂⊃∪∩")
    )


def _candidate_score(text: str, prefer_math: bool) -> float:
    """
    Heuristic 0..1 quality score used to pick between OCR engines for one line.
    Rewards math-shaped output on math lines; rewards prose-shaped output on
    prose lines; penalises empty / extremely short results.
    """
    s = (text or "").strip()
    if not s:
        return 0.0
    n = len(s)
    alnum = sum(1 for c in s if c.isalnum())
    math_chars = sum(1 for c in s if c in "=+-*/()<>·×÷^_")
    primes = s.count("'") + s.count("\u0305") + s.count("\u0303")
    word_runs = len(re.findall(r"[A-Za-z]{4,}", s))
    junk = len(re.findall(r"\bee\b|\boo\b|eee|ooo", s.lower()))
    latex_noise = (s.count("\\") + s.count("{") + s.count("}")) / max(1, n)
    noise_w = 0.28 if not prefer_math else 0.14
    score = 0.30 * (alnum / max(1, n))
    score -= noise_w * min(1.0, latex_noise * 4.0)
    if prefer_math:
        score += 0.30 * min(1.0, math_chars / max(2, n // 6))
        score += 0.20 * min(1.0, primes / 2.0)
    else:
        score += 0.30 * min(1.0, word_runs / max(1, n // 30))
        score += 0.10 * min(1.0, math_chars / max(2, n // 4))
    score += 0.10 * (1.0 if n >= 6 else n / 6.0)
    score -= 0.20 * min(1.0, junk / max(1, n // 30))
    # Disincentivise outputs that are *just* one token: math engines sometimes
    # collapse a long line into a single fragment.
    if n < 4:
        score *= 0.4
    return max(0.0, min(1.0, score))


def _pick_best_candidate(
    candidates: List[Tuple[str, str]], *, prefer_math: bool
) -> str:
    """
    Choose the highest-scoring candidate. Tie-break: math engines on math-like
    lines; prose engine on normal handwriting.
    """

    def _tie_break(name: str) -> int:
        if prefer_math:
            if name == "trocr-math":
                return 3
            if name == "pix2tex":
                return 2
            if name == "prose":
                return 1
            return 0
        if name == "prose":
            return 3
        if name == "trocr-math":
            return 2
        if name == "pix2tex":
            return 1
        return 0

    ranked = sorted(
        candidates,
        key=lambda kv: (_candidate_score(kv[1], prefer_math), _tie_break(kv[0])),
        reverse=True,
    )
    return ranked[0][1]


# Back-compat shim retained for older imports
def _pick_best_line(text_a: str, text_b: str) -> str:
    """Two-way version of _pick_best_candidate kept for older callers."""
    s = (text_a or text_b or "").strip()
    return _pick_best_candidate(
        [("a", text_a or ""), ("b", text_b or "")],
        prefer_math=_ensemble_prefer_math(s),
    )


def local_handwriting_engine_status() -> dict:
    """
    Introspection for /api/ocr/status. Does not load model weights — only env
    resolution and whether pix2tex was importable when USE_PIX2TEX was on.
    """
    heuristic_only = os.getenv("OCR_MATH_HEURISTIC_ONLY", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    return {
        "proseModel": _resolve_prose_model(),
        "mathTrocrModel": _resolve_math_model(),
        "pix2texOptIn": _pix2tex_opt_in(),
        "pix2texImportable": bool(_PIX2TEX_AVAILABLE),
        "mathEnsembleMode": "heuristic" if heuristic_only else "full",
    }


# ── Module-level singleton ──────────────────────────────────────────────────


_trocr_reader: Optional[LocalTrOCRReader] = None


def _trocr_explicitly_disabled() -> bool:
    """Operator opt-out — e.g. on slim Docker images that don't ship torch."""
    return os.getenv("USE_TROCR", "").strip().lower() in ("0", "false", "no", "off")


def get_trocr_reader_if_enabled() -> Optional[LocalTrOCRReader]:
    """
    Returns a LocalTrOCRReader by default whenever the runtime imports are
    available — students should not have to ask an admin to turn handwriting
    recognition on. Set `USE_TROCR=0` (or `false`/`off`) to opt out, e.g. on
    deployments that don't ship torch/transformers.

    The reader is lazy: the ~330MB model only downloads/loads on the first
    `read_page` call, so backend startup stays fast.
    """
    if _trocr_explicitly_disabled():
        return None
    if not _TROCR_AVAILABLE:
        # Optional dependency missing — silently fall through to the older
        # Tesseract/EasyOCR ensemble. Logged at debug level so it doesn't spam
        # production logs when running on slim images.
        logger.debug(
            "torch/transformers not importable; local TrOCR disabled."
        )
        return None
    global _trocr_reader
    if _trocr_reader is None:
        _trocr_reader = LocalTrOCRReader()
    return _trocr_reader
