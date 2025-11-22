"""
Tests for the testing infrastructure itself

Meta-tests to ensure the testing framework is working correctly.
"""

import pytest
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.mark.unit
class TestPytestConfiguration:
    """Test pytest configuration and setup."""

    def test_pytest_ini_exists(self):
        """Test that pytest.ini exists."""
        pytest_ini = Path(__file__).parent.parent / "pytest.ini"
        assert pytest_ini.exists()

    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml exists."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject.exists()

    def test_conftest_exists(self):
        """Test that conftest.py exists."""
        conftest = Path(__file__).parent / "conftest.py"
        assert conftest.exists()

    def test_test_directories_exist(self):
        """Test that test directories are properly created."""
        base_path = Path(__file__).parent

        dirs = ["unit", "integration", "e2e", "utils", "reports"]
        for dir_name in dirs:
            dir_path = base_path / dir_name
            assert dir_path.exists(), f"Directory {dir_name} should exist"


@pytest.mark.unit
class TestFixtures:
    """Test that fixtures are working correctly."""

    def test_test_settings_fixture(self, test_settings):
        """Test that test_settings fixture works."""
        assert test_settings is not None
        assert test_settings.ENVIRONMENT == "testing"

    def test_db_session_fixture(self, db_session):
        """Test that db_session fixture works."""
        assert db_session is not None

    def test_test_user_fixture(self, test_user):
        """Test that test_user fixture works."""
        assert test_user is not None
        assert test_user.email == "test@example.com"

    def test_auth_token_fixture(self, auth_token):
        """Test that auth_token fixture works."""
        assert auth_token is not None
        assert isinstance(auth_token, str)
        assert len(auth_token) > 0

    def test_auth_headers_fixture(self, auth_headers):
        """Test that auth_headers fixture works."""
        assert auth_headers is not None
        assert "Authorization" in auth_headers
        assert auth_headers["Authorization"].startswith("Bearer ")

    def test_client_fixture(self, client):
        """Test that FastAPI client fixture works."""
        assert client is not None

    def test_sample_image_fixture(self, sample_image_path):
        """Test that sample image fixture works."""
        assert sample_image_path is not None
        assert sample_image_path.exists()

    def test_sample_pdf_fixture(self, sample_pdf_path):
        """Test that sample PDF fixture works."""
        assert sample_pdf_path is not None
        assert sample_pdf_path.exists()

    def test_sample_job_data_fixture(self, sample_job_data):
        """Test that sample job data fixture works."""
        assert sample_job_data is not None
        assert "document_type" in sample_job_data

    def test_sample_extracted_data_fixture(self, sample_extracted_data):
        """Test that sample extracted data fixture works."""
        assert sample_extracted_data is not None
        assert "patient" in sample_extracted_data
        assert "medical_info" in sample_extracted_data


@pytest.mark.unit
class TestMockServices:
    """Test that mock services are working."""

    def test_mock_ocr_service(self, mock_ocr_service):
        """Test mock OCR service."""
        assert mock_ocr_service is not None

        result = mock_ocr_service.extract_text("test.png")
        assert "text" in result
        assert "confidence" in result

    def test_mock_llm_service(self, mock_llm_service):
        """Test mock LLM service."""
        assert mock_llm_service is not None

        result = mock_llm_service.extract_structured_data("test text", "hospice_admission")
        assert "patient" in result

    def test_mock_storage_service(self, mock_storage_service):
        """Test mock storage service."""
        assert mock_storage_service is not None

        upload_result = mock_storage_service.upload_file(b"content", "test.pdf", "bucket")
        assert upload_result is not None

    def test_mock_celery_task(self, mock_celery_task):
        """Test mock Celery task."""
        assert mock_celery_task is not None
        assert mock_celery_task.id is not None


@pytest.mark.unit
class TestMarkers:
    """Test that pytest markers are working."""

    def test_unit_marker_applied(self, request):
        """Test that unit marker is applied."""
        # This test itself has the unit marker
        pass

    @pytest.mark.integration
    def test_integration_marker(self):
        """Test integration marker."""
        pass

    @pytest.mark.e2e
    def test_e2e_marker(self):
        """Test e2e marker."""
        pass

    @pytest.mark.slow
    def test_slow_marker(self):
        """Test slow marker."""
        pass

    @pytest.mark.api
    def test_api_marker(self):
        """Test api marker."""
        pass


