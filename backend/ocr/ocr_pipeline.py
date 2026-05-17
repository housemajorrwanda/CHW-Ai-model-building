import io
import logging
import re
from dataclasses import dataclass
from typing import List, Sequence, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps, ImageFilter
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from .cloud_ocr import CloudOCRManager
except Exception:  # pragma: no cover - cloud module is optional
    CloudOCRManager = None  # type: ignore

try:
    from .local_handwriting import (
        get_trocr_reader_if_enabled,
        trocr_runtime_available,
    )
except Exception:  # pragma: no cover - optional ML deps
    def get_trocr_reader_if_enabled():  # type: ignore[misc]
        return None

    def trocr_runtime_available() -> bool:  # type: ignore[misc]
        return False


@dataclass
class OCRResult:
    """Structured result returned by the OCR pipeline."""

    combined_text: str
    steps: List[str]
    page_count: int
    processed_previews: List[bytes]


class OCRProcessor:
    """Extracts ordered steps from uploaded math work (images or PDFs)."""

    def __init__(self, language: str = "en", dpi: int = 300, psm: int = 6, use_easyocr: bool = True):
        # Convert language codes: EasyOCR uses 'en', Tesseract uses 'eng'
        self.easyocr_lang = 'en' if language.startswith('en') else language
        self.tesseract_lang = 'eng' if language.startswith('en') else language
        
        self.dpi = dpi
        self.psm = psm
        self.use_easyocr = use_easyocr and EASYOCR_AVAILABLE
        # OEM 3 lets Tesseract decide the best engine.
        self.tesseract_config = f"--oem 3 --psm {self.psm}"
        
        # Initialize EasyOCR reader if available and requested
        self.easyocr_reader = None
        if self.use_easyocr:
            try:
                self.easyocr_reader = easyocr.Reader([self.easyocr_lang], gpu=False)
            except Exception as e:
                print(f"EasyOCR initialization failed: {e}")
                self.use_easyocr = False

        # Cloud OCR (Mathpix / Google Vision / Azure Read) — primary when configured.
        # Local engines are kept as a fallback so the system stays usable without an
        # API key, but they cannot match a dedicated handwriting/math OCR service.
        self.cloud = CloudOCRManager() if CloudOCRManager else None
        if self.cloud and self.cloud.active_provider_name:
            logger.info(
                "Cloud OCR provider active: %s (handwriting/math)",
                self.cloud.active_provider_name,
            )

        # Local TrOCR (microsoft/trocr-small-handwritten by default + fhswf math).
        # Disabled with USE_TROCR=0. Lazy-loads weights on first use.
        self.trocr = get_trocr_reader_if_enabled()
        self.trocr_runtime_available = trocr_runtime_available()
        if self.trocr is not None:
            logger.info("Local TrOCR handwriting engine enabled (model loads on first use).")

    # ── Direct PDF text extraction (no OCR needed for typed PDFs) ────────────

    @staticmethod
    def extract_pdf_text_pages(pdf_bytes: bytes) -> List[str]:
        """
        Try to extract text directly from a PDF using pypdf.
        Returns one string per page.  If a page has no selectable text (scanned),
        the string for that page is empty.
        """
        try:
            import io as _io
            from pypdf import PdfReader
            reader = PdfReader(_io.BytesIO(pdf_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ''
                # Normalise whitespace
                text = '\n'.join(
                    line.strip() for line in text.splitlines() if line.strip()
                )
                pages.append(text)
            return pages
        except Exception:
            return []

    @staticmethod
    def _text_is_clean(text: str) -> bool:
        """
        Return True if the extracted text looks like real readable content
        (not garbled OCR noise or just whitespace).
        """
        if not text or len(text.strip()) < 15:
            return False
        # Ratio of printable ASCII to total chars should be high
        printable = sum(1 for c in text if c.isprintable() or c in '\n\t')
        return (printable / len(text)) > 0.85

    # ── Main entry point ──────────────────────────────────────────────────────

    def extract_steps_from_file(
        self,
        file_bytes: bytes,
        filename: str,
        *,
        fast: bool = False,
    ) -> OCRResult:
        """
        Extract answer steps from an image or PDF file.

        For PDFs: tries direct text extraction first (perfect for typed answers).
        Falls back to image-based OCR when the PDF is scanned / handwritten.

        When `fast=True`, the slower local TrOCR model is skipped (used during
        the live PDF routing preview where we just need a quick excerpt).
        Submission-time grading should call with the default `fast=False`.
        """
        lower = filename.lower()

        # ── Fast path: typed PDF ─────────────────────────────────────────────
        if lower.endswith('.pdf'):
            pdf_pages = self.extract_pdf_text_pages(file_bytes)
            # If every page produced clean text, skip OCR entirely
            clean_pages = [p for p in pdf_pages if self._text_is_clean(p)]
            if clean_pages and len(clean_pages) == max(len(pdf_pages), 1):
                all_text = '\n\n'.join(clean_pages)
                steps = []
                for page_text in clean_pages:
                    steps.extend(self._segment_steps(page_text))
                steps = [s for s in (s.strip() for s in steps) if s]
                return OCRResult(
                    combined_text=all_text,
                    steps=steps,
                    page_count=len(clean_pages),
                    processed_previews=[],   # no images to show
                )
            # Partial or zero extraction → fall through to OCR below,
            # but seed the text with whatever was extracted.
            pre_extracted = pdf_pages  # list of str, may be empty per page
        else:
            pre_extracted = []

        # ── OCR path (images + scanned PDFs) ─────────────────────────────────
        images = self._load_pages(file_bytes, filename)
        if not images:
            return OCRResult("", [], 0, [])

        combined_text: List[str] = []
        extracted_steps: List[str] = []
        previews: List[bytes] = []

        for page_idx, image in enumerate(images):
            # If we already have clean direct text for this page, use it
            direct = pre_extracted[page_idx] if page_idx < len(pre_extracted) else ''
            if self._text_is_clean(direct):
                text = direct
                previews.append(self._pil_to_png_bytes(self._light_preprocess(image)))
            else:
                light = self._light_preprocess(image)
                previews.append(self._pil_to_png_bytes(light))
                text = self._ocr_page_handwriting(image, fast=fast)

            combined_text.append(text.strip())
            extracted_steps.extend(self._segment_steps(text))

        steps = [step for step in (s.strip() for s in extracted_steps) if step]
        steps = self._merge_instruction_and_equation_lines(steps)
        return OCRResult(
            combined_text="\n\n".join(t for t in combined_text if t),
            steps=steps,
            page_count=len(images),
            processed_previews=previews,
        )

    def _load_pages(self, file_bytes: bytes, filename: str) -> Sequence[Image.Image]:
        """Load uploaded bytes into one or more PIL Images."""
        lower_name = filename.lower()
        try:
            if lower_name.endswith(".pdf"):
                return convert_from_bytes(file_bytes, dpi=self.dpi)

            image = Image.open(io.BytesIO(file_bytes))
            return [image.convert("RGB")]
        except Exception:
            return []

    # ── Shared normalisation ──────────────────────────────────────────────────

    def _base_normalise(self, image: Image.Image) -> np.ndarray:
        """
        Shared first step: grayscale → upscale → fix inversion.
        Returns an uint8 numpy array (no binarisation yet).
        """
        gray = ImageOps.grayscale(image)

        # Upscale images that are too small for reliable OCR (handwriting benefits a lot)
        min_width = 2200
        if gray.width < min_width:
            scale = min_width / gray.width
            gray = gray.resize(
                (int(gray.width * scale), int(gray.height * scale)),
                Image.Resampling.LANCZOS,
            )

        np_img = np.array(gray, dtype=np.uint8)

        # Fix dark-on-light inversion (e.g. photos of whiteboards or dark paper)
        if np.mean(np_img) < 110:
            np_img = 255 - np_img

        return np_img

    # ── Light preprocessing (for EasyOCR) ────────────────────────────────────

    def _light_preprocess(self, image: Image.Image) -> Image.Image:
        """
        Minimal preprocessing that preserves natural texture for EasyOCR.
        EasyOCR's neural network reads natural photos better than binary images.
        """
        np_img = self._base_normalise(image)

        # Mild denoising — keep strokes intact
        np_img = cv2.fastNlMeansDenoising(np_img, None, h=7,
                                           templateWindowSize=7,
                                           searchWindowSize=21)

        # Gentle CLAHE to even out lighting (phone photos taken at an angle)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        np_img = clahe.apply(np_img)

        # Return as RGB so EasyOCR can use colour channels if needed
        pil = Image.fromarray(np_img, mode='L').convert('RGB')
        return pil

    def _high_contrast_rgb(self, image: Image.Image) -> Image.Image:
        """Second EasyOCR pass: stretch contrast for faint pencil / gray scans."""
        np_img = self._base_normalise(image)
        np_img = cv2.normalize(np_img, None, 0, 255, cv2.NORM_MINMAX)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        np_img = clahe.apply(np_img)
        # Mild sharpen to emphasize strokes
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
        sharp = cv2.filter2D(np_img, -1, kernel)
        sharp = np.clip(sharp, 0, 255).astype(np.uint8)
        return Image.fromarray(sharp, mode="L").convert("RGB")

    def _soft_binarize(self, image: Image.Image) -> Image.Image:
        """Otsu binarisation — often preserves pencil strokes better than adaptive thresh."""
        np_img = self._base_normalise(image)
        np_img = cv2.GaussianBlur(np_img, (3, 3), 0)
        _, binary = cv2.threshold(np_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(binary) < 128:
            binary = cv2.bitwise_not(binary)
        return Image.fromarray(binary.astype(np.uint8), mode="L")

    # ── Heavy preprocessing (for Tesseract) ──────────────────────────────────

    def _heavy_preprocess(self, image: Image.Image) -> Image.Image:
        """
        Full binarisation pipeline for Tesseract.
        Goal: crisp black text on white background.
        """
        np_img = self._base_normalise(image)

        # CLAHE for local contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        np_img = clahe.apply(np_img)

        # Denoising
        np_img = cv2.fastNlMeansDenoising(np_img, None, h=10,
                                           templateWindowSize=7,
                                           searchWindowSize=21)

        # Gentle deskew (≤ 5°)
        np_img = self._deskew(np_img)

        # Adaptive threshold → black text on white background
        binary = cv2.adaptiveThreshold(
            np_img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            21, 10,
        )

        # Morphological close to reconnect broken strokes
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Guarantee black text on white background
        # THRESH_BINARY: pixels > threshold → 255 (white), else → 0 (black)
        # So text (darker regions) becomes 0 (black), background 255 (white). ✓
        # If somehow the image is inverted, fix it.
        if np.mean(binary) < 128:           # mostly black → flip
            binary = cv2.bitwise_not(binary)

        return Image.fromarray(binary.astype(np.uint8), mode='L')

    @staticmethod
    def _ocr_quality_score(text: str) -> float:
        """
        Heuristic 0..1: prefer math-like, letter-dense output; penalize repetitive OCR junk.
        Used to pick the best among EasyOCR / Tesseract / preprocessing variants.
        """
        if not text:
            return 0.0
        s = text.strip()
        n = len(s)
        if n < 4:
            return 0.0
        alnum = sum(1 for c in s if c.isalnum())
        mathish = sum(
            1
            for c in s
            if c in "+-*/=()[]{}^'′·•∧∨¬⊕×÷≤≥≠°"
        )
        # Boolean-style identifiers (A, B', etc.)
        boolish = len(re.findall(r"\b[A-Z]\b", s))
        boolish += s.count("A'") + s.count("B'") + s.count("C'")
        words = len(re.findall(r"[A-Za-z]{4,}", s))
        junk = len(re.findall(r"\bee\b|\boo\b|eee|ooo", s.lower()))
        score = 0.38 * (alnum / n)
        score += 0.18 * min(1.0, (mathish / max(n, 1)) * 12.0)
        score += 0.14 * min(1.0, boolish / max(n // 25, 1))
        score += 0.22 * min(1.0, words / max(n // 60, 1))
        score -= 0.15 * min(1.0, junk / max(n // 40, 1))
        return float(max(0.0, min(1.0, score)))

    def _post_filter_scan_lines(self, text: str) -> str:
        """Drop scanner watermarks and border-noise lines (robust to OCR noise)."""
        if not text:
            return text
        out: List[str] = []
        for line in text.splitlines():
            sl = line.strip()
            # Collapse OCR noise (primes / dots / spaces between letters) so brand
            # names still match when an over-eager prime detector sprinkles
            # `c'a'm'sca'n'n'e'r` everywhere.
            normalised = re.sub(r"[^A-Za-z]+", "", sl).lower()
            if normalised and re.search(
                r"(camscanner|scannedwith|adobescan|tinyscanner|microsoftlens|"
                r"geniusscan|scannerapp|notescan|officelens|clearscanner)",
                normalised,
            ):
                continue
            if sl and re.fullmatch(r"[|_\-=\s.·•']+", sl):
                continue
            out.append(line)
        return "\n".join(out).strip()

    def _ocr_page_handwriting(self, image: Image.Image, *, fast: bool = False) -> str:
        """
        Run multiple OCR variants and keep the best-scoring transcript.
        Handwritten math is inherently noisy; ensemble + scoring beats a single pass.

        When a cloud math/handwriting provider is configured (Mathpix etc.) we use it
        as the primary transcription — that is the only realistic way to read student
        handwriting reliably. Local ensemble stays as a fallback so the system still
        works without an API key.
        """
        # ── Cloud math/handwriting OCR (preferred when configured) ────────────
        if self.cloud and self.cloud.active_provider_name:
            try:
                upscaled = self._upscale_for_cloud(image)
                cloud_res = self.cloud.recognize_pil(upscaled)
            except Exception as ex:  # pragma: no cover - network errors
                logger.warning("Cloud OCR failed, falling back to local: %s", ex)
                cloud_res = None
            if cloud_res and cloud_res.text.strip():
                cleaned = self._post_filter_scan_lines(cloud_res.text)
                if cleaned.strip():
                    return cleaned

        # ── Local TrOCR handwriting model (free, USE_TROCR=1) ─────────────────
        # We run it before the EasyOCR / Tesseract ensemble because on real
        # student handwriting it usually wins. If its output is empty or clearly
        # low-quality, we still fall through to the older ensemble.
        # Skipped in `fast` mode (live PDF preview) — TrOCR on CPU is ~seconds per
        # line, which is fine for submission-time grading but too slow for preview.
        trocr_cleaned = ""
        trocr_score = 0.0
        if self.trocr is not None:
            try:
                upscaled = self._upscale_for_cloud(image)  # same target size works well
                # `fast=True` runs the small TrOCR prose model on the first
                # ~14 lines only — fast enough for the live PDF-routing
                # preview while still real handwriting OCR, not Tesseract.
                trocr_text = self.trocr.read_page(upscaled, fast=fast)
            except Exception as ex:  # pragma: no cover - model failure
                logger.warning("TrOCR failed, falling back to local ensemble: %s", ex)
                trocr_text = ""
            if trocr_text.strip():
                trocr_cleaned = self._post_filter_scan_lines(trocr_text)
                if trocr_cleaned.strip():
                    trocr_score = self._ocr_quality_score(trocr_cleaned)
                    # In fast mode there is no ensemble pass to compare against,
                    # so accept the TrOCR result directly and return early.
                    if fast:
                        return trocr_cleaned

        # ── Local ensemble (EasyOCR / Tesseract) ───────────────────────────────
        light = self._light_preprocess(image)
        hc = self._high_contrast_rgb(image)
        soft = self._soft_binarize(image)
        heavy = self._heavy_preprocess(image)
        gray_l = Image.fromarray(self._base_normalise(image), mode="L")

        candidates: List[str] = []
        if self.use_easyocr and self.easyocr_reader:
            t_a = self._run_easyocr(light)
            t_b = self._run_easyocr(hc)
            t_c = self._run_easyocr_math_restricted(light)
            for t in (t_a, t_b, t_c):
                if t.strip():
                    candidates.append(t.strip())

        best_easy = max((self._ocr_quality_score(c) for c in candidates), default=0.0)
        if best_easy < 0.52 or not candidates:
            for img in (soft, heavy, gray_l):
                t = self._run_ocr(img)
                if t.strip():
                    candidates.append(t.strip())

        ensemble_text = ""
        ens_score = 0.0
        if candidates:
            best = max(candidates, key=self._ocr_quality_score)
            ensemble_text = self._post_filter_scan_lines(best)
            if ensemble_text.strip():
                ens_score = self._ocr_quality_score(ensemble_text)

        # Prefer TrOCR when it is clearly good; when it is only mediocre, let the
        # classical ensemble win if it scores noticeably higher (reduces stuck
        # wrong-line crops from the neural line splitter).
        if trocr_cleaned.strip():
            if trocr_score >= 0.48:
                return trocr_cleaned
            if trocr_score >= 0.34 and trocr_score + 0.06 >= ens_score:
                return trocr_cleaned
            if ens_score > trocr_score + 0.07 and ensemble_text.strip():
                return ensemble_text
            return trocr_cleaned

        return ensemble_text

    def _upscale_for_cloud(self, image: Image.Image) -> Image.Image:
        """
        Cloud providers want clean, large images. Mathpix specifically prefers
        ≥ ~1000-1500px on the long edge for handwriting; over ~3000px wastes bytes.
        """
        target = 2600
        if image.width >= target or image.height >= target:
            return image.convert("RGB")
        long_side = max(image.width, image.height)
        scale = target / float(long_side)
        new_size = (int(image.width * scale), int(image.height * scale))
        return image.convert("RGB").resize(new_size, Image.Resampling.LANCZOS)

    # ── Kept for backward compatibility but no longer called ─────────────────

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Legacy wrapper — routes to _heavy_preprocess."""
        return self._heavy_preprocess(image)

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Correct slight rotations using minAreaRect."""
        coords = np.column_stack(np.where(image < 250))
        if coords.size == 0:
            return image

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Only correct small angles (less than 5 degrees) to avoid over-correction
        if abs(angle) > 5:
            return image

        (h, w) = image.shape
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return rotated

    def _run_ocr(self, image: Image.Image) -> str:
        """Run Tesseract on a PIL image."""
        # Ensure image is in grayscale mode (L) for best OCR results
        if image.mode != 'L':
            image = image.convert('L')
        
        # Ensure minimum size for Tesseract (it works better with larger images)
        min_size = 300
        if image.width < min_size or image.height < min_size:
            scale = max(min_size / image.width, min_size / image.height)
            new_size = (int(image.width * scale), int(image.height * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Try OCR with the configured settings first
        try:
            text = pytesseract.image_to_string(
                image, 
                lang=self.tesseract_lang, 
                config=self.tesseract_config
            ).strip()
        except Exception as e:
            # If language fails, try without language specification
            try:
                text = pytesseract.image_to_string(
                    image,
                    config=self.tesseract_config
                ).strip()
            except Exception:
                raise Exception(
                    f"Tesseract OCR failed. Make sure Tesseract is installed and language data is available. "
                    f"Error: {str(e)}. Try installing EasyOCR instead: pip install easyocr"
                )
        
        def _letter_ratio(s: str) -> float:
            if not s:
                return 0.0
            letters = sum(1 for c in s if c.isalnum())
            return letters / len(s)

        # If we got very little text, try alternative PSM modes
        if len(text) < 5:
            # Try single line mode (often better for math)
            alt_configs = [
                f"--oem 3 --psm 7",  # Single line
                f"--oem 3 --psm 8",  # Single word
                f"--oem 3 --psm 11", # Sparse text
                f"--oem 3 --psm 4",  # Single column
            ]

            for alt_config in alt_configs:
                try:
                    alt_text = pytesseract.image_to_string(
                        image,
                        lang=self.tesseract_lang,
                        config=alt_config
                    ).strip()
                    if len(alt_text) > len(text):
                        text = alt_text
                        break
                except Exception:
                    continue
        # Handwriting / noisy scans: long output can still be garbage; try sparse / OSD-free modes
        elif len(text) > 20 and _letter_ratio(text) < 0.35:
            alt_configs = [
                "--oem 3 --psm 11",  # Sparse text (often better for uneven handwriting)
                "--oem 3 --psm 12",  # Sparse with OSD
                "--oem 3 --psm 13",  # Raw line
            ]
            best = text
            best_lr = _letter_ratio(text)
            for alt_config in alt_configs:
                try:
                    alt_text = pytesseract.image_to_string(
                        image,
                        lang=self.tesseract_lang,
                        config=alt_config,
                    ).strip()
                    if not alt_text:
                        continue
                    lr = _letter_ratio(alt_text)
                    if lr > best_lr + 0.05 or (lr >= best_lr and len(alt_text) > len(best) * 1.1):
                        best, best_lr = alt_text, lr
                except Exception:
                    continue
            text = best

        return text
    
    def _run_easyocr(self, image: Image.Image) -> str:
        """Run EasyOCR on a lightly-preprocessed PIL image."""
        if not self.easyocr_reader:
            return self._run_ocr(image)

        if image.mode != 'RGB':
            image = image.convert('RGB')
        np_img = np.array(image)

        # paragraph=False gives finer-grained bounding boxes, better for multi-line
        try:
            results = self.easyocr_reader.readtext(
                np_img,
                paragraph=False,
                mag_ratio=2.0,
                text_threshold=0.55,
                low_text=0.32,
                link_threshold=0.35,
                contrast_ths=0.08,
            )
        except TypeError:
            results = self.easyocr_reader.readtext(np_img, paragraph=False)

        # Collect detected text sorted top-to-bottom by bounding box y-coordinate
        detections = []
        for item in results:
            bbox, text, confidence = item
            if confidence > 0.18 and text.strip():  # permissive for faint handwriting
                # Use the top-left y coordinate for ordering
                top_y = min(pt[1] for pt in bbox)
                detections.append((top_y, text.strip()))

        detections.sort(key=lambda x: x[0])
        text_lines = [t for _, t in detections]

        combined = '\n'.join(text_lines)

        # If EasyOCR returned almost nothing, let the caller fall back to Tesseract
        return combined

    def _run_easyocr_math_restricted(self, image: Image.Image) -> str:
        """
        Extra EasyOCR pass with an allowlist biased toward Latin letters, digits, and math
        punctuation — reduces random symbols / emoji from phone scans.
        """
        if not self.easyocr_reader:
            return ""
        if image.mode != "RGB":
            image = image.convert("RGB")
        np_img = np.array(image)
        # ¬ ∧ ∨ left out (EasyOCR often misreads anyway); instructor can use LaTeX in typed mode
        allow = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            "0123456789=()'+\\-^*/[]{}.,:;|& "
        )
        try:
            results = self.easyocr_reader.readtext(
                np_img,
                paragraph=False,
                allowlist=allow,
                mag_ratio=2.0,
                text_threshold=0.55,
                low_text=0.32,
                link_threshold=0.35,
                contrast_ths=0.08,
            )
        except TypeError:
            try:
                results = self.easyocr_reader.readtext(
                    np_img, paragraph=False, allowlist=allow
                )
            except TypeError:
                return ""

        detections: List[Tuple[float, str]] = []
        for item in results:
            bbox, text, confidence = item
            if confidence > 0.18 and text.strip():
                top_y = min(pt[1] for pt in bbox)
                detections.append((top_y, text.strip()))
        detections.sort(key=lambda x: x[0])
        return "\n".join(t for _, t in detections)

    def _pil_to_png_bytes(self, image: Image.Image) -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.read()

    def _segment_steps(self, text: str) -> List[str]:
        """
        Split raw OCR text into step-sized chunks using heuristics.

        Rules:
        - Blank lines delimit steps.
        - Numbering like "1.", "2)", or "Step 3" starts a new step.
        - Mathematical expressions (containing =, +, -, *, /, ^) are split intelligently.
        - Parentheses patterns help identify separate steps.
        """
        # First, normalize the text
        text = self._normalize_ocr_text(text)
        
        lines = [line.strip() for line in text.splitlines()]
        steps: List[str] = []
        buffer: List[str] = []

        for line in lines:
            if not line:
                self._flush_buffer(buffer, steps)
                continue

            # Check if line contains multiple potential steps (e.g., multiple equations)
            potential_steps = self._split_line_into_steps(line)
            
            if len(potential_steps) > 1:
                # Multiple steps on one line
                self._flush_buffer(buffer, steps)
                steps.extend(potential_steps)
            elif self._looks_like_new_step(line):
                self._flush_buffer(buffer, steps)
                buffer.append(self._strip_step_prefix(line))
            else:
                buffer.append(line)

        self._flush_buffer(buffer, steps)
        return steps

    def _merge_instruction_and_equation_lines(self, steps: List[str]) -> List[str]:
        """
        OCR often returns 'Add 8 to both sides:' and '2x = 18' as separate steps.
        Merge instruction-only lines with the following equation line so grading
        compares full context and SymPy sees '2x = 18'.
        """
        if not steps:
            return steps
        merged: List[str] = []
        i = 0
        while i < len(steps):
            cur = steps[i].strip()
            if i + 1 < len(steps):
                nxt = steps[i + 1].strip()
                has_eq = "=" in nxt
                cur_no_eq = "=" not in cur
                # Instruction line: no '=', often ends with ':' or is short prose
                looks_instruction = cur_no_eq and (
                    cur.endswith(":")
                    or re.match(
                        r"(?i)^(add|subtract|multiply|divide|simplify|factor|expand|combine|substitute|solve|therefore|then|so|hence)\b",
                        cur,
                    )
                )
                if looks_instruction and has_eq:
                    merged.append(f"{cur} {nxt}".strip())
                    i += 2
                    continue
            merged.append(cur)
            i += 1
        return merged

    def _flush_buffer(self, buffer: List[str], steps: List[str]) -> None:
        if buffer:
            steps.append(" ".join(buffer))
            buffer.clear()

    def _looks_like_new_step(self, line: str) -> bool:
        normalized = line.lower()
        if re.match(r"^(step\s*\d+[\.:]?)", normalized):
            return True
        if re.match(r"^\d+[\).\s]", normalized):
            return True
        if re.match(r"^[a-z]\)", normalized):
            return True
        return False

    def _strip_step_prefix(self, line: str) -> str:
        return re.sub(r"^(step\s*\d+[\.:]?|\d+[\).\s]|[a-z]\))\s*", "", line, flags=re.IGNORECASE).strip()
    
    def _normalize_ocr_text(self, text: str) -> str:
        """
        Fix common OCR errors in mathematical expressions.
        - Fix spacing around operators
        - Fix common character misreads (x42 -> x^2, Xx -> x, etc.)
        """
        # Fix spacing around operators (but preserve existing spacing first)
        text = re.sub(r'\s*([=+\-*/^])\s*', r' \1 ', text)
        
        # Fix common OCR errors
        # x42 or x^2 misreads -> x^2 (but be careful not to change x2 in x2 + 3x)
        # Only change if it looks like exponent: x followed by digit at start or after operator
        text = re.sub(r'([+\-*=(\s])x(\d+)', r'\1x^\2', text)
        text = re.sub(r'^x(\d+)', r'x^\1', text)
        
        # Xx -> x (double x, common OCR error)
        text = re.sub(r'Xx', 'x', text)
        text = re.sub(r'XX', 'x', text)
        
        # Fix "or" without spaces: "x=2orx=3" -> "x = 2 or x = 3"
        # Pattern: letter/digit followed by "or" followed by letter
        text = re.sub(r'([a-z0-9])\s*or\s*([a-z])', r'\1 or \2', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d)\s*or\s*(\d)', r'\1 or \2', text)
        
        # Fix missing spaces before/after parentheses in math
        text = re.sub(r'([a-z0-9])\s*\(', r'\1 (', text)
        text = re.sub(r'\)\s*([a-z0-9])', r') \1', text)
        
        # Fix patterns like "+6=0" -> "+ 6 = 0"
        text = re.sub(r'([+\-])(\d+)\s*=', r'\1 \2 =', text)
        
        # Clean up multiple spaces but preserve single spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _split_line_into_steps(self, line: str) -> List[str]:
        """
        Try to split a line that might contain multiple steps.
        Looks for patterns like multiple equations or expressions.
        """
        # Strategy 1: Split on ") = 0" or "= 0" followed by "(" (new expression starts)
        # Pattern: "expression1 = 0 (expression2"
        if re.search(r'=\s*0\s+\(', line):
            parts = re.split(r'(=\s*0)\s+\(', line)
            if len(parts) >= 3:
                steps = []
                # First expression with "= 0"
                first = (parts[0] + parts[1]).strip()
                if first:
                    steps.append(first)
                # Remaining expression(s) starting with "("
                remaining = '(' + ''.join(parts[2:])
                # Recursively split remaining if it has more steps
                if remaining.strip() and '=' in remaining:
                    sub_steps = self._split_line_into_steps(remaining)
                    steps.extend(sub_steps)
                elif remaining.strip():
                    steps.append(remaining.strip())
                if len(steps) > 1:
                    return steps
        
        # Strategy 2: Split on ") = 0" or ") =0" followed by letter (new variable/expression)
        # Pattern: "expression1) = 0 x = ..." or "expression1) = 0 (expression2"
        if re.search(r'\)\s*=\s*0\s+[a-z(]', line, re.IGNORECASE):
            # Find all positions where ") = 0" is followed by letter or "("
            matches = list(re.finditer(r'\)\s*=\s*0\s+(?=[a-z(])', line, re.IGNORECASE))
            if len(matches) > 0:
                split_points = [0]
                for match in matches:
                    # Position after ") = 0"
                    split_points.append(match.end())
                split_points.append(len(line))
                
                steps = []
                for i in range(len(split_points) - 1):
                    step = line[split_points[i]:split_points[i+1]].strip()
                    if step and '=' in step:
                        steps.append(step)
                if len(steps) > 1:
                    return steps
        
        # Strategy 3: If line has multiple "=" and is long, try splitting on natural breaks
        # Look for pattern: expression ending, then space, then new expression starting with letter
        if len(line) > 30 and line.count('=') >= 2:
            # Try to find where one complete expression ends
            # Look for ") = " or " = " patterns where what follows looks like start of new expr
            # Pattern: digit/letter followed by space, then letter (new variable)
            # But only if there's an "=" before it
            potential_splits = []
            # Look for ") = 0" or ") = number" followed by space and letter
            for match in re.finditer(r'\)\s*=\s*\d+\s+(?=[a-z])', line, re.IGNORECASE):
                potential_splits.append(match.end())
            
            if potential_splits:
                potential_splits.insert(0, 0)
                potential_splits.append(len(line))
                steps = []
                for i in range(len(potential_splits) - 1):
                    step = line[potential_splits[i]:potential_splits[i+1]].strip()
                    if step and '=' in step:
                        steps.append(step)
                if len(steps) > 1:
                    return steps
        
        # If no clear split pattern, return as single step
        return [line] if line.strip() else []

