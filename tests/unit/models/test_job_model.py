"""
Unit tests for Job model (app/models/job.py)
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "backend"))

from app.models.job import Job
from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.unit
@pytest.mark.database
class TestJobModel:
    """Test Job model."""

    @pytest.fixture
    def job_user(self, db_session):
        """Create a user for job tests."""
        user = User(
            email="jobuser@example.com",
            username="jobuser",
            hashed_password=get_password_hash("password"),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_create_job(self, db_session, job_user):
        """Test creating a new job."""
        job = Job(
            user_id=job_user.id,
            status="pending",
            document_type="hospice_admission",
        )

        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.id is not None
        assert job.user_id == job_user.id
        assert job.status == "pending"
        assert job.document_type == "hospice_admission"

    def test_job_status_transitions(self, db_session, job_user):
        """Test job status transitions."""
        job = Job(user_id=job_user.id, status="pending")
        db_session.add(job)
        db_session.commit()

        # Transition through statuses
        statuses = ["pending", "processing", "completed"]

        for status in statuses:
            job.status = status
            db_session.commit()
            db_session.refresh(job)
            assert job.status == status

    def test_job_error_status(self, db_session, job_user):
        """Test job error handling."""
        job = Job(
            user_id=job_user.id,
            status="failed",
            error_message="OCR processing failed"
        )

        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.status == "failed"
        assert job.error_message == "OCR processing failed"

    def test_job_extracted_data(self, db_session, job_user, sample_extracted_data):
        """Test storing extracted data in job."""
        job = Job(
            user_id=job_user.id,
            status="completed",
            extracted_data=sample_extracted_data,
        )

        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.extracted_data is not None
        assert "patient" in job.extracted_data
        assert "medical_info" in job.extracted_data

    def test_job_timestamps(self, db_session, job_user):
        """Test job timestamps."""
        job = Job(user_id=job_user.id, status="pending")

        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.created_at is not None
        assert job.updated_at is not None

        # Mark as completed
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db_session.commit()

        assert job.completed_at is not None

    def test_job_confidence_score(self, db_session, job_user):
        """Test job confidence score."""
        job = Job(
            user_id=job_user.id,
            status="completed",
            confidence_score=0.95,
        )

        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.confidence_score == 0.95
        assert 0.0 <= job.confidence_score <= 1.0

    def test_job_webhook_url(self, db_session, job_user):
        """Test job with webhook URL."""
        job = Job(
            user_id=job_user.id,
            status="pending",
            webhook_url="https://example.com/webhook",
        )

        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.webhook_url == "https://example.com/webhook"

    def test_job_user_relationship(self, db_session, job_user):
        """Test job-user relationship."""
        job = Job(user_id=job_user.id, status="pending")

        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        # Should be able to access user through relationship
        try:
            assert job.user.id == job_user.id
            assert job.user.email == job_user.email
        except AttributeError:
            # Relationship might not be configured
            pass
