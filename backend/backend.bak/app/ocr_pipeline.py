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

    def extract_steps_from_file(self, file_bytes: bytes, filename: str) -> OCRResult:
        """High-level helper for any supported document type."""
        images = self._load_pages(file_bytes, filename)
        if not images:
            return OCRResult("", [], 0, [])

        combined_text: List[str] = []
        extracted_steps: List[str] = []
        previews: List[bytes] = []

        for image in images:
            processed = self._preprocess_image(image)
            previews.append(self._pil_to_png_bytes(processed))
            
            # Try EasyOCR first if available (better for handwriting and rotation)
            if self.use_easyocr:
                text = self._run_easyocr(processed)
            else:
                text = self._run_ocr(processed)
            
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

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Enhance the image to improve OCR results."""
        grayscale = ImageOps.grayscale(image)
        grayscale = ImageOps.autocontrast(grayscale)

        # Upscale low-resolution images for better OCR accuracy
        min_width = 1200
        if grayscale.width < min_width:
            scale = min_width / grayscale.width
            grayscale = grayscale.resize(
                (int(grayscale.width * scale), int(grayscale.height * scale)),
                Image.Resampling.LANCZOS,
            )

        np_img = np.array(grayscale)

        # Check and fix inversion FIRST (before any processing)
        # If image is mostly dark (inverted), flip it
        mean_brightness = np.mean(np_img)
        if mean_brightness < 128:  # More dark than light = likely inverted
            np_img = 255 - np_img

        # Auto-rotate image to correct orientation (0, 90, 180, 270 degrees)
        np_img = self._auto_orient_image(np_img)

        # Enhance contrast first (CLAHE - Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        np_img = clahe.apply(np_img)

        # Denoise while preserving edges (lighter denoising for handwriting)
        np_img = cv2.fastNlMeansDenoising(
            np_img, None, h=10, templateWindowSize=7, searchWindowSize=21
        )

        # Deskew image to correct tilted writing
        np_img = self._deskew(np_img)

        # Try multiple preprocessing strategies and pick the best one
        # Strategy 1: Otsu's threshold (good for clear images)
        _, thresh1 = cv2.threshold(np_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Strategy 2: Adaptive threshold (good for uneven lighting)
        thresh2 = cv2.adaptiveThreshold(
            np_img,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,  # Smaller block size for handwriting
            8,   # Slightly higher C value
        )
        
        # Strategy 3: Morphological operations to strengthen thin strokes
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(thresh2, kernel, iterations=1)
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # Use the closed version (strategy 3) as it's best for handwriting
        # Sharpen using unsharp mask
        blurred = cv2.GaussianBlur(closed, (0, 0), sigmaX=0.5)
        sharpened = cv2.addWeighted(closed, 2.0, blurred, -1.0, 0)
        
        # Ensure we have proper contrast
        # Invert to match Tesseract expectation (black text on white background)
        inverted = cv2.bitwise_not(sharpened)
        
        # Final cleanup: remove small noise
        kernel_clean = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, kernel_clean, iterations=1)
        
        # Double-check inversion (should already be fixed, but verify)
        # Count pixels: if more dark pixels, image is likely inverted
        dark_pixels = np.sum(cleaned < 128)
        total_pixels = cleaned.size
        if dark_pixels > total_pixels * 0.6:  # More than 60% dark = likely inverted
            cleaned = cv2.bitwise_not(cleaned)
        
        # Ensure proper data type and convert to PIL Image in grayscale mode
        cleaned = np.clip(cleaned, 0, 255).astype(np.uint8)
        pil_image = Image.fromarray(cleaned, mode='L')
        
        return pil_image

    def _auto_orient_image(self, image: np.ndarray) -> np.ndarray:
        """
        Auto-rotate image to correct orientation (0, 90, 180, 270 degrees).
        Uses aggressive heuristics for rotation detection.
        """
        h, w = image.shape
        
        # Aggressive heuristic: If image is taller than wide, rotate it
        # Math equations are almost always wider than tall
        if h > w * 1.1:  # Even slight portrait orientation
            # Rotate 90° clockwise
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            h, w = w, h  # Update dimensions
        
        # Try all 4 orientations and pick the one with best horizontal text distribution
        orientations = [
            (0, image),
            (90, cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)),
            (180, cv2.rotate(image, cv2.ROTATE_180)),
            (270, cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)),
        ]
        
        best_image = image
        best_score = 0
        
        for angle, rotated in orientations:
            # Calculate horizontal projection variance (higher = more horizontal text)
            h_proj = np.sum(rotated, axis=0)
            v_proj = np.sum(rotated, axis=1)
            
            # Score based on: high horizontal variance, low vertical variance
            h_var = np.var(h_proj)
            v_var = np.var(v_proj)
            
            # Prefer wider images with strong horizontal text lines
            aspect_ratio = rotated.shape[1] / max(rotated.shape[0], 1)
            score = h_var * aspect_ratio / max(v_var, 1)
            
            if score > best_score:
                best_score = score
                best_image = rotated
        
        return best_image

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
        """Run EasyOCR on a PIL image. Better for handwriting and rotated text."""
        if not self.easyocr_reader:
            # Fallback to Tesseract if EasyOCR not available
            return self._run_ocr(image)
        
        # Convert PIL to numpy array
        if image.mode != 'RGB':
            image = image.convert('RGB')
        np_img = np.array(image)
        
        # EasyOCR handles rotation automatically, so we can pass the image directly
        # But we still want to use our preprocessed version
        results = self.easyocr_reader.readtext(np_img)
        
        # Combine all detected text
        text_lines = []
        for (bbox, text, confidence) in results:
            if confidence > 0.3:  # Filter low confidence detections
                text_lines.append(text)
        
        return '\n'.join(text_lines)

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

