"""
PP-StructureV3 document OCR via PaddleOCR.

Layout-aware parsing with optional formula recognition — useful for handwritten
math worksheets and mixed text/equation pages. Opt in with USE_PP_STRUCTURE=1 and:

    pip install -r requirements-paddleocr.txt

See: https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, List, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_PIPELINE = None
_PIPELINE_LOCK = threading.Lock()


def pp_structure_opt_in() -> bool:
    return os.getenv("USE_PP_STRUCTURE", "").strip().lower() in ("1", "true", "yes", "on")


def pp_structure_runtime_available() -> bool:
    if not pp_structure_opt_in():
        return False
    try:
        from paddleocr import PPStructureV3  # noqa: F401
    except Exception:
        return False
    return True


def pp_structure_engine_status() -> dict:
    """Summary for /api/ocr/status."""
    opt_in = pp_structure_opt_in()
    importable = False
    if opt_in:
        try:
            from paddleocr import PPStructureV3  # noqa: F401

            importable = True
        except Exception as ex:
            return {
                "optIn": True,
                "importable": False,
                "ready": False,
                "lang": os.getenv("PP_STRUCTURE_LANG", "en"),
                "device": os.getenv("PP_STRUCTURE_DEVICE", "cpu"),
                "error": str(ex),
            }
    return {
        "optIn": opt_in,
        "importable": importable,
        "ready": opt_in and importable,
        "lang": os.getenv("PP_STRUCTURE_LANG", "en"),
        "device": os.getenv("PP_STRUCTURE_DEVICE", "cpu"),
        "textRecognitionModel": os.getenv(
            "PP_STRUCTURE_TEXT_REC_MODEL", "en_PP-OCRv4_mobile_rec"
        ),
    }


def _build_pipeline(*, fast: bool):
    from paddleocr import PPStructureV3

    lang = os.getenv("PP_STRUCTURE_LANG", "en").strip() or "en"
    device = os.getenv("PP_STRUCTURE_DEVICE", "cpu").strip() or "cpu"
    text_rec_model = os.getenv("PP_STRUCTURE_TEXT_REC_MODEL", "").strip()
    if not text_rec_model:
        # English grading site default; override via PP_STRUCTURE_TEXT_REC_MODEL.
        text_rec_model = "en_PP-OCRv4_mobile_rec" if lang.startswith("en") else None

    # Formula recognition is the main win for math grading but is slow on CPU.
    use_formula = not fast and os.getenv("PP_STRUCTURE_FORMULA", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )
    use_tables = not fast and os.getenv("PP_STRUCTURE_TABLES", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    logger.info(
        "Loading PP-StructureV3 (device=%s, formula=%s, tables=%s, fast=%s, rec_model=%s)",
        device,
        use_formula,
        use_tables,
        fast,
        text_rec_model,
    )
    kwargs = dict(
        device=device,
        use_doc_orientation_classify=True,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        use_formula_recognition=use_formula,
        use_table_recognition=use_tables,
        use_chart_recognition=False,
        use_seal_recognition=False,
        format_block_content=True,
    )
    if text_rec_model:
        kwargs["text_recognition_model_name"] = text_rec_model
    else:
        kwargs["lang"] = lang
    return PPStructureV3(**kwargs)


def _get_pipeline(*, fast: bool):
    """
    Lazy singleton. We rebuild when switching between fast/full settings because
    formula/table modules differ.
    """
    global _PIPELINE
    cache_key = "fast" if fast else "full"
    with _PIPELINE_LOCK:
        if _PIPELINE is not None and _PIPELINE.get("key") == cache_key:
            return _PIPELINE["pipeline"]
        pipeline = _build_pipeline(fast=fast)
        _PIPELINE = {"key": cache_key, "pipeline": pipeline}
        return pipeline


def _extract_block_lines(data: dict) -> List[str]:
    lines: List[str] = []
    parsing = data.get("parsing_res_list") or []
    if isinstance(parsing, list):
        ordered = sorted(
            (b for b in parsing if isinstance(b, dict)),
            key=lambda b: (
                b.get("block_order") if b.get("block_order") is not None else 10**9,
                b.get("block_id") if b.get("block_id") is not None else 10**9,
            ),
        )
        for block in ordered:
            content = block.get("block_content")
            if content is not None and str(content).strip():
                lines.append(str(content).strip())
    return lines


def _extract_from_result(res: Any) -> str:
    md = getattr(res, "markdown", None)
    if isinstance(md, dict):
        md_text = md.get("markdown_texts")
        if isinstance(md_text, str) and md_text.strip():
            return md_text.strip()

    payload = getattr(res, "json", None)
    if isinstance(payload, dict):
        # PaddleX result objects usually nest under `res`.
        inner = payload.get("res") if isinstance(payload.get("res"), dict) else payload
        block_lines = _extract_block_lines(inner)
        if block_lines:
            return "\n".join(block_lines)

        ocr_res = inner.get("overall_ocr_res") or inner.get("ocr_res") or {}
        if isinstance(ocr_res, dict):
            rec_texts = ocr_res.get("rec_texts") or []
            if isinstance(rec_texts, list):
                texts = [str(t).strip() for t in rec_texts if str(t).strip()]
                if texts:
                    return "\n".join(texts)

    return ""


def read_page(image: Image.Image, *, fast: bool = False) -> str:
    """
    Run PP-StructureV3 on a single page image and return plain text / markdown.
    """
    if not pp_structure_opt_in():
        return ""

    rgb = image.convert("RGB")
    np_img = np.asarray(rgb)
    pipeline = _get_pipeline(fast=fast)

    try:
        output = pipeline.predict(input=np_img)
    except Exception as ex:
        logger.warning("PP-StructureV3 predict failed: %s", ex)
        return ""

    chunks: List[str] = []
    for res in output or []:
        text = _extract_from_result(res)
        if text.strip():
            chunks.append(text.strip())

    return "\n\n".join(chunks)
