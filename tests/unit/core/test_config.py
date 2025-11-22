"""
Unit tests for configuration module (app/core/config.py)
"""

import pytest
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "backend"))

from app.core.config import Settings


@pytest.mark.unit
class TestSettings:
    """Test application settings."""

    def test_default_settings(self):
        """Test default settings initialization."""
        settings = Settings()

        assert settings.APP_NAME == "SaaS OCR for Healthcare"
        assert settings.ENVIRONMENT in ["development", "production", "testing"]
        assert settings.MAX_PAGES_PER_DOCUMENT == 100

    def test_database_url(self, test_settings):
        """Test database URL configuration."""
        assert test_settings.DATABASE_URL is not None
        assert "postgresql" in test_settings.DATABASE_URL

    def test_secret_key_set(self, test_settings):
        """Test that secret key is set."""
        assert test_settings.SECRET_KEY is not None
        assert len(test_settings.SECRET_KEY) > 0

    def test_max_upload_size_bytes(self, test_settings):
        """Test max upload size calculation."""
        test_settings.MAX_UPLOAD_SIZE_MB = 10
        expected_bytes = 10 * 1024 * 1024

        assert test_settings.max_upload_size_bytes == expected_bytes

    def test_allowed_extensions_parsing(self, test_settings):
        """Test parsing of allowed file extensions."""
        assert isinstance(test_settings.ALLOWED_EXTENSIONS, list)
        assert "pdf" in test_settings.ALLOWED_EXTENSIONS
        assert "png" in test_settings.ALLOWED_EXTENSIONS

    def test_cors_origins_parsing(self, test_settings):
        """Test parsing of CORS origins."""
        assert isinstance(test_settings.CORS_ORIGINS, list)

    def test_storage_type(self, test_settings):
        """Test storage type configuration."""
        assert test_settings.STORAGE_TYPE in ["local", "s3", "minio"]

    def test_ocr_settings(self, test_settings):
        """Test OCR configuration."""
        assert hasattr(test_settings, "OCR_LANGUAGE")
        assert hasattr(test_settings, "OCR_USE_GPU")
        assert hasattr(test_settings, "OCR_BATCH_SIZE")

    def test_rate_limiting(self, test_settings):
        """Test rate limiting configuration."""
        assert test_settings.RATE_LIMIT_PER_MINUTE > 0
        assert test_settings.RATE_LIMIT_PER_HOUR > 0

    def test_hipaa_compliance_settings(self, test_settings):
        """Test HIPAA compliance settings."""
        assert hasattr(test_settings, "ENABLE_AUDIT_LOG")
        assert hasattr(test_settings, "AUDIT_LOG_RETENTION_DAYS")
        assert test_settings.AUDIT_LOG_RETENTION_DAYS >= 2555  # 7 years
