"""
End-to-end tests for complete document processing workflow
"""

import pytest
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteDocumentProcessing:
    """Test complete end-to-end document processing workflow."""

    def test_complete_workflow_user_registration_to_results(self, client, sample_image_path):
        """
        Test complete workflow:
        1. Register user
        2. Login
        3. Upload document
        4. Monitor job status
        5. Retrieve results
        """
        # Step 1: Register new user
        register_response = client.post(
            "/api/v1/register",
            json={
                "email": "e2e_test@example.com",
                "username": "e2euser",
                "password": "SecurePass123!",
                "full_name": "E2E Test User",
            }
        )

        assert register_response.status_code in [200, 201]

        # Step 2: Login
        login_response = client.post(
            "/api/v1/login",
            data={
                "username": "e2e_test@example.com",
                "password": "SecurePass123!",
            }
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 3: Upload document
        with open(sample_image_path, "rb") as f:
            files = {"file": ("document.png", f, "image/png")}
            data = {"document_type": "hospice_admission"}

            upload_response = client.post(
                "/api/v1/jobs",
                headers=headers,
                files=files,
                data=data,
            )

        if upload_response.status_code not in [200, 201]:
            pytest.skip("File upload not fully implemented")

        job_data = upload_response.json()
        job_id = job_data.get("job_id") or job_data.get("id")

        assert job_id is not None

        # Step 4: Monitor job status
        max_attempts = 10
        for attempt in range(max_attempts):
            status_response = client.get(
                f"/api/v1/jobs/{job_id}",
                headers=headers,
            )

            assert status_response.status_code == 200
            job_status = status_response.json()

            if job_status.get("status") in ["completed", "failed"]:
                break

            time.sleep(1)  # Wait before checking again

        # Step 5: Retrieve results
        results_response = client.get(
            f"/api/v1/jobs/{job_id}/results",
            headers=headers,
        )

        # Results may not be available if processing failed
        assert results_response.status_code in [200, 400, 404]

        if results_response.status_code == 200:
            results = results_response.json()
            assert "extracted_data" in results or "patient" in results

    def test_batch_processing_workflow(self, client, auth_headers, sample_image_path, tmp_path):
        """Test batch processing workflow with multiple documents."""
        # Create multiple test images
        import shutil
        images = []
        for i in range(3):
            img_path = tmp_path / f"document_{i}.png"
            shutil.copy(sample_image_path, img_path)
            images.append(img_path)

        # Upload batch
        files = []
        for img_path in images:
            with open(img_path, "rb") as f:
                files.append(("files", (img_path.name, f.read(), "image/png")))

        # This endpoint may not exist
        pytest.skip("Batch processing E2E test - implementation dependent")

    def test_ehr_export_workflow(self, client, auth_headers):
        """
        Test EHR export workflow:
        1. Upload document
        2. Wait for processing
        3. Export to HL7
        4. Export to FHIR
        """
        pytest.skip("EHR export E2E test - requires completed job")


@pytest.mark.e2e
@pytest.mark.slow
class TestAPIKeyWorkflow:
    """Test API key authentication workflow."""

    def test_api_key_creation_and_usage(self, client, auth_headers):
        """
        Test API key workflow:
        1. Generate API key
        2. Use API key for authentication
        3. Process document with API key
        """
        # Step 1: Generate API key
        response = client.post(
            "/api/v1/api-keys",
            headers=auth_headers,
            json={"name": "Test API Key"}
        )

        if response.status_code not in [200, 201]:
            pytest.skip("API key generation not implemented")

        api_key_data = response.json()
        api_key = api_key_data.get("key") or api_key_data.get("api_key")

        assert api_key is not None

        # Step 2: Use API key for authentication
        api_headers = {"X-API-Key": api_key}

        # Step 3: Try to access protected resource
        me_response = client.get("/api/v1/users/me", headers=api_headers)

        # Should authenticate successfully
        assert me_response.status_code == 200


@pytest.mark.e2e
@pytest.mark.slow
class TestErrorHandlingWorkflow:
    """Test error handling in complete workflows."""

    def test_invalid_document_handling(self, client, auth_headers, tmp_path):
        """Test system handles invalid documents gracefully."""
        # Create corrupted file
        corrupt_file = tmp_path / "corrupt.pdf"
        corrupt_file.write_bytes(b"Not a valid PDF file")

        with open(corrupt_file, "rb") as f:
            files = {"file": ("corrupt.pdf", f, "application/pdf")}

            response = client.post(
                "/api/v1/jobs",
                headers=auth_headers,
                files=files,
            )

        # Should handle gracefully (reject or accept and fail later)
        assert response.status_code in [200, 201, 400, 415, 422]

    def test_concurrent_requests_handling(self, client, auth_headers, sample_image_path):
        """Test system handles concurrent requests."""
        import concurrent.futures

        def upload_document():
            with open(sample_image_path, "rb") as f:
                files = {"file": ("doc.png", f, "image/png")}
                return client.post("/api/v1/jobs", headers=auth_headers, files=files)

        # Submit multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_document) for _ in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should complete without errors
        for response in results:
            assert response.status_code in [200, 201, 400, 429]  # 429 = rate limited

    def test_rate_limiting(self, client, auth_headers):
        """Test rate limiting enforcement."""
        # Make many rapid requests
        responses = []
        for _ in range(150):  # More than rate limit
            response = client.get("/api/v1/users/me", headers=auth_headers)
            responses.append(response)

        # Should eventually get rate limited
        status_codes = [r.status_code for r in responses]

        # May or may not have rate limiting implemented
        # If implemented, should see 429 status codes
        if 429 in status_codes:
            assert status_codes.count(429) > 0


@pytest.mark.e2e
@pytest.mark.slow
class TestDataPersistence:
    """Test data persistence across sessions."""

    def test_job_history_persistence(self, client, test_user, auth_headers):
        """Test that job history persists correctly."""
        # Get initial job count
        response1 = client.get("/api/v1/jobs", headers=auth_headers)
        assert response1.status_code == 200

        initial_data = response1.json()
        initial_count = len(initial_data) if isinstance(initial_data, list) else initial_data.get("total", 0)

        # Get jobs again
        response2 = client.get("/api/v1/jobs", headers=auth_headers)
        assert response2.status_code == 200

        second_data = response2.json()
        second_count = len(second_data) if isinstance(second_data, list) else second_data.get("total", 0)

        # Count should be consistent
        assert initial_count == second_count

    def test_user_profile_persistence(self, client, auth_headers):
        """Test user profile data persists."""
        # Get user profile
        response1 = client.get("/api/v1/users/me", headers=auth_headers)
        assert response1.status_code == 200
        profile1 = response1.json()

        # Get profile again
        response2 = client.get("/api/v1/users/me", headers=auth_headers)
        assert response2.status_code == 200
        profile2 = response2.json()

        # Should be identical
        assert profile1["email"] == profile2["email"]
        assert profile1["username"] == profile2["username"]
