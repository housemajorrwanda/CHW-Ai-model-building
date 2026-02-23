import io
import re
from dataclasses import dataclass
from typing import List, Sequence, Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps, ImageFilter
from pdf2image import convert_from_bytes

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


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

    def extract_steps_from_file(self, file_bytes: bytes, filename: str) -> OCRResult:
        """
        Extract answer steps from an image or PDF file.

        For PDFs: tries direct text extraction first (perfect for typed answers).
        Falls back to image-based OCR when the PDF is scanned / handwritten.
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
            elif self.use_easyocr:
                light = self._light_preprocess(image)
                previews.append(self._pil_to_png_bytes(light))
                text = self._run_easyocr(light)
                if len(text.strip()) < 4:
                    heavy = self._heavy_preprocess(image)
                    text = self._run_ocr(heavy)
            else:
                heavy = self._heavy_preprocess(image)
                previews.append(self._pil_to_png_bytes(heavy))
                text = self._run_ocr(heavy)

            combined_text.append(text.strip())
            extracted_steps.extend(self._segment_steps(text))

        steps = [step for step in (s.strip() for s in extracted_steps) if step]
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

        # Upscale images that are too small for reliable OCR
        min_width = 1200
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
                except:
                    continue
        
        return text
    
    def _run_easyocr(self, image: Image.Image) -> str:
        """Run EasyOCR on a lightly-preprocessed PIL image."""
        if not self.easyocr_reader:
            return self._run_ocr(image)

        if image.mode != 'RGB':
            image = image.convert('RGB')
        np_img = np.array(image)

        # paragraph=False gives finer-grained bounding boxes, better for multi-line
        results = self.easyocr_reader.readtext(np_img, paragraph=False)

        # Collect detected text sorted top-to-bottom by bounding box y-coordinate
        detections = []
        for item in results:
            bbox, text, confidence = item
            if confidence > 0.2 and text.strip():    # lower threshold for handwriting
                # Use the top-left y coordinate for ordering
                top_y = min(pt[1] for pt in bbox)
                detections.append((top_y, text.strip()))

        detections.sort(key=lambda x: x[0])
        text_lines = [t for _, t in detections]

        combined = '\n'.join(text_lines)

        # If EasyOCR returned almost nothing, let the caller fall back to Tesseract
        return combined

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

