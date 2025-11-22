# SaaS OCR - Testing Documentation

## Overview

This document describes the comprehensive testing infrastructure for the SaaS OCR project. The testing suite includes unit tests, integration tests, and end-to-end (E2E) tests with detailed reporting capabilities.

## Table of Contents

1. [Test Structure](#test-structure)
2. [Running Tests](#running-tests)
3. [Test Types](#test-types)
4. [Test Reports](#test-reports)
5. [Writing Tests](#writing-tests)
6. [CI/CD Integration](#cicd-integration)
7. [Troubleshooting](#troubleshooting)

---

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Global fixtures and configuration
├── test_testing_infrastructure.py  # Meta-tests for testing framework
├── unit/                       # Unit tests
│   ├── core/                   # Core functionality tests
│   │   ├── test_config.py
│   │   └── test_security.py
│   ├── models/                 # Database model tests
│   │   ├── test_user_model.py
│   │   └── test_job_model.py
│   └── services/               # Service layer tests
│       ├── test_ocr_service.py
│       ├── test_llm_service.py
│       └── test_storage_service.py
├── integration/                # Integration tests
│   ├── test_auth_api.py        # Authentication endpoints
│   └── test_job_api.py         # Job processing endpoints
├── e2e/                        # End-to-end tests
│   └── test_complete_workflow.py  # Complete system workflows
└── utils/                      # Testing utilities
    └── test_runner.py          # Test execution and reporting

test-reports/                   # Generated test reports
├── unit-tests-report.html
├── integration-tests-report.html
├── e2e-tests-report.html
├── coverage-html/
└── test-summary-*.txt
```

---

## Running Tests

### Prerequisites

1. **Install test dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

2. **Set up test database:**
   ```bash
   # Create test database
   createdb saas_ocr_test

   # Or configure in .env
   TEST_DATABASE_URL=postgresql://user:password@localhost:5432/saas_ocr_test
   ```

3. **Ensure required services are running:**
   - PostgreSQL (for database tests)
   - Redis (for Celery tests, optional)

### Quick Start

**Run all tests:**
```bash
./run_tests.sh all
```

**Run specific test suites:**
```bash
# Unit tests only
./run_tests.sh unit

# Integration tests only
./run_tests.sh integration

# E2E tests only
./run_tests.sh e2e

# Quick smoke tests
./run_tests.sh quick

# With coverage analysis
./run_tests.sh coverage
```

### Using pytest directly

**Run all tests:**
```bash
pytest tests/ -v
```

**Run specific test file:**
```bash
pytest tests/unit/services/test_ocr_service.py -v
```

**Run tests by marker:**
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only E2E tests
pytest -m e2e

# Run API tests
pytest -m api

# Run database tests
pytest -m database
```

**Run with coverage:**
```bash
pytest tests/ --cov=backend/app --cov-report=html
```

**Run in parallel:**
```bash
pytest tests/ -n auto
```

---

## Test Types

### 1. Unit Tests

**Location:** `tests/unit/`

**Purpose:** Test individual components in isolation

**Characteristics:**
- Fast execution (< 1 second per test)
- No external dependencies
- Mock all external services
- High code coverage target (>80%)

**Examples:**
```python
@pytest.mark.unit
def test_password_hashing():
    password = "secret"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
```

**Running:**
```bash
pytest tests/unit -m unit
```

### 2. Integration Tests

**Location:** `tests/integration/`

**Purpose:** Test interaction between components

**Characteristics:**
- Test API endpoints
- Use test database
- May use real services (with test data)
- Medium execution time (1-5 seconds per test)

**Examples:**
```python
@pytest.mark.integration
@pytest.mark.api
def test_user_registration(client):
    response = client.post("/api/v1/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
```

**Running:**
```bash
pytest tests/integration -m integration
```

### 3. End-to-End (E2E) Tests

**Location:** `tests/e2e/`

**Purpose:** Test complete user workflows

**Characteristics:**
- Test entire system flow
- Simulate real user behavior
- Slower execution (5-30 seconds per test)
- Test data persistence and state

**Examples:**
```python
@pytest.mark.e2e
@pytest.mark.slow
def test_complete_document_processing(client, sample_image_path):
    # Register user
    # Login
    # Upload document
    # Wait for processing
    # Retrieve results
    # Verify data
```

**Running:**
```bash
pytest tests/e2e -m e2e
```

---

## Test Reports

### HTML Reports

After running tests, HTML reports are generated in `test-reports/`:

- `unit-tests-report.html` - Unit test results
- `integration-tests-report.html` - Integration test results
- `e2e-tests-report.html` - E2E test results
- `all-tests-report.html` - Combined results

**Viewing reports:**
```bash
# Open in browser
open test-reports/unit-tests-report.html

# Or use Python's HTTP server
cd test-reports
python -m http.server 8080
# Visit http://localhost:8080
```

### Coverage Reports

**HTML Coverage Report:**
```bash
open test-reports/coverage-html/index.html
```

**Console Coverage Report:**
```bash
pytest tests/ --cov=backend/app --cov-report=term-missing
```

**Coverage Metrics:**
- **Statement Coverage:** Lines executed
- **Branch Coverage:** Decision paths taken
- **Function Coverage:** Functions called
- **Target:** >80% overall coverage

### JSON Reports

JSON reports for programmatic analysis:
```bash
cat test-reports/unit-tests-report.json | jq
```

### Summary Reports

Text summary of all test runs:
```bash
cat test-reports/test-summary-*.txt
```

---

## Writing Tests

### Test Structure

```python
"""
Module docstring describing what is being tested
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.services.my_service import MyService


@pytest.mark.unit  # or @pytest.mark.integration or @pytest.mark.e2e
@pytest.mark.specific_feature  # e.g., @pytest.mark.ocr
class TestMyService:
    """Test suite for MyService."""

    @pytest.fixture
    def my_service(self):
        """Create service instance for testing."""
        return MyService()

    def test_feature_works(self, my_service):
        """Test that feature works correctly."""
        result = my_service.do_something()
        assert result is not None

    def test_feature_handles_errors(self, my_service):
        """Test error handling."""
        with pytest.raises(ValueError):
            my_service.do_invalid_thing()
```

### Using Fixtures

**Common fixtures available:**

```python
def test_with_database(db_session):
    """Use database session."""
    pass

def test_with_user(test_user):
    """Use test user."""
    pass

def test_with_auth(client, auth_headers):
    """Test authenticated endpoint."""
    response = client.get("/api/v1/protected", headers=auth_headers)
```

### Mocking Services

```python
from unittest.mock import Mock, patch

def test_with_mock_ocr(mock_ocr_service):
    """Use mocked OCR service."""
    result = mock_ocr_service.extract_text("image.png")
    assert "text" in result

@patch('app.services.external_api.requests.post')
def test_external_api(mock_post):
    """Mock external API call."""
    mock_post.return_value.status_code = 200
    # Test your code
```

### Best Practices

1. **Test Naming:**
   - Use descriptive names: `test_user_cannot_access_other_user_data`
   - Start with `test_`
   - Use underscores for readability

2. **Test Organization:**
   - Group related tests in classes
   - One concept per test
   - Arrange-Act-Assert pattern

3. **Assertions:**
   - Use specific assertions: `assert user.email == "test@example.com"`
   - Include failure messages: `assert result, "Result should not be None"`

4. **Markers:**
   - Use appropriate markers: `@pytest.mark.unit`, `@pytest.mark.slow`
   - Mark slow tests: `@pytest.mark.slow`
   - Mark tests that require specific services

5. **Fixtures:**
   - Use fixtures for setup/teardown
   - Keep fixtures focused and reusable
   - Use appropriate scope (function, class, module, session)

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run tests
        run: |
          ./run_tests.sh all

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./test-reports/coverage.xml

      - name: Archive test reports
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: test-reports/
```

---

## Troubleshooting

### Common Issues

**1. Import errors:**
```bash
# Ensure backend is in path
export PYTHONPATH="${PYTHONPATH}:${PWD}/backend"
```

**2. Database connection errors:**
```bash
# Check database exists
psql -l | grep saas_ocr_test

# Create if missing
createdb saas_ocr_test
```

**3. Fixture not found:**
- Check `conftest.py` is present in test directory
- Verify fixture name matches

**4. Tests hanging:**
- Check for infinite loops
- Use `--timeout=60` flag
- Check database connections are closed

**5. Permission errors:**
```bash
# Make test script executable
chmod +x run_tests.sh
```

### Debug Mode

**Run with verbose output:**
```bash
pytest tests/ -vv -s
```

**Run with debug logging:**
```bash
pytest tests/ --log-cli-level=DEBUG
```

**Run single test:**
```bash
pytest tests/unit/test_file.py::TestClass::test_method -vv
```

**Stop on first failure:**
```bash
pytest tests/ -x
```

**Drop into debugger on failure:**
```bash
pytest tests/ --pdb
```

---

## Test Metrics

### Current Coverage

Run to see current coverage:
```bash
./run_tests.sh coverage
```

### Performance Benchmarks

- Unit tests: < 1 second each
- Integration tests: 1-5 seconds each
- E2E tests: 5-30 seconds each
- Full test suite: < 10 minutes

### Quality Gates

**Before merging:**
- ✅ All tests pass
- ✅ Code coverage > 80%
- ✅ No new linting errors
- ✅ No security vulnerabilities

---

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

## Support

For testing issues:
1. Check this documentation
2. Review test output in `test-reports/`
3. Check GitHub issues
4. Contact development team

---

**Last Updated:** 2024
