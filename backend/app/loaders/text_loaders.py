"""Loaders for text-based documents (TXT, RTF, MD, HTML, CSV, JSON, XML)"""
import os
from typing import List, Optional, Union, BinaryIO
import io
import logging
from .base import BaseDocumentLoader, LoadedDocument, DocumentType, DocumentChunk

logger = logging.getLogger(__name__)


class TextLoader(BaseDocumentLoader):
    """Loader for plain text files"""

    def __init__(self, encoding: str = 'utf-8', **kwargs):
        super().__init__(**kwargs)
        self.encoding = encoding

    def supported_extensions(self) -> List[str]:
        """Return supported file extensions"""
        return [".txt"]

    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """Load text file"""
        if not file_path and not file_content:
            raise ValueError("Either file_path or file_content must be provided")

        # Read content
        if file_path:
            with open(file_path, 'r', encoding=self.encoding, errors='ignore') as f:
                text_content = f.read()
            file_size = os.path.getsize(file_path)
        else:
            if isinstance(file_content, bytes):
                text_content = file_content.decode(self.encoding, errors='ignore')
                file_size = len(file_content)
            else:
                text_content = file_content.read()
                if isinstance(text_content, bytes):
                    text_content = text_content.decode(self.encoding, errors='ignore')
                file_size = len(text_content.encode(self.encoding))

        self.validate_file_size(file_size)

        metadata = self.extract_metadata(file_path)
        metadata.update({
            "encoding": self.encoding,
            "line_count": text_content.count('\n') + 1,
            "page_count": max(1, len(text_content) // 3000)
        })

        # Create chunks
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
                    metadata=chunk.metadata
                )
                for chunk in text_chunks
            ]

        return LoadedDocument(
            content=text_content,
            document_type=DocumentType.TEXT,
            file_size=file_size,
            page_count=metadata["page_count"],
            metadata=metadata,
            chunks=chunks
        )


class RTFLoader(BaseDocumentLoader):
    """Loader for Rich Text Format files"""

    def supported_extensions(self) -> List[str]:
        return [".rtf"]

    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """Load RTF file"""
        try:
            from striprtf.striprtf import rtf_to_text

            if file_path:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    rtf_content = f.read()
                file_size = os.path.getsize(file_path)
            else:
                if isinstance(file_content, bytes):
                    rtf_content = file_content.decode('utf-8', errors='ignore')
                    file_size = len(file_content)
                else:
                    rtf_content = file_content.read()
                    if isinstance(rtf_content, bytes):
                        rtf_content = rtf_content.decode('utf-8', errors='ignore')
                    file_size = len(rtf_content.encode('utf-8'))

            self.validate_file_size(file_size)

            # Convert RTF to plain text
            text_content = rtf_to_text(rtf_content)

            metadata = self.extract_metadata(file_path)
            metadata.update({
                "page_count": max(1, len(text_content) // 3000)
            })

            # Create chunks
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
                        metadata=chunk.metadata
                    )
                    for chunk in text_chunks
                ]

            return LoadedDocument(
                content=text_content,
                document_type=DocumentType.RTF,
                file_size=file_size,
                page_count=metadata["page_count"],
                metadata=metadata,
                chunks=chunks
            )

        except ImportError:
            logger.error("striprtf not available - install with: pip install striprtf")
            raise
        except Exception as e:
            logger.error(f"Failed to load RTF: {e}")
            raise


