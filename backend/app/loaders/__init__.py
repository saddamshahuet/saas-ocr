"""Document loaders module - Factory and utilities"""
import os
from typing import Optional, Dict, Any
import logging
from .base import BaseDocumentLoader, LoadedDocument, DocumentType
from .pdf_loader import PDFLoader
from .image_loader import ImageLoader
from .office_loaders import WordLoader, ExcelLoader, PowerPointLoader
from .text_loaders import (
    TextLoader, RTFLoader, MarkdownLoader,
    HTMLLoader, CSVLoader, JSONLoader, XMLLoader
)

logger = logging.getLogger(__name__)


class DocumentLoaderFactory:
    """Factory for creating appropriate document loaders"""

    def __init__(self, ocr_engine=None):
        """
        Initialize factory

        Args:
            ocr_engine: OCR engine instance for loaders that need it
        """
        self.ocr_engine = ocr_engine
        self._loaders: Dict[str, BaseDocumentLoader] = {}

    def get_loader(
        self,
        file_extension: str,
        loader_config: Optional[Dict[str, Any]] = None
    ) -> BaseDocumentLoader:
        """
        Get appropriate loader for file extension

        Args:
            file_extension: File extension (with or without dot)
            loader_config: Optional configuration for the loader

        Returns:
            Document loader instance

        Raises:
            ValueError: If no loader available for the file type
        """
        # Normalize extension
        ext = file_extension.lower()
        if not ext.startswith('.'):
            ext = f'.{ext}'

        # Default config
        config = loader_config or {}

        # Select and instantiate loader
        if ext == '.pdf':
            return PDFLoader(
                ocr_engine=self.ocr_engine,
                **config
            )

        elif ext in [
            # Standard formats
            '.png', '.jpg', '.jpeg', '.bmp', '.gif',
            # Scanned formats
            '.tiff', '.tif',
            # Modern formats
            '.webp', '.heic', '.heif', '.avif',
            # JPEG variants
            '.jp2', '.j2k', '.jpe', '.jfif',
            # Professional/RAW
            '.dng', '.raw',
            # Legacy
            '.pcx', '.tga', '.ico',
            # Netpbm
            '.pbm', '.pgm', '.ppm', '.pnm',
            # Vector (rasterized)
            '.svg', '.eps'
        ]:
            return ImageLoader(
                ocr_engine=self.ocr_engine,
                **config
            )

        elif ext in ['.doc', '.docx']:
            return WordLoader(**config)

        elif ext in ['.xls', '.xlsx', '.xlsm']:
            return ExcelLoader(**config)

        elif ext in ['.ppt', '.pptx']:
            return PowerPointLoader(**config)

        elif ext == '.txt':
            return TextLoader(**config)

        elif ext == '.rtf':
            return RTFLoader(**config)

        elif ext in ['.md', '.markdown']:
            return MarkdownLoader(**config)

        elif ext in ['.html', '.htm']:
            return HTMLLoader(**config)

        elif ext == '.csv':
            return CSVLoader(**config)

        elif ext == '.json':
            return JSONLoader(**config)

        elif ext == '.xml':
            return XMLLoader(**config)

        else:
            raise ValueError(f"No loader available for file type: {ext}")

    def load_document(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        file_extension: Optional[str] = None,
        loader_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LoadedDocument:
        """
        Load a document using appropriate loader

        Args:
            file_path: Path to the document
            file_content: Binary content of the document
            file_extension: File extension (required if file_content is provided)
            loader_config: Configuration for the loader
            **kwargs: Additional arguments for the loader

        Returns:
            LoadedDocument object

        Raises:
            ValueError: If neither file_path nor (file_content + file_extension) provided
        """
        # Determine file extension
        if file_path:
            ext = os.path.splitext(file_path)[1]
        elif file_extension:
            ext = file_extension
        else:
            raise ValueError("Either file_path or file_extension must be provided")

        # Get appropriate loader
        loader = self.get_loader(ext, loader_config)

        # Load document
        return loader.load(
            file_path=file_path,
            file_content=file_content,
            **kwargs
        )

    def get_supported_extensions(self) -> Dict[str, str]:
        """
        Get all supported file extensions and their document types

        Returns:
            Dictionary mapping extensions to document type names
        """
        return {
            # PDF
            '.pdf': 'PDF Document',

            # Standard Image Formats
            '.png': 'PNG Image',
            '.jpg': 'JPEG Image',
            '.jpeg': 'JPEG Image',
            '.bmp': 'Bitmap Image',
            '.gif': 'GIF Image',

            # Scanned Document Formats
            '.tiff': 'TIFF Image (Multi-page support)',
            '.tif': 'TIFF Image (Multi-page support)',

            # Modern Image Formats
            '.webp': 'WebP Image',
            '.heic': 'HEIC Image (Apple)',
            '.heif': 'HEIF Image (Apple)',
            '.avif': 'AVIF Image (Next-gen)',

            # JPEG Variants
            '.jp2': 'JPEG 2000',
            '.j2k': 'JPEG 2000',
            '.jpe': 'JPEG',
            '.jfif': 'JPEG',

            # Professional/RAW Formats
            '.dng': 'Digital Negative (Adobe RAW)',
            '.raw': 'RAW Image',

            # Legacy Image Formats
            '.pcx': 'PC Paintbrush',
            '.tga': 'Truevision TGA',
            '.ico': 'Icon File',

            # Netpbm Formats
            '.pbm': 'Portable Bitmap',
            '.pgm': 'Portable Graymap',
            '.ppm': 'Portable Pixmap',
            '.pnm': 'Portable Anymap',

            # Vector Graphics (Rasterized)
            '.svg': 'SVG (Scalable Vector Graphics)',
            '.eps': 'EPS (Encapsulated PostScript)',

            # Office Documents
            '.doc': 'Word Document (Legacy)',
            '.docx': 'Word Document',
            '.xls': 'Excel Spreadsheet (Legacy)',
            '.xlsx': 'Excel Spreadsheet',
            '.xlsm': 'Excel Spreadsheet (Macro-enabled)',
            '.ppt': 'PowerPoint Presentation (Legacy)',
            '.pptx': 'PowerPoint Presentation',

            # Text Formats
            '.txt': 'Plain Text',
            '.rtf': 'Rich Text Format',
            '.md': 'Markdown',
            '.markdown': 'Markdown',
            '.html': 'HTML Document',
            '.htm': 'HTML Document',

            # Data Formats
            '.csv': 'CSV File',
            '.json': 'JSON File',
            '.xml': 'XML File',
        }


# Convenience function
def load_document(
    file_path: Optional[str] = None,
    file_content: Optional[bytes] = None,
    file_extension: Optional[str] = None,
    ocr_engine=None,
    loader_config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> LoadedDocument:
    """
    Convenience function to load a document

    Args:
        file_path: Path to the document
        file_content: Binary content of the document
        file_extension: File extension (required if file_content is provided)
        ocr_engine: OCR engine instance
        loader_config: Configuration for the loader
        **kwargs: Additional arguments for the loader

    Returns:
        LoadedDocument object
    """
    factory = DocumentLoaderFactory(ocr_engine=ocr_engine)
    return factory.load_document(
        file_path=file_path,
        file_content=file_content,
        file_extension=file_extension,
        loader_config=loader_config,
        **kwargs
    )


# Export main classes
__all__ = [
    'BaseDocumentLoader',
    'LoadedDocument',
    'DocumentType',
    'DocumentLoaderFactory',
    'load_document',
    'PDFLoader',
    'ImageLoader',
    'WordLoader',
    'ExcelLoader',
    'PowerPointLoader',
    'TextLoader',
    'RTFLoader',
    'MarkdownLoader',
    'HTMLLoader',
    'CSVLoader',
    'JSONLoader',
    'XMLLoader',
]
