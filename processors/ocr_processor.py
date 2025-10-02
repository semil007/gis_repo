"""
OCR processing pipeline using Tesseract with image preprocessing and confidence scoring.
"""

import io
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from loguru import logger

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available, PDF to image conversion will be limited")

from .base import DocumentProcessingError


class OCRProcessingError(DocumentProcessingError):
    """OCR-specific processing error."""
    pass


class OCRProcessor:
    """
    OCR processing pipeline with image preprocessing and confidence scoring.
    Supports multiple languages and document orientations.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize OCR processor with configuration.
        
        Args:
            config: Configuration dictionary with OCR options
        """
        self.config = config or {}
        
        # OCR configuration
        self.language = self.config.get("language", "eng")
        self.psm_mode = self.config.get("psm_mode", 6)  # Uniform block of text
        self.oem_mode = self.config.get("oem_mode", 3)  # Default OCR Engine Mode
        self.confidence_threshold = self.config.get("confidence_threshold", 30)
        self.preprocessing_enabled = self.config.get("preprocessing", True)
        
        # Image preprocessing settings
        self.dpi = self.config.get("dpi", 300)
        self.enhance_contrast = self.config.get("enhance_contrast", True)
        self.denoise = self.config.get("denoise", True)
        self.deskew = self.config.get("deskew", True)
        
        # Character whitelist for better accuracy
        self.char_whitelist = self.config.get(
            "char_whitelist", 
            "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?@#$%^&*()_+-=[]{}|;:'\",.<>?/`~ "
        )
        
        self.setup_tesseract_config()
        
    def setup_tesseract_config(self):
        """Setup Tesseract configuration string."""
        config_parts = [
            f"--psm {self.psm_mode}",
            f"--oem {self.oem_mode}",
            f"-c tessedit_char_whitelist={self.char_whitelist}"
        ]
        
        self.tesseract_config = " ".join(config_parts)
        logger.debug(f"Tesseract config: {self.tesseract_config}")
        
    def process_pdf_to_images(self, pdf_path: Union[str, Path]) -> List[Image.Image]:
        """
        Convert PDF pages to images for OCR processing.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PIL Image objects
            
        Raises:
            OCRProcessingError: If PDF conversion fails
        """
        if not PDF2IMAGE_AVAILABLE:
            raise OCRProcessingError("pdf2image library required for PDF to image conversion")
            
        try:
            logger.info(f"Converting PDF to images: {pdf_path}")
            
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt='RGB'
            )
            
            logger.info(f"Converted PDF to {len(images)} images")
            return images
            
        except Exception as e:
            raise OCRProcessingError(f"PDF to image conversion failed: {str(e)}")
            
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Apply preprocessing to improve OCR accuracy.
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image object
        """
        if not self.preprocessing_enabled:
            return image
            
        try:
            logger.debug("Applying image preprocessing")
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            # Convert to OpenCV format for advanced preprocessing
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Denoise if enabled
            if self.denoise:
                gray = cv2.fastNlMeansDenoising(gray)
                
            # Deskew if enabled
            if self.deskew:
                gray = self._deskew_image(gray)
                
            # Apply adaptive thresholding for better text contrast
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(thresh)
            
            # Enhance contrast if enabled
            if self.enhance_contrast:
                enhancer = ImageEnhance.Contrast(processed_image)
                processed_image = enhancer.enhance(1.5)
                
            logger.debug("Image preprocessing completed")
            return processed_image
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}")
            return image  # Return original image if preprocessing fails
            
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """
        Correct skew in the image.
        
        Args:
            image: OpenCV image array
            
        Returns:
            Deskewed image array
        """
        try:
            # Find contours and get the largest one (assumed to be the document)
            contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return image
                
            # Get the largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Get the minimum area rectangle
            rect = cv2.minAreaRect(largest_contour)
            angle = rect[2]
            
            # Correct the angle
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
                
            # Only apply correction if angle is significant
            if abs(angle) > 0.5:
                h, w = image.shape
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                image = cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                logger.debug(f"Applied deskew correction: {angle:.2f} degrees")
                
            return image
            
        except Exception as e:
            logger.warning(f"Deskew failed: {str(e)}")
            return image
            
    def extract_text_with_confidence(self, image: Image.Image) -> Tuple[str, Dict]:
        """
        Extract text from image with confidence scores.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (extracted_text, confidence_data)
        """
        try:
            logger.debug("Extracting text with confidence scores")
            
            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(
                image, 
                lang=self.language,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text with confidence filtering
            filtered_text_parts = []
            confidence_scores = []
            word_confidences = []
            
            for i, confidence in enumerate(ocr_data['conf']):
                text = ocr_data['text'][i].strip()
                
                if text and confidence > self.confidence_threshold:
                    filtered_text_parts.append(text)
                    confidence_scores.append(confidence)
                    word_confidences.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': {
                            'left': ocr_data['left'][i],
                            'top': ocr_data['top'][i],
                            'width': ocr_data['width'][i],
                            'height': ocr_data['height'][i]
                        }
                    })
                    
            # Combine text
            extracted_text = ' '.join(filtered_text_parts)
            
            # Calculate overall confidence metrics
            confidence_data = {
                'overall_confidence': np.mean(confidence_scores) if confidence_scores else 0,
                'word_count': len(word_confidences),
                'low_confidence_words': len([w for w in word_confidences if w['confidence'] < 60]),
                'high_confidence_words': len([w for w in word_confidences if w['confidence'] > 80]),
                'word_details': word_confidences,
                'confidence_distribution': {
                    'min': min(confidence_scores) if confidence_scores else 0,
                    'max': max(confidence_scores) if confidence_scores else 0,
                    'mean': np.mean(confidence_scores) if confidence_scores else 0,
                    'std': np.std(confidence_scores) if confidence_scores else 0
                }
            }
            
            logger.debug(f"OCR extracted {len(extracted_text)} characters with {confidence_data['overall_confidence']:.1f}% confidence")
            
            return extracted_text, confidence_data
            
        except Exception as e:
            logger.error(f"OCR text extraction failed: {str(e)}")
            return "", {"overall_confidence": 0, "error": str(e)}
            
    def process_image(self, image: Union[Image.Image, str, Path]) -> Dict:
        """
        Process a single image with OCR.
        
        Args:
            image: PIL Image object or path to image file
            
        Returns:
            Dictionary with OCR results and confidence data
        """
        try:
            # Load image if path provided
            if isinstance(image, (str, Path)):
                image = Image.open(image)
                
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Extract text with confidence
            text, confidence_data = self.extract_text_with_confidence(processed_image)
            
            return {
                'text': text,
                'confidence_data': confidence_data,
                'preprocessing_applied': self.preprocessing_enabled,
                'language': self.language
            }
            
        except Exception as e:
            logger.error(f"Image OCR processing failed: {str(e)}")
            return {
                'text': "",
                'confidence_data': {"overall_confidence": 0, "error": str(e)},
                'preprocessing_applied': False,
                'error': str(e)
            }
            
    def process_pdf_with_ocr(self, pdf_path: Union[str, Path]) -> Dict:
        """
        Process PDF with OCR by converting to images first.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with combined OCR results from all pages
        """
        try:
            logger.info(f"Processing PDF with OCR: {pdf_path}")
            
            # Convert PDF to images
            images = self.process_pdf_to_images(pdf_path)
            
            # Process each page
            page_results = []
            all_text_parts = []
            all_confidences = []
            
            for i, image in enumerate(images):
                logger.debug(f"Processing page {i + 1}/{len(images)}")
                
                page_result = self.process_image(image)
                page_results.append({
                    'page_number': i + 1,
                    'text': page_result['text'],
                    'confidence': page_result['confidence_data']['overall_confidence']
                })
                
                if page_result['text']:
                    all_text_parts.append(page_result['text'])
                    all_confidences.append(page_result['confidence_data']['overall_confidence'])
                    
            # Combine results
            combined_text = '\n\n'.join(all_text_parts)
            overall_confidence = np.mean(all_confidences) if all_confidences else 0
            
            result = {
                'text': combined_text,
                'page_count': len(images),
                'pages_processed': len([p for p in page_results if p['text']]),
                'overall_confidence': overall_confidence,
                'page_results': page_results,
                'language': self.language,
                'preprocessing_applied': self.preprocessing_enabled
            }
            
            logger.info(f"OCR completed: {len(combined_text)} characters, {overall_confidence:.1f}% confidence")
            
            return result
            
        except Exception as e:
            logger.error(f"PDF OCR processing failed: {str(e)}")
            return {
                'text': "",
                'page_count': 0,
                'pages_processed': 0,
                'overall_confidence': 0,
                'error': str(e)
            }
            
    def detect_orientation(self, image: Image.Image) -> Dict:
        """
        Detect document orientation and suggest rotation.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with orientation information
        """
        try:
            # Use Tesseract's orientation detection
            osd_data = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
            
            orientation_info = {
                'rotate': osd_data.get('rotate', 0),
                'orientation_confidence': osd_data.get('orientation_conf', 0),
                'script': osd_data.get('script', 'Latin'),
                'script_confidence': osd_data.get('script_conf', 0)
            }
            
            logger.debug(f"Detected orientation: {orientation_info}")
            
            return orientation_info
            
        except Exception as e:
            logger.warning(f"Orientation detection failed: {str(e)}")
            return {'rotate': 0, 'orientation_confidence': 0}
            
    def auto_rotate_image(self, image: Image.Image) -> Image.Image:
        """
        Automatically rotate image based on detected orientation.
        
        Args:
            image: PIL Image object
            
        Returns:
            Rotated PIL Image object
        """
        try:
            orientation_info = self.detect_orientation(image)
            rotation_angle = orientation_info.get('rotate', 0)
            
            if rotation_angle != 0 and orientation_info.get('orientation_confidence', 0) > 5:
                logger.debug(f"Auto-rotating image by {rotation_angle} degrees")
                image = image.rotate(-rotation_angle, expand=True)
                
            return image
            
        except Exception as e:
            logger.warning(f"Auto-rotation failed: {str(e)}")
            return image
            
    def get_supported_languages(self) -> List[str]:
        """
        Get list of languages supported by Tesseract installation.
        
        Returns:
            List of supported language codes
        """
        try:
            languages = pytesseract.get_languages()
            logger.debug(f"Supported OCR languages: {languages}")
            return languages
        except Exception as e:
            logger.warning(f"Could not get supported languages: {str(e)}")
            return ['eng']  # Default to English
            
    def validate_tesseract_installation(self) -> bool:
        """
        Validate that Tesseract is properly installed and accessible.
        
        Returns:
            True if Tesseract is working correctly
        """
        try:
            # Test with a simple image
            test_image = Image.new('RGB', (100, 50), color='white')
            pytesseract.image_to_string(test_image)
            logger.info("Tesseract installation validated successfully")
            return True
        except Exception as e:
            logger.error(f"Tesseract validation failed: {str(e)}")
            return False