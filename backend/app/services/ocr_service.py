"""OCR processing service using PaddleOCR"""
import os
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from PIL import Image
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import logging

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from images and PDFs using OCR"""

    def __init__(self, use_gpu: bool = True, language: str = "en"):
        """
        Initialize OCR service

        Args:
            use_gpu: Whether to use GPU acceleration
            language: Language for OCR (default: English)
        """
        self.use_gpu = use_gpu
        self.language = language

        # Initialize PaddleOCR
        try:
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,  # Enable angle classification
                lang=language,
                use_gpu=use_gpu,
                show_log=False,
            )
            logger.info(f"PaddleOCR initialized (GPU: {use_gpu}, Language: {language})")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image to improve OCR accuracy

        Args:
            image: Input image as numpy array

        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)

        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Binarization (adaptive thresholding)
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        return binary

    def extract_text_from_image(
        self,
        image_path: str,
        preprocess: bool = True
    ) -> Tuple[str, List[Dict], float]:
        """
        Extract text from an image file

        Args:
            image_path: Path to image file
            preprocess: Whether to preprocess the image

        Returns:
            Tuple of (extracted_text, detailed_results, average_confidence)
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image: {image_path}")

            # Preprocess if requested
            if preprocess:
                image = self.preprocess_image(image)

            # Run OCR
            result = self.ocr_engine.ocr(image, cls=True)

            # Parse results
            if not result or not result[0]:
                return "", [], 0.0

            text_blocks = []
            confidences = []
            full_text = []

            for line in result[0]:
                # line format: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], (text, confidence)]
                bbox = line[0]
                text, confidence = line[1]

                text_blocks.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": bbox
                })

                confidences.append(float(confidence))
                full_text.append(text)

            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Join text with newlines
            extracted_text = "\n".join(full_text)

            return extracted_text, text_blocks, avg_confidence

        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {e}")
            raise

    def extract_text_from_pdf(
        self,
        pdf_path: str,
        preprocess: bool = True,
        dpi: int = 300
    ) -> Tuple[str, List[Dict], float]:
        """
        Extract text from a PDF file

        Args:
            pdf_path: Path to PDF file
            preprocess: Whether to preprocess images
            dpi: DPI for PDF to image conversion

        Returns:
            Tuple of (extracted_text, detailed_results, average_confidence)
        """
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=dpi)
            logger.info(f"Converted PDF to {len(images)} images")

            all_text = []
            all_blocks = []
            all_confidences = []

            # Process each page
            for page_num, image in enumerate(images, 1):
                # Convert PIL Image to numpy array
                image_np = np.array(image)

                # Convert RGB to BGR (OpenCV format)
                if len(image_np.shape) == 3:
                    image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

                # Preprocess if requested
                if preprocess:
                    image_np = self.preprocess_image(image_np)

                # Run OCR
                result = self.ocr_engine.ocr(image_np, cls=True)

                if result and result[0]:
                    page_text = []
                    for line in result[0]:
                        bbox = line[0]
                        text, confidence = line[1]

                        all_blocks.append({
                            "page": page_num,
                            "text": text,
                            "confidence": float(confidence),
                            "bbox": bbox
                        })

                        all_confidences.append(float(confidence))
                        page_text.append(text)

                    # Add page separator
                    all_text.append(f"--- Page {page_num} ---\n" + "\n".join(page_text))

            # Calculate average confidence
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

            # Join all pages
            extracted_text = "\n\n".join(all_text)

            return extracted_text, all_blocks, avg_confidence

        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            raise

    def process_document(
        self,
        file_path: str,
        file_type: str,
        preprocess: bool = True
    ) -> Dict:
        """
        Process a document (image or PDF) and extract text

        Args:
            file_path: Path to document file
            file_type: File type (pdf, png, jpg, etc.)
            preprocess: Whether to preprocess images

        Returns:
            Dictionary with extraction results
        """
        file_type = file_type.lower()

        if file_type == "pdf":
            text, blocks, confidence = self.extract_text_from_pdf(file_path, preprocess)
            total_pages = len(set(block["page"] for block in blocks))
        elif file_type in ["png", "jpg", "jpeg", "tiff", "tif"]:
            text, blocks, confidence = self.extract_text_from_image(file_path, preprocess)
            total_pages = 1
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        return {
            "raw_text": text,
            "text_blocks": blocks,
            "average_confidence": confidence,
            "total_pages": total_pages,
            "total_blocks": len(blocks)
        }


# Singleton instance
_ocr_service_instance = None


def get_ocr_service(use_gpu: bool = True, language: str = "en") -> OCRService:
    """Get or create OCR service singleton"""
    global _ocr_service_instance
    if _ocr_service_instance is None:
        _ocr_service_instance = OCRService(use_gpu=use_gpu, language=language)
    return _ocr_service_instance
