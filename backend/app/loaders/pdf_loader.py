"""PDF document loader with OCR support"""
import os
from typing import List, Optional, Union, BinaryIO
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
import io
import logging
import PyPDF2
from .base import BaseDocumentLoader, LoadedDocument, DocumentType, DocumentChunk

logger = logging.getLogger(__name__)


class PDFLoader(BaseDocumentLoader):
    """Loader for PDF documents with OCR capability"""

    def __init__(
        self,
        use_ocr: bool = True,
        ocr_engine=None,
        extract_images: bool = True,
        dpi: int = 300,
        **kwargs
    ):
        """
        Initialize PDF loader

        Args:
            use_ocr: Whether to use OCR for scanned PDFs
            ocr_engine: OCR engine instance (PaddleOCR, Tesseract, etc.)
            extract_images: Whether to extract embedded images
            dpi: DPI for PDF to image conversion
            **kwargs: Additional loader arguments
        """
        super().__init__(**kwargs)
        self.use_ocr = use_ocr
        self.ocr_engine = ocr_engine
        self.extract_images = extract_images
        self.dpi = dpi

    def supported_extensions(self) -> List[str]:
        """Return supported file extensions"""
        return [".pdf"]

    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """
        Load PDF document

        Args:
            file_path: Path to PDF file
            file_content: Binary content of PDF
            **kwargs: Additional arguments

        Returns:
            LoadedDocument object
        """
        if not file_path and not file_content:
            raise ValueError("Either file_path or file_content must be provided")

        # Get file content
        if file_path:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            file_size = os.path.getsize(file_path)
        else:
            if isinstance(file_content, bytes):
                pdf_bytes = file_content
            else:
                pdf_bytes = file_content.read()
            file_size = len(pdf_bytes)

        # Validate file size
        self.validate_file_size(file_size)

        # Extract metadata
        metadata = self.extract_metadata(file_path)

        # Try to extract text directly from PDF first
        text_content, page_count = self._extract_text_from_pdf(pdf_bytes)

        # If no text found and OCR is enabled, use OCR
        if not text_content.strip() and self.use_ocr and self.ocr_engine:
            self.logger.info("No text found in PDF, using OCR")
            text_content, page_count = self._ocr_pdf(pdf_bytes, file_path)

        metadata.update({
            "page_count": page_count,
            "has_ocr": self.use_ocr and self.ocr_engine is not None,
            "extraction_method": "ocr" if self.use_ocr else "direct"
        })

        # Create chunks if enabled
        chunks = None
        if self.enable_chunking:
            # Import chunking strategy
            from ..chunking.strategies import get_chunking_strategy
            chunker = get_chunking_strategy(
                strategy_name="semantic",
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            text_chunks = chunker.chunk(text_content, metadata)

            # Convert to DocumentChunk
            chunks = [
                DocumentChunk(
                    content=chunk.content,
                    chunk_index=chunk.index,
                    total_chunks=chunk.total_chunks,
                    metadata=chunk.metadata
                )
                for chunk in text_chunks
            ]

        return LoadedDocument(
            content=text_content,
            document_type=DocumentType.PDF,
            file_size=file_size,
            page_count=page_count,
            metadata=metadata,
            chunks=chunks,
            raw_data=pdf_bytes
        )

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> tuple[str, int]:
        """
        Extract text directly from PDF

        Args:
            pdf_bytes: PDF file bytes

        Returns:
            Tuple of (text_content, page_count)
        """
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            page_count = len(pdf_reader.pages)

            text_parts = []
            for i, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(f"--- Page {i + 1} ---\n{page_text}")
                except Exception as e:
                    self.logger.warning(f"Failed to extract text from page {i + 1}: {e}")

            return "\n\n".join(text_parts), page_count

        except Exception as e:
            self.logger.error(f"Failed to extract text from PDF: {e}")
            return "", 0

    def _ocr_pdf(self, pdf_bytes: bytes, file_path: Optional[str] = None) -> tuple[str, int]:
        """
        Perform OCR on PDF

        Args:
            pdf_bytes: PDF file bytes
            file_path: Optional file path for pdf2image

        Returns:
            Tuple of (text_content, page_count)
        """
        try:
            # Convert PDF to images
            if file_path:
                images = convert_from_path(file_path, dpi=self.dpi)
            else:
                images = convert_from_bytes(pdf_bytes, dpi=self.dpi)

            self.logger.info(f"Converted PDF to {len(images)} images for OCR")

            text_parts = []
            for i, image in enumerate(images):
                try:
                    # Convert PIL image to bytes for OCR
                    import numpy as np
                    import cv2

                    img_array = np.array(image)
                    if len(img_array.shape) == 3:
                        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                    # Run OCR
                    result = self.ocr_engine.ocr(img_array, cls=True)

                    if result and result[0]:
                        page_text = []
                        for line in result[0]:
                            text, confidence = line[1]
                            page_text.append(text)

                        if page_text:
                            text_parts.append(f"--- Page {i + 1} ---\n" + "\n".join(page_text))

                except Exception as e:
                    self.logger.warning(f"Failed to OCR page {i + 1}: {e}")

            return "\n\n".join(text_parts), len(images)

        except Exception as e:
            self.logger.error(f"Failed to OCR PDF: {e}")
            return "", 0
