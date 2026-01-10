"""
OCR Module - Contains all OCR processing implementations
"""

# Current active OCR (Tesseract + EasyOCR)
from .ocr_pipeline import OCRProcessor, OCRResult

# Additional OCR implementations (for future use/research)
# from .trocr_processor import HandwritingOCR
# from .math_trocr_processor import MathOCR
# from .hybrid_processor import HybridOCR

__all__ = [
    'OCRProcessor',
    'OCRResult',
    # 'HandwritingOCR',
    # 'MathOCR',
    # 'HybridOCR',
]

