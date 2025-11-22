"""
Global pytest configuration and fixtures

This module provides shared fixtures and configuration for all test suites.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Try to import app modules, but allow tests to run even if imports fail
try:
    from app.core.config import Settings
    from app.core.database import Base, get_db
    from app.core.security import create_access_token, get_password_hash
    from app.models.user import User
    APP_IMPORTS_AVAILABLE = True
except Exception as e:
    # If imports fail (e.g., due to missing dependencies), create placeholders
    print(f"Warning: Could not import app modules: {e}")
    APP_IMPORTS_AVAILABLE = False
    Settings = None
    Base = None
    get_db = None
    create_access_token = None
    get_password_hash = None
    User = None


# Test Database Configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/saas_ocr_test"
)
TEST_DATABASE_URL_ASYNC = os.getenv(
    "TEST_DATABASE_URL_ASYNC",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/saas_ocr_test"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing."""
    if not APP_IMPORTS_AVAILABLE:
        pytest.skip("App imports not available")

    from app.core.config import Settings

    return Settings(
        DATABASE_URL=TEST_DATABASE_URL,
        SECRET_KEY="test-secret-key-for-testing-only",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        ENVIRONMENT="testing",
        DEBUG=True,
        STORAGE_TYPE="local",
        REDIS_URL="redis://localhost:6379/1",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        ENABLE_AUDIT_LOG=False,  # Disable for testing speed
        OCR_USE_GPU=False,  # Use CPU for testing
        LLM_USE_GPU=False,
    )


@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    _engine = create_engine(
        TEST_DATABASE_URL,
        poolclass=pool.NullPool,  # Disable connection pooling for tests
        echo=False,
    )

    # Create all tables
    Base.metadata.create_all(bind=_engine)

    yield _engine

    # Drop all tables after tests
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


@pytest.fixture(scope="session")
async def async_engine():
    """Create async test database engine."""
    _engine = create_async_engine(
        TEST_DATABASE_URL_ASYNC,
        poolclass=pool.NullPool,
        echo=False,
    )

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await _engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
async def async_db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async with async_engine.connect() as connection:
        async with connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)

            yield session

            await session.close()
            await transaction.rollback()


@pytest.fixture(scope="function")
def test_user(db_session: Session):
    """Create a test user."""
    if not APP_IMPORTS_AVAILABLE:
        pytest.skip("App imports not available")

    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        subscription_tier="pro",
        api_calls_remaining=1000,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def superuser(db_session: Session):
    """Create a test superuser."""
    if not APP_IMPORTS_AVAILABLE:
        pytest.skip("App imports not available")

    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
        subscription_tier="enterprise",
        api_calls_remaining=10000,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(test_user) -> str:
    """Generate JWT token for test user."""
    if not APP_IMPORTS_AVAILABLE:
        pytest.skip("App imports not available")

    return create_access_token(
        data={"sub": test_user.email},
        expires_delta=timedelta(minutes=30)
    )


@pytest.fixture(scope="function")
def auth_headers(auth_token: str) -> dict:
    """Generate authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def client(db_session: Session, test_settings) -> TestClient:
    """Create FastAPI test client."""
    if not APP_IMPORTS_AVAILABLE:
        pytest.skip("App imports not available")

    from app.main_v2 import app

    # Override database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(async_db_session: AsyncSession, test_settings) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    if not APP_IMPORTS_AVAILABLE:
        pytest.skip("App imports not available")

    from app.main_v2 import app

    async def override_get_db():
        try:
            yield async_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_ocr_service():
    """Mock OCR service for testing."""
    mock = Mock()
    mock.extract_text.return_value = {
        "text": "Sample extracted text",
        "confidence": 0.95,
        "blocks": [
            {"text": "Sample", "confidence": 0.96, "bbox": [10, 10, 100, 30]},
            {"text": "extracted", "confidence": 0.94, "bbox": [110, 10, 200, 30]},
            {"text": "text", "confidence": 0.95, "bbox": [210, 10, 260, 30]},
        ]
    }
    return mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing."""
    mock = Mock()
    mock.extract_structured_data.return_value = {
        "patient": {
            "name": "John Doe",
            "date_of_birth": "1980-01-15",
            "mrn": "MRN123456",
        },
        "medical_info": {
            "diagnosis": "Hypertension",
            "medications": ["Lisinopril 10mg"],
        },
        "confidence_scores": {
            "patient.name": 0.95,
            "patient.date_of_birth": 0.90,
        }
    }
    return mock


@pytest.fixture
def mock_storage_service():
    """Mock storage service for testing."""
    mock = Mock()
    mock.upload_file.return_value = "test-bucket/test-file.pdf"
    mock.download_file.return_value = b"mock file content"
    mock.delete_file.return_value = True
    mock.generate_presigned_url.return_value = "https://storage.example.com/presigned-url"
    return mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    mock = MagicMock()
    mock.id = "test-task-id-12345"
    mock.state = "SUCCESS"
    mock.result = {"status": "completed"}
    mock.apply_async.return_value = mock
    return mock


@pytest.fixture
def sample_pdf_path(tmp_path) -> Path:
    """Create a sample PDF file for testing."""
    from PIL import Image

    # Create a simple image
    img = Image.new('RGB', (800, 600), color='white')

    # Save as temp file
    pdf_path = tmp_path / "sample.pdf"
    img.save(pdf_path, "PDF")

    return pdf_path


@pytest.fixture
def sample_image_path(tmp_path) -> Path:
    """Create a sample image for testing."""
    from PIL import Image, ImageDraw, ImageFont

    # Create image with text
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)

    # Add sample text
    text = "Sample Medical Document\n\nPatient: John Doe\nDOB: 01/15/1980\nMRN: 123456"
    draw.text((50, 50), text, fill='black')

    # Save
    img_path = tmp_path / "sample.png"
    img.save(img_path)

    return img_path


@pytest.fixture
def sample_job_data() -> dict:
    """Sample job data for testing."""
    return {
        "document_type": "hospice_admission",
        "schema_template_id": None,
        "webhook_url": None,
        "metadata": {
            "source": "test",
            "batch_id": None,
        }
    }


@pytest.fixture
def sample_extracted_data() -> dict:
    """Sample extracted data for testing."""
    return {
        "patient": {
            "name": "John Doe",
            "date_of_birth": "1980-01-15",
            "mrn": "MRN123456",
            "phone": "555-1234",
            "address": "123 Main St, Anytown, USA"
        },
        "medical_info": {
            "diagnosis": "End-stage heart failure",
            "medications": ["Lisinopril 10mg daily", "Metoprolol 25mg BID"],
            "allergies": ["Penicillin"],
            "dnr_status": "Full code",
        },
        "provider": {
            "physician_name": "Dr. Jane Smith",
            "facility": "Memorial Hospital",
            "phone": "555-5678",
        },
        "confidence_scores": {
            "patient.name": 0.95,
            "patient.date_of_birth": 0.90,
            "patient.mrn": 0.92,
            "medical_info.diagnosis": 0.88,
        }
    }


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_temp_files(tmp_path):
    """Cleanup temporary files after each test."""
    yield
    # Cleanup is automatic with tmp_path


# Performance tracking
@pytest.fixture(autouse=True)
def track_test_performance(request):
    """Track test execution time."""
    start_time = datetime.now()

    yield

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Mark slow tests
    if duration > 5:
        print(f"\n⚠️  Slow test: {request.node.name} took {duration:.2f}s")