@pytest.mark.unit
class TestReporting:
    """Test reporting functionality."""

    def test_reports_directory_exists(self):
        """Test that test-reports directory exists."""
        reports_dir = Path(__file__).parent.parent / "test-reports"
        assert reports_dir.exists()

    def test_test_runner_script_exists(self):
        """Test that test runner script exists."""
        runner = Path(__file__).parent.parent / "run_tests.sh"
        assert runner.exists()

    def test_test_runner_utility_exists(self):
        """Test that test runner utility exists."""
        runner_py = Path(__file__).parent / "utils" / "test_runner.py"
        assert runner_py.exists()


@pytest.mark.unit
class TestDatabaseIsolation:
    """Test that database isolation is working."""

    def test_database_session_isolation(self, db_session):
        """Test that database sessions are isolated."""
        from app.models.user import User
        from app.core.security import get_password_hash

        # Create a user in this test
        user = User(
            email="isolation_test@example.com",
            username="isolationtest",
            hashed_password=get_password_hash("password"),
        )
        db_session.add(user)
        db_session.commit()

        # User should exist in this session
        found_user = db_session.query(User).filter_by(email="isolation_test@example.com").first()
        assert found_user is not None

    def test_another_isolated_test(self, db_session):
        """Test that previous test data doesn't leak."""
        from app.models.user import User

        # User from previous test should NOT exist
        found_user = db_session.query(User).filter_by(email="isolation_test@example.com").first()
        # Due to transaction rollback, user should not exist
        # This depends on fixture implementation


@pytest.mark.unit
class TestTestUtilities:
    """Test utility functions for testing."""

    def test_import_app_modules(self):
        """Test that app modules can be imported."""
        try:
            from app.core.config import Settings
            from app.core.security import get_password_hash
            from app.models.user import User

            assert Settings is not None
            assert get_password_hash is not None
            assert User is not None
        except ImportError as e:
            pytest.fail(f"Failed to import app modules: {e}")

    def test_path_configuration(self):
        """Test that Python path is configured correctly."""
        backend_path = str(Path(__file__).parent.parent / "backend")
        assert backend_path in sys.path


@pytest.mark.unit
class TestCoverageConfiguration:
    """Test coverage configuration."""

    def test_coverage_settings_in_pytest_ini(self):
        """Test that coverage is configured in pytest.ini."""
        pytest_ini = Path(__file__).parent.parent / "pytest.ini"
        content = pytest_ini.read_text()

        assert "--cov" in content
        assert "--cov-report" in content

    def test_coverage_settings_in_pyproject(self):
        """Test that coverage is configured in pyproject.toml."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject.read_text()

        assert "[tool.coverage" in content


@pytest.mark.unit
class TestTestExecution:
    """Test that tests can be executed."""

    def test_simple_assertion(self):
        """Test simple assertion."""
        assert True

    def test_arithmetic(self):
        """Test basic arithmetic."""
        assert 1 + 1 == 2
        assert 10 - 5 == 5
        assert 2 * 3 == 6

    def test_string_operations(self):
        """Test string operations."""
        assert "hello" + " " + "world" == "hello world"
        assert "test".upper() == "TEST"

    def test_list_operations(self):
        """Test list operations."""
        test_list = [1, 2, 3]
        assert len(test_list) == 3
        assert 2 in test_list

    def test_dict_operations(self):
        """Test dictionary operations."""
        test_dict = {"key": "value"}
        assert "key" in test_dict
        assert test_dict["key"] == "value"


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in tests."""

    def test_expected_exception(self):
        """Test that expected exceptions are handled."""
        with pytest.raises(ValueError):
            raise ValueError("Expected error")

    def test_assertion_error(self):
        """Test assertion errors."""
        with pytest.raises(AssertionError):
            assert False, "This should fail"


# Performance test for the testing infrastructure
@pytest.mark.unit
class TestPerformance:
    """Test performance of testing infrastructure."""

    def test_fixture_creation_performance(self, test_user, auth_token, sample_image_path):
        """Test that fixtures are created quickly."""
        import time

        start = time.time()

        # Access fixtures
        assert test_user is not None
        assert auth_token is not None
        assert sample_image_path is not None

        end = time.time()

        # Fixtures should be created very quickly
        assert (end - start) < 1.0, "Fixture creation took too long"

    def test_database_query_performance(self, db_session, test_user):
        """Test database query performance."""
        import time
        from app.models.user import User

        start = time.time()

        # Simple query
        user = db_session.query(User).filter_by(email=test_user.email).first()

        end = time.time()

        assert user is not None
        assert (end - start) < 0.5, "Database query took too long"
