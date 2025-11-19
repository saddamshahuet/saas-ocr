"""Intelligent chunking strategies for large documents"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk"""
    content: str
    index: int
    total_chunks: int
    start_char: int
    end_char: int
    metadata: Optional[Dict] = None

    def __len__(self) -> int:
        return len(self.content)

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "index": self.index,
            "total_chunks": self.total_chunks,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "length": len(self.content),
            "metadata": self.metadata or {}
        }


class BaseChunkingStrategy(ABC):
    """Base class for chunking strategies"""

    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 200):
        """
        Initialize chunking strategy

        Args:
            chunk_size: Target size for each chunk
            chunk_overlap: Overlap between consecutive chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """
        Chunk text according to strategy

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of Chunk objects
        """
        pass


class FixedSizeChunking(BaseChunkingStrategy):
    """Simple fixed-size chunking with word boundary awareness"""

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """Chunk text into fixed-size chunks"""
        if len(text) <= self.chunk_size:
            return [Chunk(
                content=text,
                index=0,
                total_chunks=1,
                start_char=0,
                end_char=len(text),
                metadata=metadata
            )]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # If not at the end, try to break at word boundary
            if end < len(text):
                # Look for last space in the chunk
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space + 1

            chunk_content = text[start:end].strip()

            if chunk_content:  # Only add non-empty chunks
                chunks.append(Chunk(
                    content=chunk_content,
                    index=chunk_index,
                    total_chunks=0,  # Will update after
                    start_char=start,
                    end_char=end,
                    metadata=metadata
                ))
                chunk_index += 1

            # Move start position with overlap
            if end < len(text):
                start = end - self.chunk_overlap
            else:
                break

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks


class SentenceAwareChunking(BaseChunkingStrategy):
    """Chunking that preserves sentence boundaries"""

    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 200):
        super().__init__(chunk_size, chunk_overlap)
        # Improved sentence boundary detection
        self.sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """Chunk text preserving sentence boundaries"""
        # Split into sentences
        sentences = self.sentence_endings.split(text)

        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_size = 0
        start_char = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If single sentence exceeds chunk size, split it
            if sentence_len > self.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    content = ' '.join(current_chunk)
                    chunks.append(Chunk(
                        content=content,
                        index=len(chunks),
                        total_chunks=0,
                        start_char=start_char,
                        end_char=start_char + len(content),
                        metadata=metadata
                    ))
                    start_char += len(content)
                    current_chunk = []
                    current_size = 0

                # Split long sentence using fixed size
                fixed_chunker = FixedSizeChunking(self.chunk_size, self.chunk_overlap)
                sentence_chunks = fixed_chunker.chunk(sentence, metadata)
                for sc in sentence_chunks:
                    sc.index = len(chunks)
                    chunks.append(sc)
                continue

            # If adding this sentence exceeds chunk size, start new chunk
            if current_size + sentence_len > self.chunk_size and current_chunk:
                content = ' '.join(current_chunk)
                chunks.append(Chunk(
                    content=content,
                    index=len(chunks),
                    total_chunks=0,
                    start_char=start_char,
                    end_char=start_char + len(content),
                    metadata=metadata
                ))

                # Handle overlap
                if self.chunk_overlap > 0:
                    overlap_size = 0
                    overlap_sentences = []
                    for s in reversed(current_chunk):
                        if overlap_size + len(s) <= self.chunk_overlap:
                            overlap_sentences.insert(0, s)
                            overlap_size += len(s)
                        else:
                            break
                    current_chunk = overlap_sentences
                    current_size = overlap_size
                else:
                    current_chunk = []
                    current_size = 0

                start_char += len(content) - current_size

            current_chunk.append(sentence)
            current_size += sentence_len

        # Add remaining chunk
        if current_chunk:
            content = ' '.join(current_chunk)
            chunks.append(Chunk(
                content=content,
                index=len(chunks),
                total_chunks=0,
                start_char=start_char,
                end_char=start_char + len(content),
                metadata=metadata
            ))

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks


class SemanticChunking(BaseChunkingStrategy):
    """Semantic chunking based on document structure"""

    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 200):
        super().__init__(chunk_size, chunk_overlap)
        # Patterns for identifying section headers
        self.section_patterns = [
            re.compile(r'^#+\s+(.+)$', re.MULTILINE),  # Markdown headers
            re.compile(r'^[A-Z][A-Z\s]+:$', re.MULTILINE),  # ALL CAPS headers
            re.compile(r'^\d+\.\s+[A-Z]', re.MULTILINE),  # Numbered sections
            re.compile(r'^-{3,}$', re.MULTILINE),  # Horizontal rules
        ]

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """Chunk text based on semantic structure"""
        # Try to identify sections
        sections = self._identify_sections(text)

        if not sections:
            # Fall back to sentence-aware chunking
            return SentenceAwareChunking(self.chunk_size, self.chunk_overlap).chunk(text, metadata)

        chunks = []
        current_chunk = []
        current_size = 0
        start_char = 0

        for section_text in sections:
            section_len = len(section_text)

            # If section is larger than chunk size, split it
            if section_len > self.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    content = '\n\n'.join(current_chunk)
                    chunks.append(Chunk(
                        content=content,
                        index=len(chunks),
                        total_chunks=0,
                        start_char=start_char,
                        end_char=start_char + len(content),
                        metadata=metadata
                    ))
                    start_char += len(content)
                    current_chunk = []
                    current_size = 0

                # Split large section
                sentence_chunker = SentenceAwareChunking(self.chunk_size, self.chunk_overlap)
                section_chunks = sentence_chunker.chunk(section_text, metadata)
                for sc in section_chunks:
                    sc.index = len(chunks)
                    chunks.append(sc)
                continue

            # If adding this section exceeds chunk size, start new chunk
            if current_size + section_len > self.chunk_size and current_chunk:
                content = '\n\n'.join(current_chunk)
                chunks.append(Chunk(
                    content=content,
                    index=len(chunks),
                    total_chunks=0,
                    start_char=start_char,
                    end_char=start_char + len(content),
                    metadata=metadata
                ))
                start_char += len(content)
                current_chunk = []
                current_size = 0

            current_chunk.append(section_text)
            current_size += section_len

        # Add remaining chunk
        if current_chunk:
            content = '\n\n'.join(current_chunk)
            chunks.append(Chunk(
                content=content,
                index=len(chunks),
                total_chunks=0,
                start_char=start_char,
                end_char=start_char + len(content),
                metadata=metadata
            ))

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks if chunks else [Chunk(
            content=text,
            index=0,
            total_chunks=1,
            start_char=0,
            end_char=len(text),
            metadata=metadata
        )]

    def _identify_sections(self, text: str) -> List[str]:
        """Identify logical sections in the document"""
        # Look for section breaks
        sections = []
        current_pos = 0

        # Find all section boundaries
        boundaries = []
        for pattern in self.section_patterns:
            for match in pattern.finditer(text):
                boundaries.append(match.start())

        # Sort boundaries
        boundaries = sorted(set(boundaries))

        if not boundaries:
            return [text]

        # Extract sections
        for i, boundary in enumerate(boundaries):
            if i == 0 and boundary > 0:
                sections.append(text[0:boundary].strip())

            if i < len(boundaries) - 1:
                section = text[boundary:boundaries[i + 1]].strip()
            else:
                section = text[boundary:].strip()

            if section:
                sections.append(section)

        return sections


class SlidingWindowChunking(BaseChunkingStrategy):
    """Sliding window chunking with configurable stride"""

    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 200, stride: Optional[int] = None):
        super().__init__(chunk_size, chunk_overlap)
        self.stride = stride or (chunk_size - chunk_overlap)

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """Chunk text using sliding window"""
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_content = text[start:end].strip()

            if chunk_content:
                chunks.append(Chunk(
                    content=chunk_content,
                    index=chunk_index,
                    total_chunks=0,
                    start_char=start,
                    end_char=end,
                    metadata=metadata
                ))
                chunk_index += 1

            start += self.stride

            # Prevent infinite loop
            if self.stride == 0:
                break

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks


def get_chunking_strategy(
    strategy_name: str = "sentence_aware",
    chunk_size: int = 4000,
    chunk_overlap: int = 200
) -> BaseChunkingStrategy:
    """
    Factory function to get chunking strategy

    Args:
        strategy_name: Name of strategy (fixed_size, sentence_aware, semantic, sliding_window)
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks

    Returns:
        Chunking strategy instance
    """
    strategies = {
        "fixed_size": FixedSizeChunking,
        "sentence_aware": SentenceAwareChunking,
        "semantic": SemanticChunking,
        "sliding_window": SlidingWindowChunking,
    }

    strategy_class = strategies.get(strategy_name.lower())
    if not strategy_class:
        logger.warning(f"Unknown strategy '{strategy_name}', using sentence_aware")
        strategy_class = SentenceAwareChunking

    return strategy_class(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
