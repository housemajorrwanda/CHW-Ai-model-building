"""
Hybrid OCR Processor - Automatically chooses between text and math OCR
Intelligently detects content type and uses appropriate model
"""
import logging
from typing import Union, Dict, List
from PIL import Image
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.ocr_processor import HandwritingOCR
from src.math_ocr_processor import MathOCR, detect_math_content
from src.utils import load_image
import config

logger = logging.getLogger(__name__)


class HybridOCR:
    """
    Hybrid OCR system that automatically detects content type
    and uses the appropriate specialized model.
    """
    
    def __init__(self,
                 device: str = None,
                 preprocess: bool = None,
                 enable_math: bool = True,
                 auto_detect: bool = True):
        """
        Initialize Hybrid OCR system.
        
        Args:
            device: Device to use ('cuda', 'cpu', or None for auto)
            preprocess: Enable preprocessing
            enable_math: Enable math OCR model
            auto_detect: Auto-detect content type (if False, always use text OCR)
        """
        self.device = device or config.DEVICE
        self.preprocess_enabled = preprocess if preprocess is not None else config.ENABLE_PREPROCESSING
        self.enable_math = enable_math
        self.auto_detect = auto_detect
        
        logger.info("\n" + "=" * 70)
        logger.info("INITIALIZING HYBRID OCR SYSTEM")
        logger.info("=" * 70)
        
        # Initialize text OCR
        logger.info("\n[1/2] Loading Text OCR Model...")
        self.text_ocr = HandwritingOCR(
            device=self.device,
            preprocess=self.preprocess_enabled
        )
        
        # Initialize math OCR if enabled
        if self.enable_math:
            logger.info("\n[2/2] Loading Math OCR Model...")
            try:
                self.math_ocr = MathOCR(
                    device=self.device,
                    preprocess=self.preprocess_enabled
                )
                logger.info("✓ Math OCR enabled")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load Math OCR: {e}")
                logger.warning("Falling back to text-only mode")
                self.enable_math = False
                self.math_ocr = None
        else:
            self.math_ocr = None
            logger.info("Math OCR disabled - using text-only mode")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ HYBRID OCR SYSTEM READY")
        logger.info("=" * 70)
        logger.info(f"  Text OCR: Enabled")
        logger.info(f"  Math OCR: {'Enabled' if self.enable_math else 'Disabled'}")
        logger.info(f"  Auto-detect: {'Enabled' if self.auto_detect else 'Disabled'}")
        logger.info("=" * 70 + "\n")
    
    def process_image(self,
                     image_path: str,
                     force_mode: str = None,
                     return_details: bool = False) -> Union[str, Dict]:
        """
        Process image with automatic model selection.
        
        Args:
            image_path: Path to image
            force_mode: Force specific mode ('text' or 'math'), None for auto
            return_details: Return detailed results with model used
            
        Returns:
            Extracted text or dict with details
        """
        try:
            # Determine which model to use
            if force_mode:
                use_math = (force_mode == 'math')
                detection_method = 'forced'
            elif self.auto_detect and self.enable_math:
                # Try text OCR first for quick detection
                text_result = self.text_ocr.process_image(image_path)
                use_math = detect_math_content(text_result)
                detection_method = 'auto-detected'
            else:
                use_math = False
                detection_method = 'default'
            
            # Process with appropriate model
            if use_math and self.math_ocr:
                logger.info(f"📐 Using MATH OCR ({detection_method})")
                result_text = self.math_ocr.process_image(image_path)
                model_used = 'math'
            else:
                logger.info(f"📝 Using TEXT OCR ({detection_method})")
                if self.auto_detect and 'text_result' in locals():
                    result_text = text_result  # Use already processed result
                else:
                    result_text = self.text_ocr.process_image(image_path)
                model_used = 'text'
            
            if return_details:
                return {
                    'text': result_text,
                    'model_used': model_used,
                    'detection_method': detection_method,
                    'length': len(result_text)
                }
            
            return result_text
            
        except Exception as e:
            logger.error(f"✗ Hybrid OCR failed: {e}")
            raise
    
    def process_with_both(self, image_path: str) -> Dict:
        """
        Process image with BOTH models and return comparison.
        Useful for testing and accuracy comparison.
        
        Args:
            image_path: Path to image
            
        Returns:
            Dict with results from both models
        """
        logger.info("\n" + "=" * 70)
        logger.info("PROCESSING WITH BOTH MODELS FOR COMPARISON")
        logger.info("=" * 70 + "\n")
        
        results = {}
        
        # Process with text OCR
        try:
            logger.info("[1/2] Processing with TEXT OCR...")
            text_result = self.text_ocr.process_image(image_path)
            results['text_ocr'] = {
                'text': text_result,
                'status': 'success',
                'length': len(text_result)
            }
            logger.info(f"✓ Text OCR result: {text_result}")
        except Exception as e:
            results['text_ocr'] = {
                'text': None,
                'status': 'error',
                'error': str(e)
            }
            logger.error(f"✗ Text OCR failed: {e}")
        
        # Process with math OCR
        if self.enable_math and self.math_ocr:
            try:
                logger.info("\n[2/2] Processing with MATH OCR...")
                math_result = self.math_ocr.process_image(image_path)
                results['math_ocr'] = {
                    'text': math_result,
                    'status': 'success',
                    'length': len(math_result)
                }
                logger.info(f"✓ Math OCR result: {math_result}")
            except Exception as e:
                results['math_ocr'] = {
                    'text': None,
                    'status': 'error',
                    'error': str(e)
                }
                logger.error(f"✗ Math OCR failed: {e}")
        else:
            results['math_ocr'] = {
                'text': None,
                'status': 'disabled',
                'error': 'Math OCR not enabled'
            }
        
        # Add recommendation
        if results['text_ocr']['status'] == 'success' and results['math_ocr']['status'] == 'success':
            text_content = results['text_ocr']['text']
            if detect_math_content(text_content):
                results['recommendation'] = 'Use MATH OCR (math content detected)'
            else:
                results['recommendation'] = 'Use TEXT OCR (no math detected)'
        
        logger.info("\n" + "=" * 70)
        logger.info("COMPARISON COMPLETE")
        logger.info("=" * 70 + "\n")
        
        return results
    
    def get_system_info(self) -> Dict:
        """Get information about hybrid system."""
        info = {
            'mode': 'hybrid',
            'text_ocr': self.text_ocr.get_model_info(),
            'math_ocr_enabled': self.enable_math,
            'auto_detect_enabled': self.auto_detect,
            'device': self.device
        }
        
        if self.math_ocr:
            info['math_ocr'] = self.math_ocr.get_model_info()
        
        return info

