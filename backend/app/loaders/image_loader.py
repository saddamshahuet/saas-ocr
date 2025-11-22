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
        """
        Return supported file extensions

        Comprehensive image format support including:
        - Standard formats: PNG, JPG, BMP, GIF
        - Scanned documents: TIFF (multi-page), TIFF with compression
        - Modern formats: WebP, HEIC, AVIF
        - Professional formats: JPEG 2000, DNG, RAW
        - Legacy formats: PCX, TGA, PBM/PGM/PPM
        """
        return [
            # Standard formats
            ".png",           # Portable Network Graphics
            ".jpg", ".jpeg",  # JPEG
            ".bmp",           # Bitmap
            ".gif",           # Graphics Interchange Format

            # Scanned document formats (most common for scanners)
            ".tiff", ".tif",  # Tagged Image File Format (supports multi-page, compression)

            # Modern/Web formats
            ".webp",          # WebP (Google's format, good compression)
            ".heic", ".heif", # High Efficiency Image Format (Apple)
            ".avif",          # AV1 Image File Format (next-gen)

            # JPEG variants
            ".jp2", ".j2k",   # JPEG 2000
            ".jpe",           # JPEG variant
            ".jfif",          # JPEG File Interchange Format

            # Professional/RAW formats
            ".dng",           # Digital Negative (Adobe RAW)
            ".raw",           # RAW image data

            # Legacy/Specialized formats
            ".pcx",           # PC Paintbrush
            ".tga",           # Truevision TGA/TARGA
            ".ico",           # Icon file

            # Netpbm formats
            ".pbm",           # Portable Bitmap
            ".pgm",           # Portable Graymap
            ".ppm",           # Portable Pixmap
            ".pnm",           # Portable Anymap

            # Other formats
            ".svg",           # Scalable Vector Graphics (will be rasterized)
            ".eps",           # Encapsulated PostScript (will be rasterized)
        ]

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

        # Load image with special format handling
        if file_path:
            image, file_size = self._load_image_file(file_path)
        else:
            if isinstance(file_content, bytes):
                image_bytes = file_content
            else:
                image_bytes = file_content.read()

            image = self._load_image_from_bytes(image_bytes)
            file_size = len(image_bytes)

        # Validate file size
        self.validate_file_size(file_size)

        # Check if this is a multi-page TIFF
        is_multipage = hasattr(image, 'n_frames') and image.n_frames > 1

        if is_multipage:
            return self._load_multipage_image(image, file_path, file_size)


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

    def _load_image_file(self, file_path: str) -> tuple[Image.Image, int]:
        """
        Load image from file with special format handling

        Args:
            file_path: Path to image file

        Returns:
            Tuple of (PIL Image, file size)
        """
        import os
        file_ext = os.path.splitext(file_path)[1].lower()

        # Special handling for certain formats
        if file_ext in ['.heic', '.heif']:
            # HEIC/HEIF requires pillow-heif plugin
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener()
            except ImportError:
                logger.warning("pillow-heif not installed. Install with: pip install pillow-heif")

        elif file_ext in ['.avif']:
            # AVIF may need pillow-avif-plugin
            try:
                import pillow_avif
            except ImportError:
                logger.warning("pillow-avif-plugin not installed. Install with: pip install pillow-avif-plugin")

        elif file_ext in ['.svg', '.eps']:
            # SVG/EPS need to be rasterized
            return self._rasterize_vector_image(file_path), os.path.getsize(file_path)

        # Standard PIL loading
        image = Image.open(file_path)
        file_size = os.path.getsize(file_path)

        return image, file_size

    def _load_image_from_bytes(self, image_bytes: bytes) -> Image.Image:
        """
        Load image from bytes with format detection

        Args:
            image_bytes: Image data as bytes

        Returns:
            PIL Image object
        """
        # Try to detect format and apply special handling
        try:
            # First try standard PIL loading
            return Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.error(f"Failed to load image from bytes: {e}")
            raise

    def _rasterize_vector_image(self, file_path: str, dpi: int = 300) -> Image.Image:
        """
        Rasterize vector images (SVG, EPS) to raster format

        Args:
            file_path: Path to vector image
            dpi: DPI for rasterization

        Returns:
            Rasterized PIL Image
        """
        import os
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.svg':
            try:
                from cairosvg import svg2png
                png_bytes = svg2png(url=file_path, dpi=dpi)
                return Image.open(io.BytesIO(png_bytes))
            except ImportError:
                logger.warning("cairosvg not installed. Install with: pip install cairosvg")
                # Fallback: try with PIL
                return Image.open(file_path)

        elif file_ext == '.eps':
            # EPS can be opened with PIL but may need Ghostscript
            try:
                image = Image.open(file_path)
                image.load(scale=dpi/72)  # Convert to desired DPI
                return image
            except Exception as e:
                logger.error(f"Failed to rasterize EPS: {e}")
                raise

        return Image.open(file_path)

    def _load_multipage_image(
        self,
        image: Image.Image,
        file_path: Optional[str],
        file_size: int
    ) -> LoadedDocument:
        """
        Load multi-page image (e.g., multi-page TIFF)

        Args:
            image: PIL Image object
            file_path: Optional file path
            file_size: File size in bytes

        Returns:
            LoadedDocument with all pages processed
        """
        metadata = self.extract_metadata(file_path)

        n_frames = image.n_frames
        logger.info(f"Loading multi-page image with {n_frames} pages")

        metadata.update({
            "is_multipage": True,
            "total_pages": n_frames,
            "image_format": image.format or "unknown"
        })

        all_text = []
        all_confidences = []

        # Process each page/frame
        for frame_num in range(n_frames):
            try:
                image.seek(frame_num)

                if self.ocr_engine:
                    text, confidence = self._extract_text_with_ocr(image)
                    if text:
                        all_text.append(f"--- Page {frame_num + 1} ---\n{text}")
                        all_confidences.append(confidence)
                else:
                    logger.warning(f"No OCR engine for page {frame_num + 1}")

            except Exception as e:
                logger.error(f"Failed to process page {frame_num + 1}: {e}")

        # Combine all pages
        full_text = "\n\n".join(all_text)
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        metadata["ocr_confidence"] = avg_confidence

        # Create chunks if enabled
        chunks = None
        if self.enable_chunking and full_text:
            from ..chunking.strategies import get_chunking_strategy
            chunker = get_chunking_strategy(
                strategy_name="sentence_aware",
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            text_chunks = chunker.chunk(full_text, metadata)

            chunks = [
                DocumentChunk(
                    content=chunk.content,
                    chunk_index=chunk.index,
                    total_chunks=chunk.total_chunks,
                    metadata=chunk.metadata,
                    confidence=avg_confidence
                )
                for chunk in text_chunks
            ]

        return LoadedDocument(
            content=full_text,
            document_type=DocumentType.IMAGE,
            file_size=file_size,
            page_count=n_frames,
            metadata=metadata,
            chunks=chunks
        )
