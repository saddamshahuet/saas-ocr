"""
Unit tests for security module (app/core/security.py)
"""

import pytest
from datetime import timedelta
from jose import jwt

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "backend"))

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)
from app.core.config import Settings


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "mysecretpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_correct_password(self):
        """Test verification of correct password."""
        password = "correctpassword"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verification of incorrect password."""
        password = "correctpassword"
        hashed = get_password_hash(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "samepassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self, test_settings):
        """Test JWT token creation."""
        data = {"sub": "user@example.com"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_expiry(self, test_settings):
        """Test token creation with custom expiry."""
        data = {"sub": "user@example.com"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)

        assert isinstance(token, str)

        # Decode and check expiry
        settings = Settings()
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert "exp" in payload

    def test_decode_valid_token(self, test_settings):
        """Test decoding valid JWT token."""
        email = "test@example.com"
        data = {"sub": email}
        token = create_access_token(data)

        decoded_email = decode_access_token(token)
        assert decoded_email == email

    def test_decode_invalid_token(self, test_settings):
        """Test decoding invalid token."""
        invalid_token = "invalid.token.here"
        decoded = decode_access_token(invalid_token)

        assert decoded is None

    def test_decode_expired_token(self, test_settings):
        """Test decoding expired token."""
        data = {"sub": "user@example.com"}
        # Create token that expires immediately
        token = create_access_token(data, timedelta(seconds=-1))

        decoded = decode_access_token(token)
        assert decoded is None

    def test_token_contains_correct_data(self, test_settings):
        """Test that token contains correct payload data."""
        email = "user@example.com"
        custom_data = {"sub": email, "role": "admin"}
        token = create_access_token(custom_data)

        settings = Settings()
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        assert payload["sub"] == email
        assert payload["role"] == "admin"
        assert "exp" in payload
