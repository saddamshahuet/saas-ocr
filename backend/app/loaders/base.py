"""Base document loader interface"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, BinaryIO, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Supported document types"""
    PDF = "pdf"
    IMAGE = "image"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    TEXT = "text"
    HTML = "html"
    EMAIL = "email"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    MARKDOWN = "markdown"
    RTF = "rtf"


@dataclass
class DocumentChunk:
    """Represents a chunk of a document"""
    content: str
    chunk_index: int
    total_chunks: int
    page_number: Optional[int] = None
    metadata: Optional[Dict] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "page_number": self.page_number,
            "metadata": self.metadata or {},
            "confidence": self.confidence
        }


@dataclass
class LoadedDocument:
    """Represents a loaded document with all its content"""
    content: str
    document_type: DocumentType
    file_size: int
    page_count: int
    metadata: Dict
    chunks: Optional[List[DocumentChunk]] = None
    raw_data: Optional[bytes] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "content": self.content,
            "document_type": self.document_type.value,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "metadata": self.metadata,
            "chunks": [chunk.to_dict() for chunk in self.chunks] if self.chunks else [],
            "has_raw_data": self.raw_data is not None
        }


class BaseDocumentLoader(ABC):
    """Abstract base class for document loaders"""

    def __init__(
        self,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB default
        enable_chunking: bool = True,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        """
        Initialize document loader

        Args:
            max_file_size: Maximum file size in bytes
            enable_chunking: Whether to enable chunking for large documents
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks
            **kwargs: Additional loader-specific arguments
        """
        self.max_file_size = max_file_size
        self.enable_chunking = enable_chunking
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions"""
        pass

    @abstractmethod
    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """
        Load document from file path or content

        Args:
            file_path: Path to the document file
            file_content: Binary content of the document
            **kwargs: Additional loader-specific arguments

        Returns:
            LoadedDocument object
        """
        pass

    def validate_file_size(self, file_size: int) -> bool:
        """Validate file size against maximum allowed"""
        if file_size > self.max_file_size:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds maximum allowed "
                f"({self.max_file_size} bytes)"
            )
        return True

    def create_chunks(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ) -> List[DocumentChunk]:
        """
        Create chunks from content

        Args:
            content: Full document content
            metadata: Optional metadata to include in chunks

        Returns:
            List of DocumentChunk objects
        """
        if not self.enable_chunking or len(content) <= self.chunk_size:
            return [DocumentChunk(
                content=content,
                chunk_index=0,
                total_chunks=1,
                metadata=metadata
            )]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(content):
            end = start + self.chunk_size

            # If not the last chunk, try to break at word boundary
            if end < len(content):
                # Look for last space in the chunk
                last_space = content.rfind(' ', start, end)
                if last_space > start:
                    end = last_space + 1

            chunk_content = content[start:end]
            chunks.append(DocumentChunk(
                content=chunk_content,
                chunk_index=chunk_index,
                total_chunks=0,  # Will be updated after all chunks are created
                metadata=metadata
            ))

            # Move start position with overlap
            start = end - self.chunk_overlap if end < len(content) else end
            chunk_index += 1

        # Update total_chunks for all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total_chunks

        return chunks

    def extract_metadata(self, file_path: Optional[str] = None) -> Dict:
        """
        Extract metadata from document

        Args:
            file_path: Path to the document

        Returns:
            Dictionary of metadata
        """
        import os
        from datetime import datetime

        metadata = {
            "loader": self.__class__.__name__,
            "loaded_at": datetime.utcnow().isoformat()
        }

        if file_path:
            metadata.update({
                "filename": os.path.basename(file_path),
                "file_path": file_path,
                "file_extension": os.path.splitext(file_path)[1].lower()
            })

        return metadata
