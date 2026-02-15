"""
TrOCR Processor - Main OCR engine using Microsoft's TrOCR model
"""
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import logging
from typing import List, Dict, Union, Optional
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.image_preprocessor import ImagePreprocessor
from src.utils import (
    load_image, save_text, save_json, save_csv,
    get_image_files, create_output_filename, ensure_directory,
    clean_text, get_timestamp
)
import config

logger = logging.getLogger(__name__)


class HandwritingOCR:
    """
    Main OCR processor using Microsoft's TrOCR model.
    Handles single image and batch processing of handwritten text.
    """
    
    def __init__(self,
                 model_name: str = None,
                 device: str = None,
                 preprocess: bool = None,
                 **preprocess_kwargs):
        """
        Initialize TrOCR Processor.
        
        Args:
            model_name: HuggingFace model name (default: from config)
            device: Device to run on ('cuda', 'cpu', or None for auto)
            preprocess: Enable image preprocessing (default: from config)
            **preprocess_kwargs: Additional preprocessing arguments
        """
        # Set defaults from config if not provided
        self.model_name = model_name or config.MODEL_NAME
        self.device = device or config.DEVICE
        self.preprocess_enabled = preprocess if preprocess is not None else config.ENABLE_PREPROCESSING
        
        logger.info("=" * 70)
        logger.info("Initializing TrOCR Processor")
        logger.info("=" * 70)
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Device: {self.device.upper()}")
        logger.info(f"Preprocessing: {'Enabled' if self.preprocess_enabled else 'Disabled'}")
        
        # Load model and processor
        self._load_model()
        
        # Initialize image preprocessor if enabled
        if self.preprocess_enabled:
            preprocess_config = {
                'denoise': preprocess_kwargs.get('denoise', config.DENOISE),
                'enhance_contrast': preprocess_kwargs.get('enhance_contrast', config.ENHANCE_CONTRAST),
                'auto_rotate': preprocess_kwargs.get('auto_rotate', config.AUTO_ROTATE),
                'remove_borders': preprocess_kwargs.get('remove_borders', config.REMOVE_BORDERS),
                'binarize': preprocess_kwargs.get('binarize', config.BINARIZE)
            }
            self.preprocessor = ImagePreprocessor(**preprocess_config)
        else:
            self.preprocessor = None
        
        logger.info("=" * 70)
        logger.info("✓ TrOCR Processor ready!")
        logger.info("=" * 70 + "\n")
    
    def _load_model(self):
        """Load TrOCR model and processor from HuggingFace."""
        try:
            logger.info(f"Loading model: {self.model_name}")
            logger.info("(First time will download ~1GB, please wait...)")
            
            # Load processor (tokenizer + feature extractor)
            self.processor = TrOCRProcessor.from_pretrained(
                self.model_name,
                cache_dir=config.CACHE_DIR
            )
            
            # Load model
            self.model = VisionEncoderDecoderModel.from_pretrained(
                self.model_name,
                cache_dir=config.CACHE_DIR
            )
            
            # Move model to device
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            logger.info(f"✓ Model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"✗ Failed to load model: {e}")
            logger.error("Make sure you have internet connection for first-time model download")
            raise
    
    def process_image(self, image_path: str, return_confidence: bool = False) -> Union[str, Dict]:
        """
        Process a single image and extract text.
        
        Args:
            image_path: Path to the image file
            return_confidence: Return confidence scores along with text
            
        Returns:
            Extracted text string, or dict with text and confidence
        """
        try:
            logger.info(f"Processing image: {image_path}")
            
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
            
            # Extract text
            text = self._extract_text_from_image(image)
            
            # Clean text
            if config.REMOVE_EXTRA_SPACES or config.REMOVE_EMPTY_LINES:
                text = clean_text(
                    text,
                    remove_extra_spaces=config.REMOVE_EXTRA_SPACES,
                    remove_empty_lines=config.REMOVE_EMPTY_LINES,
                    strip_whitespace=config.STRIP_WHITESPACE
                )
            
            logger.info(f"✓ Successfully extracted text ({len(text)} characters)")
            
            if return_confidence:
                return {
                    'text': text,
                    'confidence': None,  # TrOCR doesn't provide direct confidence scores
                    'length': len(text)
                }
            
            return text
            
        except Exception as e:
            logger.error(f"✗ Failed to process image {image_path}: {e}")
            raise
    
    def _extract_text_from_image(self, image: Image.Image) -> str:
        """
        Extract text from PIL Image using TrOCR model.
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted text
        """
        try:
            # Prepare image for model
            pixel_values = self.processor(
                images=image,
                return_tensors="pt"
            ).pixel_values
            
            # Move to device
            pixel_values = pixel_values.to(self.device)
            
            # Generate text
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    max_length=config.MAX_LENGTH,
                    num_beams=config.NUM_BEAMS,
                    early_stopping=config.EARLY_STOPPING
                )
            
            # Decode generated text
            generated_text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise
    
    def process_batch(self,
                     image_paths: List[str],
                     output_dir: str = None,
                     save_output: bool = True,
                     output_format: str = 'txt') -> List[Dict]:
        """
        Process multiple images in batch.
        
        Args:
            image_paths: List of image file paths
            output_dir: Directory to save outputs (default: data/output)
            save_output: Whether to save outputs to files
            output_format: Output format ('txt', 'json', 'csv')
            
        Returns:
            List of results with format:
            [{'file': path, 'status': 'success/error', 'text': text, 'error': error_msg}]
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'output')
        
        ensure_directory(output_dir)
        
        results = []
        total = len(image_paths)
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"BATCH PROCESSING: {total} images")
        logger.info(f"{'=' * 70}\n")
        
        for idx, image_path in enumerate(image_paths, 1):
            logger.info(f"[{idx}/{total}] Processing: {Path(image_path).name}")
            
            result = {
                'file': image_path,
                'filename': Path(image_path).name,
                'status': 'success',
                'text': '',
                'error': None,
                'timestamp': get_timestamp()
            }
            
            try:
                # Process image
                text = self.process_image(image_path)
                result['text'] = text
                result['length'] = len(text)
                
                # Save output if requested
                if save_output:
                    output_path = create_output_filename(
                        image_path,
                        output_dir,
                        suffix='_extracted',
                        extension=output_format
                    )
                    
                    if output_format == 'txt':
                        save_text(text, output_path)
                    elif output_format == 'json':
                        save_json(result, output_path)
                    
                    result['output_file'] = output_path
                
            except Exception as e:
                result['status'] = 'error'
                result['error'] = str(e)
                logger.error(f"✗ Error processing {Path(image_path).name}: {e}")
            
            results.append(result)
        
        # Save summary
        if save_output:
            summary_path = os.path.join(output_dir, f'summary_{get_timestamp()}.json')
            save_json({
                'total_processed': total,
                'successful': sum(1 for r in results if r['status'] == 'success'),
                'failed': sum(1 for r in results if r['status'] == 'error'),
                'results': results
            }, summary_path)
            
            logger.info(f"\n✓ Summary saved to: {summary_path}")
        
        # Print summary
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'error')
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"BATCH PROCESSING COMPLETE")
        logger.info(f"{'=' * 70}")
        logger.info(f"Total: {total} | Success: {successful} | Failed: {failed}")
        logger.info(f"{'=' * 70}\n")
        
        return results
    
    def process_directory(self,
                         input_dir: str,
                         output_dir: str = None,
                         recursive: bool = False,
                         **kwargs) -> List[Dict]:
        """
        Process all images in a directory.
        
        Args:
            input_dir: Input directory containing images
            output_dir: Output directory for results
            recursive: Search subdirectories recursively
            **kwargs: Additional arguments for process_batch
            
        Returns:
            List of results
        """
        logger.info(f"Searching for images in: {input_dir}")
        
        # Get all image files
        image_files = get_image_files(input_dir, config.SUPPORTED_IMAGE_FORMATS)
        
        if not image_files:
            logger.warning(f"No images found in {input_dir}")
            return []
        
        # Process batch
        return self.process_batch(image_files, output_dir=output_dir, **kwargs)
    
    def process_pdf(self, pdf_path: str, output_dir: str = None, **kwargs) -> str:
        """
        Process a PDF file (converts to images first).
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory
            **kwargs: Additional processing arguments
            
        Returns:
            Combined extracted text from all pages
        """
        try:
            from pdf2image import convert_from_path
            
            logger.info(f"Converting PDF to images: {pdf_path}")
            
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            
            logger.info(f"PDF has {len(images)} pages")
            
            # Process each page
            all_text = []
            for idx, image in enumerate(images, 1):
                logger.info(f"Processing page {idx}/{len(images)}")
                text = self._extract_text_from_image(image)
                all_text.append(f"--- Page {idx} ---\n{text}\n")
            
            combined_text = "\n\n".join(all_text)
            
            # Save if output_dir provided
            if output_dir:
                ensure_directory(output_dir)
                output_path = create_output_filename(
                    pdf_path,
                    output_dir,
                    suffix='_extracted',
                    extension='txt'
                )
                save_text(combined_text, output_path)
            
            return combined_text
            
        except ImportError:
            logger.error("pdf2image not installed. Install with: pip install pdf2image")
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF: {e}")
            raise
    
    def get_model_info(self) -> Dict:
        """
        Get information about loaded model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.model_name,
            'device': self.device,
            'preprocessing_enabled': self.preprocess_enabled,
            'model_size_mb': sum(p.numel() * p.element_size() for p in self.model.parameters()) / (1024 * 1024),
            'total_parameters': sum(p.numel() for p in self.model.parameters())
        }

