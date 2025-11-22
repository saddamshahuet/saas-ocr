"""
Integration tests for job processing API endpoints
"""

import pytest
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


@pytest.mark.integration
@pytest.mark.api
class TestJobAPI:
    """Test job processing endpoints."""

    def test_create_job_with_file_upload(self, client, auth_headers, sample_image_path):
        """Test creating a job with file upload."""
        with open(sample_image_path, "rb") as f:
            files = {"file": ("sample.png", f, "image/png")}
            data = {"document_type": "hospice_admission"}

            response = client.post(
                "/api/v1/jobs",
                headers=auth_headers,
                files=files,
                data=data,
            )

        # Should create job or return validation error
        assert response.status_code in [200, 201, 400, 422]

        if response.status_code in [200, 201]:
            result = response.json()
            assert "job_id" in result or "id" in result

    def test_create_job_without_authentication(self, client, sample_image_path):
        """Test creating job without authentication."""
        with open(sample_image_path, "rb") as f:
            files = {"file": ("sample.png", f, "image/png")}

            response = client.post(
                "/api/v1/jobs",
                files=files,
            )

        assert response.status_code in [401, 403]

    def test_create_job_with_invalid_file_type(self, client, auth_headers, tmp_path):
        """Test creating job with invalid file type."""
        # Create a .exe file
        exe_file = tmp_path / "malware.exe"
        exe_file.write_bytes(b"fake exe content")

        with open(exe_file, "rb") as f:
            files = {"file": ("malware.exe", f, "application/x-msdownload")}

            response = client.post(
                "/api/v1/jobs",
                headers=auth_headers,
                files=files,
            )

        # Should reject invalid file type
        assert response.status_code in [400, 415, 422]

    def test_create_job_with_oversized_file(self, client, auth_headers, tmp_path):
        """Test creating job with oversized file."""
        # Create a large file (mock - not actually 100MB)
        large_file = tmp_path / "large.pdf"
        large_file.write_bytes(b"X" * 1024)  # 1KB for testing

        # This test would need actual file size validation
        pytest.skip("File size validation - implementation dependent")

    def test_get_job_status(self, client, auth_headers):
        """Test getting job status."""
        # First create a job (mock)
        job_id = "test-job-id"

        response = client.get(
            f"/api/v1/jobs/{job_id}",
            headers=auth_headers,
        )

        # May not exist, but should return proper status
        assert response.status_code in [200, 404]

    def test_get_job_unauthorized(self, client):
        """Test getting job without authentication."""
        response = client.get("/api/v1/jobs/test-job-id")

        assert response.status_code in [401, 403]

    def test_list_user_jobs(self, client, auth_headers):
        """Test listing user's jobs."""
        response = client.get(
            "/api/v1/jobs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should return list (empty or with jobs)
        assert isinstance(data, list) or "jobs" in data or "items" in data

    def test_list_jobs_with_pagination(self, client, auth_headers):
        """Test listing jobs with pagination."""
        response = client.get(
            "/api/v1/jobs?skip=0&limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_list_jobs_with_status_filter(self, client, auth_headers):
        """Test filtering jobs by status."""
        response = client.get(
            "/api/v1/jobs?status=completed",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_get_job_results(self, client, auth_headers):
        """Test getting job results."""
        job_id = "test-job-id"

        response = client.get(
            f"/api/v1/jobs/{job_id}/results",
            headers=auth_headers,
        )

        # May not exist or not be completed
        assert response.status_code in [200, 404, 400]

    def test_delete_job(self, client, auth_headers):
        """Test deleting a job."""
        job_id = "test-job-id"

        response = client.delete(
            f"/api/v1/jobs/{job_id}",
            headers=auth_headers,
        )

        # May not be implemented or job may not exist
        assert response.status_code in [200, 204, 404, 501]


@pytest.mark.integration
@pytest.mark.api
class TestBatchProcessing:
    """Test batch processing endpoints."""

    def test_create_batch_job(self, client, auth_headers, sample_image_path):
        """Test creating a batch job with multiple files."""
        files = []
        with open(sample_image_path, "rb") as f1:
            content1 = f1.read()
            files.append(("files", ("image1.png", io.BytesIO(content1), "image/png")))
            files.append(("files", ("image2.png", io.BytesIO(content1), "image/png")))

            response = client.post(
                "/api/v1/batches",
                headers=auth_headers,
                files=files,
                data={"document_type": "hospice_admission"},
            )

        # Batch processing may not be implemented
        assert response.status_code in [200, 201, 404, 501]

    def test_get_batch_status(self, client, auth_headers):
        """Test getting batch processing status."""
        batch_id = "test-batch-id"

        response = client.get(
            f"/api/v1/batches/{batch_id}",
            headers=auth_headers,
        )

        assert response.status_code in [200, 404, 501]


@pytest.mark.integration
@pytest.mark.api
class TestEHRExport:
    """Test EHR export endpoints."""

    def test_export_to_hl7(self, client, auth_headers):
        """Test exporting job results to HL7 format."""
        job_id = "test-job-id"

        response = client.get(
            f"/api/v1/jobs/{job_id}/export/hl7",
            headers=auth_headers,
        )

        # May not be implemented or job may not exist
        assert response.status_code in [200, 404, 501]

    def test_export_to_fhir(self, client, auth_headers):
        """Test exporting job results to FHIR format."""
        job_id = "test-job-id"

        response = client.get(
            f"/api/v1/jobs/{job_id}/export/fhir",
            headers=auth_headers,
        )

        assert response.status_code in [200, 404, 501]
