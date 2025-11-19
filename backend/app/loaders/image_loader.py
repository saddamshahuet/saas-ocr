"""Image document loader with OCR support"""
import os
from typing import List, Optional, Union, BinaryIO
from PIL import Image
import io
import logging
from .base import BaseDocumentLoader, LoadedDocument, DocumentType, DocumentChunk

logger = logging.getLogger(__name__)


class ImageLoader(BaseDocumentLoader):
    """Loader for image documents (PNG, JPG, TIFF, etc.)"""

    def __init__(
        self,
        ocr_engine=None,
        preprocess: bool = True,
        **kwargs
    ):
        """
        Initialize image loader

        Args:
            ocr_engine: OCR engine instance (required for text extraction)
            preprocess: Whether to preprocess image before OCR
            **kwargs: Additional loader arguments
        """
        super().__init__(**kwargs)
        self.ocr_engine = ocr_engine
        self.preprocess = preprocess

        if not self.ocr_engine:
            logger.warning("No OCR engine provided - text extraction will not be available")

    def supported_extensions(self) -> List[str]:
        """Return supported file extensions"""
        return [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"]

    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """
        Load image document

        Args:
            file_path: Path to image file
            file_content: Binary content of image
            **kwargs: Additional arguments

        Returns:
            LoadedDocument object
        """
        if not file_path and not file_content:
            raise ValueError("Either file_path or file_content must be provided")

        # Load image
        if file_path:
            image = Image.open(file_path)
            file_size = os.path.getsize(file_path)
        else:
            if isinstance(file_content, bytes):
                image = Image.open(io.BytesIO(file_content))
                file_size = len(file_content)
            else:
                image_bytes = file_content.read()
                image = Image.open(io.BytesIO(image_bytes))
                file_size = len(image_bytes)

        # Validate file size
        self.validate_file_size(file_size)

        # Extract metadata
        metadata = self.extract_metadata(file_path)
        metadata.update({
            "image_size": image.size,
            "image_mode": image.mode,
            "image_format": image.format or "unknown"
        })

        # Extract text using OCR
        text_content = ""
        confidence = 0.0

        if self.ocr_engine:
            text_content, confidence = self._extract_text_with_ocr(image)
            metadata["ocr_confidence"] = confidence
        else:
            logger.warning("No OCR engine available - returning empty text")

        # Create chunks if enabled
        chunks = None
        if self.enable_chunking and text_content:
            from ..chunking.strategies import get_chunking_strategy
            chunker = get_chunking_strategy(
                strategy_name="sentence_aware",
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            text_chunks = chunker.chunk(text_content, metadata)

            chunks = [
                DocumentChunk(
                    content=chunk.content,
                    chunk_index=chunk.index,
                    total_chunks=chunk.total_chunks,
                    page_number=1,
                    metadata=chunk.metadata,
                    confidence=confidence
                )
                for chunk in text_chunks
            ]

        # Get raw bytes
        raw_bytes = io.BytesIO()
        image.save(raw_bytes, format=image.format or 'PNG')
        raw_bytes = raw_bytes.getvalue()

        return LoadedDocument(
            content=text_content,
            document_type=DocumentType.IMAGE,
            file_size=file_size,
            page_count=1,
            metadata=metadata,
            chunks=chunks,
            raw_data=raw_bytes
        )

    def _extract_text_with_ocr(self, image: Image.Image) -> tuple[str, float]:
        """
        Extract text from image using OCR

        Args:
            image: PIL Image object

        Returns:
            Tuple of (text, confidence)
        """
        try:
            import numpy as np
            import cv2

            # Convert PIL to numpy array
            img_array = np.array(image)

            # Convert to BGR if needed
            if len(img_array.shape) == 3:
                if img_array.shape[2] == 4:  # RGBA
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
                else:  # RGB
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            # Preprocess if enabled
            if self.preprocess:
                img_array = self._preprocess_image(img_array)

            # Run OCR
            result = self.ocr_engine.ocr(img_array, cls=True)

            if not result or not result[0]:
                return "", 0.0

            # Extract text and confidence
            text_lines = []
            confidences = []

            for line in result[0]:
                text, confidence = line[1]
                text_lines.append(text)
                confidences.append(float(confidence))

            full_text = "\n".join(text_lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return full_text, avg_confidence

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", 0.0

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR

        Args:
            image: Image as numpy array

        Returns:
            Preprocessed image
        """
        import cv2

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)

        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        return binary