class MarkdownLoader(BaseDocumentLoader):
    """Loader for Markdown files"""

    def supported_extensions(self) -> List[str]:
        return [".md", ".markdown"]

    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """Load Markdown file"""
        # Markdown is essentially text, use TextLoader
        text_loader = TextLoader(
            max_file_size=self.max_file_size,
            enable_chunking=self.enable_chunking,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        doc = text_loader.load(file_path, file_content)
        doc.document_type = DocumentType.MARKDOWN

        return doc


class HTMLLoader(BaseDocumentLoader):
    """Loader for HTML files"""

    def supported_extensions(self) -> List[str]:
        return [".html", ".htm"]

    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """Load HTML file"""
        try:
            from bs4 import BeautifulSoup

            if file_path:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    html_content = f.read()
                file_size = os.path.getsize(file_path)
            else:
                if isinstance(file_content, bytes):
                    html_content = file_content.decode('utf-8', errors='ignore')
                    file_size = len(file_content)
                else:
                    html_content = file_content.read()
                    if isinstance(html_content, bytes):
                        html_content = html_content.decode('utf-8', errors='ignore')
                    file_size = len(html_content.encode('utf-8'))

            self.validate_file_size(file_size)

            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            # Get text
            text_content = soup.get_text(separator='\n', strip=True)

            metadata = self.extract_metadata(file_path)
            metadata.update({
                "title": soup.title.string if soup.title else None,
                "page_count": max(1, len(text_content) // 3000)
            })

            # Create chunks
            chunks = None
            if self.enable_chunking and text_content:
                from ..chunking.strategies import get_chunking_strategy
                chunker = get_chunking_strategy(
                    strategy_name="semantic",
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                )
                text_chunks = chunker.chunk(text_content, metadata)

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
                document_type=DocumentType.HTML,
                file_size=file_size,
                page_count=metadata["page_count"],
                metadata=metadata,
                chunks=chunks
            )

        except ImportError:
            logger.error("BeautifulSoup not available - install with: pip install beautifulsoup4")
            raise
        except Exception as e:
            logger.error(f"Failed to load HTML: {e}")
            raise


class CSVLoader(BaseDocumentLoader):
    """Loader for CSV files"""

    def supported_extensions(self) -> List[str]:
        return [".csv"]

    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """Load CSV file"""
        import csv

        if file_path:
            file_size = os.path.getsize(file_path)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        else:
            if isinstance(file_content, bytes):
                content = file_content.decode('utf-8', errors='ignore')
                file_size = len(file_content)
            else:
                content = file_content.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
                file_size = len(content.encode('utf-8'))

            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)

        self.validate_file_size(file_size)

        # Convert CSV to text format
        text_parts = []
        if rows:
            headers = list(rows[0].keys())
            text_parts.append("Headers: " + " | ".join(headers))
            text_parts.append("")

            for i, row in enumerate(rows, 1):
                row_text = " | ".join(str(row.get(h, '')) for h in headers)
                text_parts.append(f"Row {i}: {row_text}")

        text_content = "\n".join(text_parts)

        metadata = self.extract_metadata(file_path)
        metadata.update({
            "row_count": len(rows),
            "column_count": len(rows[0].keys()) if rows else 0,
            "page_count": max(1, len(rows) // 100)  # ~100 rows per page
        })

        # Create chunks
        chunks = None
        if self.enable_chunking and text_content:
            from ..chunking.strategies import get_chunking_strategy
            chunker = get_chunking_strategy(
                strategy_name="fixed_size",
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            text_chunks = chunker.chunk(text_content, metadata)

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
            document_type=DocumentType.CSV,
            file_size=file_size,
            page_count=metadata["page_count"],
            metadata=metadata,
            chunks=chunks
        )


class JSONLoader(BaseDocumentLoader):
    """Loader for JSON files"""

    def supported_extensions(self) -> List[str]:
        return [".json"]

    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """Load JSON file"""
        import json

        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            file_size = os.path.getsize(file_path)
        else:
            if isinstance(file_content, bytes):
                content = file_content.decode('utf-8')
                file_size = len(file_content)
            else:
                content = file_content.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                file_size = len(content.encode('utf-8'))

            data = json.loads(content)

        self.validate_file_size(file_size)

        # Convert JSON to readable text
        text_content = json.dumps(data, indent=2, ensure_ascii=False)

        metadata = self.extract_metadata(file_path)
        metadata.update({
            "page_count": max(1, len(text_content) // 3000)
        })

        # Create chunks
        chunks = None
        if self.enable_chunking and text_content:
            from ..chunking.strategies import get_chunking_strategy
            chunker = get_chunking_strategy(
                strategy_name="fixed_size",
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            text_chunks = chunker.chunk(text_content, metadata)

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
            document_type=DocumentType.JSON,
            file_size=file_size,
            page_count=metadata["page_count"],
            metadata=metadata,
            chunks=chunks,
            raw_data=data
        )


class XMLLoader(BaseDocumentLoader):
    """Loader for XML files"""

    def supported_extensions(self) -> List[str]:
        return [".xml"]

    def load(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[Union[bytes, BinaryIO]] = None,
        **kwargs
    ) -> LoadedDocument:
        """Load XML file"""
        import xml.etree.ElementTree as ET

        if file_path:
            tree = ET.parse(file_path)
            file_size = os.path.getsize(file_path)
        else:
            if isinstance(file_content, bytes):
                content = file_content
                file_size = len(file_content)
            else:
                content = file_content.read()
                if isinstance(content, str):
                    content = content.encode('utf-8')
                file_size = len(content)

            tree = ET.ElementTree(ET.fromstring(content))

        self.validate_file_size(file_size)

        root = tree.getroot()

        # Convert XML to readable text
        text_content = self._element_to_text(root)

        metadata = self.extract_metadata(file_path)
        metadata.update({
            "root_tag": root.tag,
            "page_count": max(1, len(text_content) // 3000)
        })

        # Create chunks
        chunks = None
        if self.enable_chunking and text_content:
            from ..chunking.strategies import get_chunking_strategy
            chunker = get_chunking_strategy(
                strategy_name="semantic",
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            text_chunks = chunker.chunk(text_content, metadata)

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
            document_type=DocumentType.XML,
            file_size=file_size,
            page_count=metadata["page_count"],
            metadata=metadata,
            chunks=chunks
        )

    def _element_to_text(self, element, level=0) -> str:
        """Recursively convert XML element to text"""
        indent = "  " * level
        text_parts = []

        # Add element tag
        text_parts.append(f"{indent}<{element.tag}>")

        # Add element text
        if element.text and element.text.strip():
            text_parts.append(f"{indent}  {element.text.strip()}")

        # Add children
        for child in element:
            text_parts.append(self._element_to_text(child, level + 1))

        return "\n".join(text_parts)
