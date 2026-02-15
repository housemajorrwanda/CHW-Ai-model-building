"""
TrOCR Exam Grading System
A modern handwriting recognition system for exam grading
"""

__version__ = '1.0.0'
__author__ = 'Exam Grading System'

from .ocr_processor import HandwritingOCR
from .math_ocr_processor import MathOCR
from .hybrid_ocr_processor import HybridOCR
from .image_preprocessor import ImagePreprocessor
from .utils import (
    load_image,
    save_text,
    get_image_files,
    format_results
)

__all__ = [
    'HandwritingOCR',
    'MathOCR',
    'HybridOCR',
    'ImagePreprocessor',
    'load_image',
    'save_text',
    'get_image_files',
    'format_results'
]

