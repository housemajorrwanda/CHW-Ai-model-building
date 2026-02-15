"""
Image preprocessing utilities for TrOCR
Improves OCR accuracy by cleaning and enhancing images
"""
import cv2
import numpy as np
from PIL import Image
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Image preprocessor for OCR optimization.
    Applies various preprocessing techniques to improve recognition accuracy.
    """
    
    def __init__(self, 
                 denoise: bool = True,
                 enhance_contrast: bool = True,
                 auto_rotate: bool = True,
                 remove_borders: bool = True,
                 binarize: bool = False):
        """
        Initialize preprocessor with settings.
        
        Args:
            denoise: Enable noise removal
            enhance_contrast: Enable contrast enhancement
            auto_rotate: Enable automatic rotation correction
            remove_borders: Enable border removal
            binarize: Enable binarization (black & white)
        """
        self.denoise = denoise
        self.enhance_contrast = enhance_contrast
        self.auto_rotate = auto_rotate
        self.remove_borders = remove_borders
        self.binarize = binarize
        
        logger.info(f"ImagePreprocessor initialized with settings:")
        logger.info(f"  Denoise: {denoise}")
        logger.info(f"  Enhance Contrast: {enhance_contrast}")
        logger.info(f"  Auto Rotate: {auto_rotate}")
        logger.info(f"  Remove Borders: {remove_borders}")
        logger.info(f"  Binarize: {binarize}")
    
    def preprocess(self, image: Image.Image) -> Image.Image:
        """
        Apply all preprocessing steps to an image.
        
        Args:
            image: PIL Image to preprocess
            
        Returns:
            Preprocessed PIL Image
        """
        # Convert PIL to OpenCV format
        img_cv = self._pil_to_cv2(image)
        
        # Apply preprocessing steps in order
        if self.denoise:
            img_cv = self._denoise(img_cv)
        
        if self.enhance_contrast:
            img_cv = self._enhance_contrast(img_cv)
        
        if self.auto_rotate:
            img_cv = self._auto_rotate(img_cv)
        
        if self.remove_borders:
            img_cv = self._remove_borders(img_cv)
        
        if self.binarize:
            img_cv = self._binarize(img_cv)
        
        # Convert back to PIL
        result = self._cv2_to_pil(img_cv)
        
        logger.debug("Image preprocessing completed")
        return result
    
    def _pil_to_cv2(self, pil_image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format."""
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    def _cv2_to_pil(self, cv_image: np.ndarray) -> Image.Image:
        """Convert OpenCV image to PIL format."""
        return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
    
    def _denoise(self, img: np.ndarray, strength: int = 10) -> np.ndarray:
        """
        Remove noise from image using Non-Local Means Denoising.
        
        Args:
            img: Input image
            strength: Denoising strength (1-20, higher = more denoising)
            
        Returns:
            Denoised image
        """
        try:
            denoised = cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)
            logger.debug(f"Applied denoising with strength {strength}")
            return denoised
        except Exception as e:
            logger.warning(f"Denoising failed: {e}, returning original image")
            return img
    
    def _enhance_contrast(self, img: np.ndarray, alpha: float = 1.5, beta: int = 10) -> np.ndarray:
        """
        Enhance image contrast and brightness.
        
        Args:
            img: Input image
            alpha: Contrast multiplier (1.0 = no change, >1.0 = more contrast)
            beta: Brightness adjustment (-100 to 100)
            
        Returns:
            Enhanced image
        """
        try:
            # Apply contrast and brightness adjustment
            enhanced = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
            logger.debug(f"Enhanced contrast (alpha={alpha}, beta={beta})")
            return enhanced
        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {e}, returning original image")
            return img
    
    def _auto_rotate(self, img: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """
        Automatically detect and correct image rotation.
        
        Args:
            img: Input image
            threshold: Minimum angle (degrees) to trigger rotation
            
        Returns:
            Rotated image
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect edges
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Detect lines using Hough Transform
            lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
            
            if lines is None or len(lines) == 0:
                logger.debug("No lines detected for rotation correction")
                return img
            
            # Calculate median angle
            angles = []
            for rho, theta in lines[:, 0]:
                angle = np.degrees(theta) - 90
                angles.append(angle)
            
            median_angle = np.median(angles)
            
            # Only rotate if angle is significant
            if abs(median_angle) < threshold:
                logger.debug(f"Angle {median_angle:.2f}° too small, skipping rotation")
                return img
            
            # Rotate image
            height, width = img.shape[:2]
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(img, rotation_matrix, (width, height),
                                    flags=cv2.INTER_CUBIC,
                                    borderMode=cv2.BORDER_REPLICATE)
            
            logger.debug(f"Rotated image by {median_angle:.2f}°")
            return rotated
            
        except Exception as e:
            logger.warning(f"Auto-rotation failed: {e}, returning original image")
            return img
    
    def _remove_borders(self, img: np.ndarray, border_threshold: int = 50) -> np.ndarray:
        """
        Remove black/white borders from image.
        
        Args:
            img: Input image
            border_threshold: Threshold for border detection
            
        Returns:
            Cropped image
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Find non-border region
            # Threshold to binary
            _, thresh = cv2.threshold(gray, border_threshold, 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return img
            
            # Get bounding box of largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Crop image
            cropped = img[y:y+h, x:x+w]
            
            # Only return cropped if it's significantly different
            original_area = img.shape[0] * img.shape[1]
            cropped_area = cropped.shape[0] * cropped.shape[1]
            
            if cropped_area > 0.5 * original_area:  # Keep at least 50% of original
                logger.debug(f"Removed borders, cropped to {w}x{h}")
                return cropped
            else:
                logger.debug("Border removal would remove too much, keeping original")
                return img
                
        except Exception as e:
            logger.warning(f"Border removal failed: {e}, returning original image")
            return img
    
    def _binarize(self, img: np.ndarray) -> np.ndarray:
        """
        Convert image to black and white (binarization).
        
        Args:
            img: Input image
            
        Returns:
            Binarized image
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply adaptive threshold for better results
            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 11, 2)
            
            # Convert back to 3-channel for consistency
            binary_color = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
            
            logger.debug("Applied binarization")
            return binary_color
            
        except Exception as e:
            logger.warning(f"Binarization failed: {e}, returning original image")
            return img
    
    def resize_if_needed(self, image: Image.Image, max_width: int = 2048, 
                        max_height: int = 2048) -> Image.Image:
        """
        Resize image if it exceeds maximum dimensions.
        
        Args:
            image: PIL Image
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            
        Returns:
            Resized PIL Image
        """
        width, height = image.size
        
        if width <= max_width and height <= max_height:
            return image
        
        # Calculate scaling factor
        scale = min(max_width / width, max_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")
        
        return resized

