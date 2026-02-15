"""
Math OCR Processor - Specialized for mathematical equations
Uses TrOCR fine-tuned on mathematical handwriting
"""
import ssl
import os
import urllib3

# Fix SSL certificate issues BEFORE importing transformers
# This must be done before any HTTPS requests
try:
    import certifi
    cert_path = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    os.environ['SSL_CERT_FILE'] = cert_path
    os.environ['CURL_CA_BUNDLE'] = cert_path
except:
    pass

# Disable SSL verification as fallback for macOS
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import logging
from typing import Union, Dict, List
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.image_preprocessor import ImagePreprocessor
from src.utils import load_image
import config

# Import converters (with fallback if not available)
try:
    from src.latex_converter import LaTeXConverter
    LATEX_CONVERTER_AVAILABLE = True
except ImportError:
    LATEX_CONVERTER_AVAILABLE = False

try:
    from src.step_parser import StepParser
    STEP_PARSER_AVAILABLE = True
except ImportError:
    STEP_PARSER_AVAILABLE = False

logger = logging.getLogger(__name__)


class MathOCR:
    """
    Specialized OCR processor for mathematical equations.
    Uses TrOCR fine-tuned on mathematical handwriting.
    """
    
    # Available math OCR models
    MODELS = {
        'trocr-math': 'fhswf/TrOCR_Math_handwritten',  # 77.8% accuracy on math
        'trocr-math-base': 'fhswf/TrOCR_Math_printed',  # For printed math
    }
    
    def __init__(self,
                 model_type: str = 'trocr-math',
                 device: str = None,
                 preprocess: bool = True):
        """
        Initialize Math OCR Processor.
        
        Args:
            model_type: Type of math model ('trocr-math' or 'trocr-math-base')
            device: Device to run on ('cuda', 'cpu', or None for auto)
            preprocess: Enable image preprocessing
        """
        self.model_type = model_type
        self.model_name = self.MODELS.get(model_type, self.MODELS['trocr-math'])
        self.device = device or config.DEVICE
        self.preprocess_enabled = preprocess
        
        logger.info("=" * 70)
        logger.info("Initializing Math OCR Processor")
        logger.info("=" * 70)
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Device: {self.device.upper()}")
        logger.info(f"Preprocessing: {'Enabled' if self.preprocess_enabled else 'Disabled'}")
        
        # Load model
        self._load_model()
        
        # Initialize preprocessor if enabled
        if self.preprocess_enabled:
            self.preprocessor = ImagePreprocessor(
                denoise=True,
                enhance_contrast=True,
                auto_rotate=False,  # Don't rotate math equations
                remove_borders=True,
                binarize=False
            )
        else:
            self.preprocessor = None
        
        logger.info("✓ Math OCR Processor ready!")
        logger.info("=" * 70 + "\n")
    
    def _load_model(self):
        """Load math TrOCR model from HuggingFace."""
        try:
            logger.info(f"Loading math model: {self.model_name}")
            logger.info("(First time will download model, please wait...)")
            
            # Handle SSL certificate issues on macOS
            import ssl
            import os
            import urllib3
            
            # Disable SSL verification warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Try to use certifi certificates if available
            try:
                import certifi
                cert_path = certifi.where()
                os.environ['REQUESTS_CA_BUNDLE'] = cert_path
                os.environ['SSL_CERT_FILE'] = cert_path
                os.environ['CURL_CA_BUNDLE'] = cert_path
                
                # Create SSL context with certifi
                ssl_context = ssl.create_default_context(cafile=cert_path)
                ssl._create_default_https_context = ssl._create_unverified_context
            except:
                # If certifi fails, disable SSL verification as fallback
                logger.warning("SSL certificate issue detected. Using workaround...")
                os.environ['CURL_CA_BUNDLE'] = ''
                os.environ['REQUESTS_CA_BUNDLE'] = ''
                os.environ['SSL_CERT_FILE'] = ''
                # Disable SSL verification
                ssl._create_default_https_context = ssl._create_unverified_context
            
            # Also set for requests library
            import requests
            requests.packages.urllib3.disable_warnings()
            
            # Load processor with SSL verification disabled
            self.processor = TrOCRProcessor.from_pretrained(
                self.model_name,
                cache_dir=config.CACHE_DIR,
                trust_remote_code=True,
                local_files_only=False
            )
            
            # Load model with SSL verification disabled
            self.model = VisionEncoderDecoderModel.from_pretrained(
                self.model_name,
                cache_dir=config.CACHE_DIR,
                trust_remote_code=True,
                local_files_only=False
            )
            
            # Move to device
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"✓ Math model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"✗ Failed to load math model: {e}")
            logger.error("Possible solutions:")
            logger.error("1. Install certificates: pip install certifi")
            logger.error("2. Run: /Applications/Python\\ 3.*/Install\\ Certificates.command")
            logger.error("3. Check internet connection")
            logger.error("4. Use 'Type Manually' option instead of OCR")
            raise
    
    def process_image(self, 
                     image_path: str, 
                     return_latex: bool = False,
                     convert_latex: bool = True,
                     parse_steps: bool = True) -> Union[str, List[str], Dict]:
        """
        Process image with mathematical content.
        
        Args:
            image_path: Path to image with math equation
            return_latex: Whether to return LaTeX format (if available)
            convert_latex: Automatically convert LaTeX to readable math
            parse_steps: Automatically parse into separate steps
            
        Returns:
            Recognized mathematical expression(s) - string, list of steps, or dict
        """
        try:
            logger.info(f"Processing math equation: {image_path}")
            
            # Load image
            image = load_image(image_path)
            
            # Preprocess if enabled
            if self.preprocessor:
                image = self.preprocessor.preprocess(image)
                image = self.preprocessor.resize_if_needed(
                    image,
                    max_width=config.MAX_IMAGE_WIDTH,
                    max_height=config.MAX_IMAGE_HEIGHT
                )
            
            # Extract math expression (may be LaTeX)
            math_text = self._extract_math(image)
            original_text = math_text
            
            logger.info(f"✓ Recognized math (raw): {math_text}")
            
            # Convert LaTeX to readable math if needed
            if convert_latex and LATEX_CONVERTER_AVAILABLE:
                converter = LaTeXConverter()
                if converter.is_latex(math_text):
                    math_text = converter.convert(math_text)
                    logger.info(f"✓ Converted LaTeX to math: {math_text}")
            
            # Parse into steps if requested
            if parse_steps and STEP_PARSER_AVAILABLE:
                parser = StepParser()
                steps = parser.parse(math_text)
                
                if len(steps) > 1:
                    logger.info(f"✓ Parsed into {len(steps)} steps")
                    if return_latex:
                        return {
                            'original_latex': original_text,
                            'converted_math': math_text,
                            'steps': steps,
                            'step_count': len(steps)
                        }
                    return steps
                else:
                    logger.info("✓ Single step detected")
            
            # Return single string
            if return_latex:
                return {
                    'original_latex': original_text,
                    'converted_math': math_text,
                    'steps': [math_text],
                    'step_count': 1
                }
            
            return math_text
            
        except Exception as e:
            logger.error(f"✗ Failed to process math equation: {e}")
            raise
    
    def _extract_math(self, image: Image.Image) -> str:
        """
        Extract mathematical expression from image.
        
        Args:
            image: PIL Image with math content
            
        Returns:
            Recognized math expression
        """
        try:
            # Prepare image
            pixel_values = self.processor(
                images=image,
                return_tensors="pt"
            ).pixel_values
            
            # Move to device
            pixel_values = pixel_values.to(self.device)
            
            # Generate output
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    max_length=config.MAX_LENGTH,
                    num_beams=config.NUM_BEAMS,
                    early_stopping=config.EARLY_STOPPING
                )
            
            # Decode
            generated_text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Math extraction failed: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """Get information about loaded model."""
        return {
            'model_name': self.model_name,
            'model_type': self.model_type,
            'device': self.device,
            'preprocessing_enabled': self.preprocess_enabled,
            'specialization': 'Mathematical Handwriting'
        }


def detect_math_content(text: str) -> bool:
    """
    Simple heuristic to detect if text contains mathematical content.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if likely contains math
    """
    math_indicators = [
        '=', '+', '-', '*', '/', '^', '√',
        '∫', '∑', '∏', 'π', '±', '≤', '≥',
        '(', ')', '[', ']', '{', '}',
        'sin', 'cos', 'tan', 'log', 'ln',
        'lim', 'dx', 'dy', 'dt'
    ]
    
    # Count math symbols
    math_count = sum(1 for indicator in math_indicators if indicator in text.lower())
    
    # If more than 20% of indicators present, likely math
    return math_count >= 2

