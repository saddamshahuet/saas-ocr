"""
Unit tests for User model (app/models/user.py)
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "backend"))

from app.models.user import User
from app.core.security import verify_password, get_password_hash


@pytest.mark.unit
@pytest.mark.database
class TestUserModel:
    """Test User model."""

    def test_create_user(self, db_session):
        """Test creating a new user."""
        user = User(
            email="newuser@example.com",
            username="newuser",
            hashed_password=get_password_hash("password123"),
            full_name="New User",
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_user_password_hashing(self, db_session):
        """Test that passwords are properly hashed."""
        password = "securepassword123"
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash(password),
            full_name="Test User",
        )

        # Password should be hashed
        assert user.hashed_password != password
        # Should be able to verify
        assert verify_password(password, user.hashed_password)

    def test_user_timestamps(self, db_session):
        """Test that timestamps are automatically set."""
        user = User(
            email="timestamp@example.com",
            username="timestampuser",
            hashed_password=get_password_hash("password"),
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_user_unique_email(self, db_session, test_user):
        """Test that email must be unique."""
        duplicate_user = User(
            email=test_user.email,  # Same email
            username="different",
            hashed_password=get_password_hash("password"),
        )

        db_session.add(duplicate_user)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_user_unique_username(self, db_session, test_user):
        """Test that username must be unique."""
        duplicate_user = User(
            email="different@example.com",
            username=test_user.username,  # Same username
            hashed_password=get_password_hash("password"),
        )

        db_session.add(duplicate_user)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_user_subscription_tiers(self, db_session):
        """Test different subscription tiers."""
        tiers = ["free", "starter", "pro", "enterprise"]

        for tier in tiers:
            user = User(
                email=f"{tier}@example.com",
                username=f"{tier}user",
                hashed_password=get_password_hash("password"),
                subscription_tier=tier,
            )

            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            assert user.subscription_tier == tier

    def test_user_api_calls_remaining(self, db_session):
        """Test API calls remaining tracking."""
        user = User(
            email="apicalls@example.com",
            username="apiuser",
            hashed_password=get_password_hash("password"),
            api_calls_remaining=1000,
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.api_calls_remaining == 1000

        # Decrease API calls
        user.api_calls_remaining -= 1
        db_session.commit()

        assert user.api_calls_remaining == 999

    def test_user_is_active_flag(self, db_session):
        """Test user active/inactive status."""
        user = User(
            email="inactive@example.com",
            username="inactiveuser",
            hashed_password=get_password_hash("password"),
            is_active=False,
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.is_active is False

    def test_user_superuser_flag(self, db_session):
        """Test superuser flag."""
        admin = User(
            email="admin@example.com",
            username="adminuser",
            hashed_password=get_password_hash("password"),
            is_superuser=True,
        )

        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

        assert admin.is_superuser is True

    def test_user_string_representation(self, test_user):
        """Test user string representation."""
        user_str = str(test_user)
        # Should contain email or username
        assert test_user.email in user_str or test_user.username in user_str
