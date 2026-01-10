"""
Utility functions for TrOCR Exam Grading System
"""
import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Union
from datetime import datetime
from PIL import Image
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_image(image_path: str) -> Image.Image:
    """
    Load an image from file path.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        PIL Image object
    """
    try:
        image = Image.open(image_path).convert('RGB')
        logger.info(f"✓ Loaded image: {image_path}")
        return image
    except Exception as e:
        logger.error(f"✗ Failed to load image {image_path}: {e}")
        raise


def save_text(text: str, output_path: str, encoding: str = 'utf-8') -> None:
    """
    Save extracted text to file.
    
    Args:
        text: Text to save
        output_path: Path to output file
        encoding: Text encoding (default: utf-8)
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(text)
        
        logger.info(f"✓ Saved text to: {output_path}")
    except Exception as e:
        logger.error(f"✗ Failed to save text to {output_path}: {e}")
        raise


def save_json(data: Dict, output_path: str) -> None:
    """
    Save data as JSON.
    
    Args:
        data: Dictionary to save
        output_path: Path to output JSON file
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Saved JSON to: {output_path}")
    except Exception as e:
        logger.error(f"✗ Failed to save JSON to {output_path}: {e}")
        raise


def save_csv(data: List[Dict], output_path: str) -> None:
    """
    Save data as CSV.
    
    Args:
        data: List of dictionaries to save
        output_path: Path to output CSV file
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if not data:
            logger.warning("No data to save to CSV")
            return
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"✓ Saved CSV to: {output_path}")
    except Exception as e:
        logger.error(f"✗ Failed to save CSV to {output_path}: {e}")
        raise


def get_image_files(directory: str, supported_formats: List[str] = None) -> List[str]:
    """
    Get all image files from a directory.
    
    Args:
        directory: Directory to search
        supported_formats: List of supported file extensions
        
    Returns:
        List of image file paths
    """
    if supported_formats is None:
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    
    image_files = []
    
    if os.path.isfile(directory):
        # Single file provided
        if any(directory.lower().endswith(fmt) for fmt in supported_formats):
            return [directory]
        else:
            logger.warning(f"File {directory} is not a supported image format")
            return []
    
    # Directory provided - search for all images
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(fmt) for fmt in supported_formats):
                image_files.append(os.path.join(root, file))
    
    logger.info(f"✓ Found {len(image_files)} image files in {directory}")
    return sorted(image_files)


def format_results(results: List[Dict], format_type: str = 'text') -> str:
    """
    Format OCR results for display.
    
    Args:
        results: List of OCR results
        format_type: Output format ('text', 'json', 'table')
        
    Returns:
        Formatted string
    """
    if format_type == 'json':
        return json.dumps(results, indent=2, ensure_ascii=False)
    
    elif format_type == 'table':
        output = []
        output.append("=" * 80)
        output.append(f"{'File':<40} {'Status':<10} {'Length':<10}")
        output.append("=" * 80)
        
        for result in results:
            filename = Path(result['file']).name[:37] + '...' if len(Path(result['file']).name) > 40 else Path(result['file']).name
            status = '✓ OK' if result['status'] == 'success' else '✗ Error'
            length = len(result.get('text', ''))
            output.append(f"{filename:<40} {status:<10} {length:<10}")
        
        output.append("=" * 80)
        return '\n'.join(output)
    
    else:  # text format
        output = []
        for result in results:
            output.append(f"\n{'=' * 80}")
            output.append(f"File: {result['file']}")
            output.append(f"Status: {result['status']}")
            if result['status'] == 'success':
                output.append(f"Text Length: {len(result.get('text', ''))} characters")
                output.append(f"\nExtracted Text:")
                output.append('-' * 80)
                output.append(result.get('text', ''))
            else:
                output.append(f"Error: {result.get('error', 'Unknown error')}")
            output.append('=' * 80)
        
        return '\n'.join(output)


def create_output_filename(input_path: str, output_dir: str, suffix: str = '_extracted', 
                          extension: str = 'txt') -> str:
    """
    Create output filename based on input filename.
    
    Args:
        input_path: Input file path
        output_dir: Output directory
        suffix: Suffix to add to filename
        extension: Output file extension
        
    Returns:
        Output file path
    """
    input_file = Path(input_path)
    output_name = f"{input_file.stem}{suffix}.{extension}"
    output_path = os.path.join(output_dir, output_name)
    
    return output_path


def ensure_directory(directory: str) -> None:
    """
    Ensure a directory exists, create if it doesn't.
    
    Args:
        directory: Directory path to create
    """
    os.makedirs(directory, exist_ok=True)
    logger.debug(f"Ensured directory exists: {directory}")


def get_timestamp() -> str:
    """
    Get current timestamp as string.
    
    Returns:
        Timestamp string in format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def validate_image(image_path: str, min_width: int = 100, min_height: int = 100,
                   max_width: int = 10000, max_height: int = 10000) -> bool:
    """
    Validate if an image meets minimum requirements.
    
    Args:
        image_path: Path to image file
        min_width: Minimum width in pixels
        min_height: Minimum height in pixels
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        
    Returns:
        True if valid, False otherwise
    """
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            
            if width < min_width or height < min_height:
                logger.warning(f"Image {image_path} too small: {width}x{height}")
                return False
            
            if width > max_width or height > max_height:
                logger.warning(f"Image {image_path} too large: {width}x{height}")
                return False
            
            return True
    except Exception as e:
        logger.error(f"Error validating image {image_path}: {e}")
        return False


def clean_text(text: str, remove_extra_spaces: bool = True, 
               remove_empty_lines: bool = True, strip_whitespace: bool = True) -> str:
    """
    Clean extracted text.
    
    Args:
        text: Text to clean
        remove_extra_spaces: Remove multiple consecutive spaces
        remove_empty_lines: Remove empty lines
        strip_whitespace: Strip leading/trailing whitespace
        
    Returns:
        Cleaned text
    """
    if remove_extra_spaces:
        # Replace multiple spaces with single space
        import re
        text = re.sub(r' +', ' ', text)
    
    if remove_empty_lines:
        lines = [line for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
    
    if strip_whitespace:
        text = text.strip()
    
    return text


def print_system_info():
    """Print system information for debugging."""
    import torch
    import sys
    
    print("\n" + "=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    print("=" * 60 + "\n")

