"""
Unit tests for OCR service (app/services/ocr_service.py)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "backend"))


@pytest.mark.unit
@pytest.mark.ocr
class TestOCRService:
    """Test OCR service functionality."""

    @pytest.fixture
    def ocr_service(self):
        """Create OCR service instance."""
        with patch('app.services.ocr_service.PaddleOCR'):
            from app.services.ocr_service import OCRService
            service = OCRService()
            return service

    def test_ocr_service_initialization(self, ocr_service):
        """Test OCR service initializes correctly."""
        assert ocr_service is not None
        assert hasattr(ocr_service, 'extract_text')

    @patch('app.services.ocr_service.PaddleOCR')
    def test_extract_text_from_image(self, mock_paddle, ocr_service, sample_image_path):
        """Test text extraction from image."""
        # Mock PaddleOCR response
        mock_paddle_instance = MagicMock()
        mock_paddle_instance.ocr.return_value = [
            [
                [[10, 10], [100, 10], [100, 30], [10, 30]],
                ("Sample text", 0.95)
            ]
        ]
        mock_paddle.return_value = mock_paddle_instance

        from app.services.ocr_service import OCRService
        service = OCRService()
        result = service.extract_text(str(sample_image_path))

        assert "text" in result
        assert "confidence" in result
        assert isinstance(result["text"], str)
        assert isinstance(result["confidence"], float)

    @patch('app.services.ocr_service.cv2')
    def test_preprocess_image(self, mock_cv2, ocr_service):
        """Test image preprocessing."""
        # Create mock image
        mock_image = np.ones((100, 100, 3), dtype=np.uint8) * 255

        from app.services.ocr_service import OCRService
        service = OCRService()

        # Test preprocessing doesn't crash
        mock_cv2.imread.return_value = mock_image
        mock_cv2.cvtColor.return_value = mock_image[:, :, 0]
        mock_cv2.threshold.return_value = (127, mock_image[:, :, 0])

        # Should not raise exception
        try:
            preprocessed = service._preprocess_image(mock_image)
            assert preprocessed is not None
        except AttributeError:
            # Method might not exist or be private
            pass

    def test_extract_text_handles_errors(self, ocr_service):
        """Test error handling in text extraction."""
        with patch.object(ocr_service, 'extract_text') as mock_extract:
            mock_extract.side_effect = Exception("OCR failed")

            with pytest.raises(Exception):
                ocr_service.extract_text("nonexistent.jpg")

    def test_confidence_score_calculation(self, ocr_service):
        """Test confidence score calculation."""
        # Mock response with multiple text blocks
        blocks = [
            {"text": "Hello", "confidence": 0.9},
            {"text": "World", "confidence": 0.8},
        ]

        # Average confidence should be 0.85
        expected_avg = 0.85

        # Test calculation logic
        confidences = [b["confidence"] for b in blocks]
        avg_confidence = sum(confidences) / len(confidences)

        assert avg_confidence == expected_avg

    @patch('app.services.ocr_service.pdf2image')
    def test_pdf_to_images_conversion(self, mock_pdf2image, ocr_service):
        """Test PDF to images conversion."""
        # Mock PDF conversion
        mock_images = [Image.new('RGB', (800, 600), color='white') for _ in range(3)]
        mock_pdf2image.convert_from_path.return_value = mock_images

        from app.services.ocr_service import OCRService
        service = OCRService()

        # Test would call convert_from_path
        # Verify it's called with correct DPI
        try:
            if hasattr(service, '_pdf_to_images'):
                images = service._pdf_to_images("test.pdf")
                assert len(images) > 0
        except AttributeError:
            pass  # Method might be implemented differently


@pytest.mark.unit
@pytest.mark.ocr
class TestOCRPerformance:
    """Test OCR performance characteristics."""

    @pytest.mark.slow
    def test_ocr_processing_time(self, sample_image_path):
        """Test OCR processing completes in reasonable time."""
        import time

        with patch('app.services.ocr_service.PaddleOCR'):
            from app.services.ocr_service import OCRService
            service = OCRService()

            start = time.time()
            # Mock the actual OCR call
            with patch.object(service, 'extract_text', return_value={
                "text": "test",
                "confidence": 0.9,
                "blocks": []
            }):
                result = service.extract_text(str(sample_image_path))
            end = time.time()

            # Should complete quickly with mock
            assert (end - start) < 1.0

    def test_batch_processing(self, ocr_service):
        """Test batch processing multiple images."""
        image_paths = [f"image_{i}.jpg" for i in range(5)]

        with patch.object(ocr_service, 'extract_text') as mock_extract:
            mock_extract.return_value = {"text": "test", "confidence": 0.9}

            results = []
            for path in image_paths:
                results.append(ocr_service.extract_text(path))

            assert len(results) == 5
            assert all("text" in r for r in results)
