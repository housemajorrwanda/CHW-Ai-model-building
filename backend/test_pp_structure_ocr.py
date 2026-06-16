#!/usr/bin/env python3
"""
Smoke-test PP-StructureV3 integration.

Usage (from backend/):
  USE_PP_STRUCTURE=1 python test_pp_structure_ocr.py
  USE_PP_STRUCTURE=1 python test_pp_structure_ocr.py path/to/scan.jpg

Downloads the official demo image when no local file is given.
"""

from __future__ import annotations

import os
import sys
import tempfile
import urllib.request
from pathlib import Path

# Ensure backend package imports resolve when run as a script.
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from PIL import Image

import importlib.util

# Load pp_structure_processor without pulling the full OCR stack (pytesseract, etc.).
_pp_spec = importlib.util.spec_from_file_location(
    "pp_structure_processor",
    BACKEND_DIR / "ocr" / "pp_structure_processor.py",
)
_pp_mod = importlib.util.module_from_spec(_pp_spec)
assert _pp_spec.loader is not None
_pp_spec.loader.exec_module(_pp_mod)
pp_structure_engine_status = _pp_mod.pp_structure_engine_status
pp_structure_opt_in = _pp_mod.pp_structure_opt_in
read_page = _pp_mod.read_page

DEMO_URL = (
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/"
    "pp_structure_v3_demo.png"
)


def _load_image(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def main() -> int:
    os.environ.setdefault("USE_PP_STRUCTURE", "1")
    status = pp_structure_engine_status()
    print("PP-Structure status:", status)
    if not pp_structure_opt_in():
        print("Set USE_PP_STRUCTURE=1 to run this test.")
        return 1
    if not status.get("importable"):
        print(
            "paddleocr is not installed. Try:\n"
            "  python3.11 -m pip install paddlepaddle==3.3.0 "
            "-i https://www.paddlepaddle.org.cn/packages/stable/cpu/\n"
            "  python3.11 -m pip install -r requirements-paddleocr.txt"
        )
        return 1

    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1]).expanduser()
        if not image_path.is_file():
            print(f"File not found: {image_path}")
            return 1
    else:
        tmp = Path(tempfile.gettempdir()) / "pp_structure_v3_demo.png"
        if not tmp.is_file():
            print(f"Downloading demo image → {tmp}")
            urllib.request.urlretrieve(DEMO_URL, tmp)
        image_path = tmp

    print(f"\nInput: {image_path}")
    image = _load_image(image_path)

    print("\n--- PP-StructureV3 (full) ---")
    full_text = read_page(image, fast=False)
    print(full_text or "(empty)")

    print("\n--- PP-StructureV3 (fast) ---")
    fast_text = read_page(image, fast=True)
    print(fast_text or "(empty)")

    # Optional baseline for comparison.
    try:
        from ocr.ocr_pipeline import OCRProcessor

        ocr = OCRProcessor(language="en", use_easyocr=False)
        baseline = ocr._ocr_page_handwriting(image, fast=True)  # noqa: SLF001
        print("\n--- Existing local OCR (fast baseline) ---")
        print(baseline or "(empty)")
    except Exception as ex:
        print(f"\n(Skipping baseline OCR comparison: {ex})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
