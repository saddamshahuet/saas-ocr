"""Layout analysis and understanding service

Provides document structure understanding, table extraction, form field detection,
section classification, and multi-column layout handling.
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import numpy as np

logger = logging.getLogger(__name__)


class LayoutElementType(Enum):
    """Types of layout elements"""
    TEXT = "text"
    TITLE = "title"
    HEADING = "heading"
    TABLE = "table"
    FIGURE = "figure"
    LIST = "list"
    FORM_FIELD = "form_field"
    CHECKBOX = "checkbox"
    SIGNATURE = "signature"
    FOOTER = "footer"
    HEADER = "header"
    COLUMN = "column"


@dataclass
class BoundingBox:
    """Bounding box coordinates"""
    x1: float  # Left
    y1: float  # Top
    x2: float  # Right
    y2: float  # Bottom

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_dict(self) -> Dict:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "width": self.width,
            "height": self.height
        }


@dataclass
class LayoutElement:
    """A layout element in a document"""
    element_type: LayoutElementType
    bbox: BoundingBox
    content: str = ""
    confidence: float = 0.0
    page_number: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "type": self.element_type.value,
            "bbox": self.bbox.to_dict(),
            "content": self.content,
            "confidence": self.confidence,
            "page_number": self.page_number,
            "metadata": self.metadata
        }


@dataclass
class TableCell:
    """A cell in a table"""
    row: int
    col: int
    content: str
    bbox: Optional[BoundingBox] = None
    is_header: bool = False

    def to_dict(self) -> Dict:
        return {
            "row": self.row,
            "col": self.col,
            "content": self.content,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "is_header": self.is_header
        }


@dataclass
class Table:
    """Extracted table structure"""
    rows: int
    cols: int
    cells: List[TableCell]
    bbox: Optional[BoundingBox] = None
    page_number: int = 1
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "cells": [cell.to_dict() for cell in self.cells],
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "page_number": self.page_number,
            "confidence": self.confidence
        }

    def to_dataframe(self):
        """Convert table to pandas DataFrame"""
        try:
            import pandas as pd

            # Group cells by row
            rows_dict = {}
            for cell in self.cells:
                if cell.row not in rows_dict:
                    rows_dict[cell.row] = {}
                rows_dict[cell.row][cell.col] = cell.content

            # Create DataFrame
            data = []
            for row_idx in sorted(rows_dict.keys()):
                row_data = []
                for col_idx in range(self.cols):
                    row_data.append(rows_dict[row_idx].get(col_idx, ""))
                data.append(row_data)

            return pd.DataFrame(data)

        except ImportError:
            logger.warning("pandas not installed. Install with: pip install pandas")
            return None


@dataclass
class LayoutAnalysisResult:
    """Result from layout analysis"""
    elements: List[LayoutElement]
    tables: List[Table]
    sections: List[Dict[str, Any]]
    columns_detected: bool = False
    num_columns: int = 1
    page_layout: str = "single"  # single, double, multi
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "elements": [elem.to_dict() for elem in self.elements],
            "tables": [table.to_dict() for table in self.tables],
            "sections": self.sections,
            "columns_detected": self.columns_detected,
            "num_columns": self.num_columns,
            "page_layout": self.page_layout,
            "metadata": self.metadata
        }


class LayoutAnalyzer:
    """Document layout analysis and understanding"""

    def __init__(
        self,
        use_layoutlm: bool = False,
        extract_tables: bool = True,
        detect_forms: bool = True,
        classify_sections: bool = True
    ):
        """
        Initialize layout analyzer

        Args:
            use_layoutlm: Use LayoutLMv3 for advanced layout understanding
            extract_tables: Enable table extraction
            detect_forms: Enable form field detection
            classify_sections: Enable section classification
        """
        self.use_layoutlm = use_layoutlm
        self.extract_tables = extract_tables
        self.detect_forms = detect_forms
        self.classify_sections = classify_sections

        self.layoutlm_model = None

        if self.use_layoutlm:
            self._initialize_layoutlm()

    def _initialize_layoutlm(self):
        """Initialize LayoutLMv3 model"""
        try:
            from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor

            self.layoutlm_processor = LayoutLMv3Processor.from_pretrained(
                "microsoft/layoutlmv3-base"
            )
            self.layoutlm_model = LayoutLMv3ForTokenClassification.from_pretrained(
                "microsoft/layoutlmv3-base"
            )

            logger.info("LayoutLMv3 model initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize LayoutLMv3: {e}")
            logger.info("Install with: pip install transformers torch")
            self.layoutlm_model = None

    def analyze_layout(
        self,
        file_path: Optional[str] = None,
        image: Optional[Any] = None,
        page_number: int = 1
    ) -> LayoutAnalysisResult:
        """
        Analyze document layout

        Args:
            file_path: Path to document file
            image: PIL Image object
            page_number: Page number

        Returns:
            LayoutAnalysisResult object
        """
        elements = []
        tables = []
        sections = []

        # Extract tables if enabled
        if self.extract_tables and file_path:
            tables = self._extract_tables(file_path, page_number)

        # Detect layout elements
        if image:
            elements = self._detect_layout_elements(image, page_number)

        # Detect columns
        columns_detected, num_columns = self._detect_columns(elements)

        # Classify sections
        if self.classify_sections:
            sections = self._classify_sections(elements)

        # Determine page layout type
        if num_columns == 1:
            page_layout = "single"
        elif num_columns == 2:
            page_layout = "double"
        else:
            page_layout = "multi"

        return LayoutAnalysisResult(
            elements=elements,
            tables=tables,
            sections=sections,
            columns_detected=columns_detected,
            num_columns=num_columns,
            page_layout=page_layout
        )

    def _extract_tables(
        self,
        file_path: str,
        page_number: int = 1
    ) -> List[Table]:
        """
        Extract tables from PDF

        Args:
            file_path: Path to PDF file
            page_number: Page number (0-indexed for pdfplumber)

        Returns:
            List of extracted tables
        """
        tables = []

        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                if page_number > len(pdf.pages):
                    return tables

                page = pdf.pages[page_number - 1]

                # Extract tables from page
                extracted_tables = page.extract_tables()

                for table_idx, table_data in enumerate(extracted_tables):
                    if not table_data:
                        continue

                    # Convert to Table object
                    rows = len(table_data)
                    cols = max(len(row) for row in table_data) if table_data else 0

                    cells = []
                    for row_idx, row in enumerate(table_data):
                        for col_idx, cell_content in enumerate(row):
                            if cell_content:
                                cells.append(TableCell(
                                    row=row_idx,
                                    col=col_idx,
                                    content=str(cell_content).strip(),
                                    is_header=(row_idx == 0)
                                ))

                    tables.append(Table(
                        rows=rows,
                        cols=cols,
                        cells=cells,
                        page_number=page_number,
                        confidence=0.85
                    ))

                logger.info(f"Extracted {len(tables)} tables from page {page_number}")

        except ImportError:
            logger.warning("pdfplumber not installed. Install with: pip install pdfplumber")
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")

        return tables

    def _detect_layout_elements(
        self,
        image: Any,
        page_number: int = 1
    ) -> List[LayoutElement]:
        """
        Detect layout elements in image

        Args:
            image: PIL Image object
            page_number: Page number

        Returns:
            List of detected layout elements
        """
        elements = []

        if self.layoutlm_model:
            elements = self._detect_with_layoutlm(image, page_number)
        else:
            # Fallback: basic layout detection
            elements = self._detect_basic_layout(image, page_number)

        return elements

    def _detect_with_layoutlm(
        self,
        image: Any,
        page_number: int = 1
    ) -> List[LayoutElement]:
        """
        Use LayoutLMv3 for layout detection

        Args:
            image: PIL Image object
            page_number: Page number

        Returns:
            List of layout elements
        """
        # This would require implementing LayoutLMv3 inference
        # For now, return empty list
        logger.info("LayoutLMv3 detection not yet implemented")
        return []

    def _detect_basic_layout(
        self,
        image: Any,
        page_number: int = 1
    ) -> List[LayoutElement]:
        """
        Basic layout detection using image processing

        Args:
            image: PIL Image object
            page_number: Page number

        Returns:
            List of layout elements
        """
        elements = []

        try:
            import cv2
            import numpy as np
            from PIL import Image

            # Convert PIL to OpenCV format
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            # Apply threshold
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

            # Find contours
            contours, _ = cv2.findContours(
                binary,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            height, width = gray.shape

            # Filter and classify contours
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)

                # Filter small elements
                if w < 10 or h < 10:
                    continue

                bbox = BoundingBox(
                    x1=float(x),
                    y1=float(y),
                    x2=float(x + w),
                    y2=float(y + h)
                )

                # Classify based on aspect ratio
                aspect_ratio = w / h if h > 0 else 0

                if aspect_ratio > 5:  # Wide horizontal elements
                    element_type = LayoutElementType.TEXT
                elif h > width * 0.8:  # Tall elements spanning page
                    element_type = LayoutElementType.COLUMN
                elif aspect_ratio < 0.2:  # Tall narrow elements
                    element_type = LayoutElementType.FIGURE
                else:
                    element_type = LayoutElementType.TEXT

                elements.append(LayoutElement(
                    element_type=element_type,
                    bbox=bbox,
                    page_number=page_number,
                    confidence=0.6
                ))

            logger.info(f"Detected {len(elements)} layout elements")

        except Exception as e:
            logger.error(f"Basic layout detection failed: {e}")

        return elements

    def _detect_columns(
        self,
        elements: List[LayoutElement]
    ) -> Tuple[bool, int]:
        """
        Detect multi-column layout

        Args:
            elements: List of layout elements

        Returns:
            Tuple of (columns_detected, num_columns)
        """
        if not elements:
            return False, 1

        # Group elements by horizontal position
        x_positions = [elem.bbox.x1 for elem in elements]

        if len(x_positions) < 3:
            return False, 1

        # Use clustering to detect columns
        try:
            from sklearn.cluster import DBSCAN
            import numpy as np

            X = np.array(x_positions).reshape(-1, 1)
            clustering = DBSCAN(eps=50, min_samples=2).fit(X)

            num_columns = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)

            if num_columns > 1:
                return True, num_columns
            else:
                return False, 1

        except ImportError:
            logger.warning("scikit-learn not installed for column detection")
            return False, 1
        except Exception as e:
            logger.error(f"Column detection failed: {e}")
            return False, 1

    def _classify_sections(
        self,
        elements: List[LayoutElement]
    ) -> List[Dict[str, Any]]:
        """
        Classify document sections

        Args:
            elements: List of layout elements

        Returns:
            List of classified sections
        """
        sections = []

        # Group elements vertically
        sorted_elements = sorted(elements, key=lambda e: e.bbox.y1)

        current_section = {
            "type": "body",
            "elements": [],
            "bbox": None
        }

        for elem in sorted_elements:
            # Simple heuristic: elements at top/bottom are headers/footers
            if elem.bbox.y1 < 100:  # Top of page
                current_section["type"] = "header"
            elif elem.bbox.y1 > 700:  # Bottom of page (assuming letter size)
                current_section["type"] = "footer"

            current_section["elements"].append(elem.to_dict())

        if current_section["elements"]:
            sections.append(current_section)

        return sections


# Singleton instance
_layout_analyzer = None


def get_layout_analyzer(
    use_layoutlm: bool = False,
    extract_tables: bool = True,
    detect_forms: bool = True,
    classify_sections: bool = True
) -> LayoutAnalyzer:
    """Get or create layout analyzer singleton"""
    global _layout_analyzer
    if _layout_analyzer is None:
        _layout_analyzer = LayoutAnalyzer(
            use_layoutlm=use_layoutlm,
            extract_tables=extract_tables,
            detect_forms=detect_forms,
            classify_sections=classify_sections
        )
    return _layout_analyzer
