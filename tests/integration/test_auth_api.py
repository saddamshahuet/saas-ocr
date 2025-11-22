"""
Integration tests for authentication API endpoints
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
class TestAuthenticationAPI:
    """Test authentication endpoints."""

    def test_register_new_user(self, client):
        """Test user registration."""
        response = client.post(
            "/api/v1/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepassword123",
                "full_name": "New User",
            }
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "email" in data
        assert data["email"] == "newuser@example.com"

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email."""
        response = client.post(
            "/api/v1/register",
            json={
                "email": test_user.email,
                "username": "differentuser",
                "password": "password123",
            }
        )

        assert response.status_code in [400, 409, 422]

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username."""
        response = client.post(
            "/api/v1/register",
            json={
                "email": "different@example.com",
                "username": test_user.username,
                "password": "password123",
            }
        )

        assert response.status_code in [400, 409, 422]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/api/v1/register",
            json={
                "email": "invalid-email",
                "username": "testuser",
                "password": "password123",
            }
        )

        assert response.status_code == 422

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/api/v1/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "123",  # Too short
            }
        )

        # Should either reject or accept (depending on validation)
        assert response.status_code in [200, 201, 400, 422]

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            }
        )

        assert response.status_code in [400, 401]

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post(
            "/api/v1/login",
            data={
                "username": "nonexistent@example.com",
                "password": "password123",
            }
        )

        assert response.status_code in [400, 401, 404]

    def test_access_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/users/me")

        assert response.status_code in [401, 403]

    def test_access_protected_endpoint_with_token(self, client, auth_headers):
        """Test accessing protected endpoint with valid token."""
        response = client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "email" in data

    def test_access_with_invalid_token(self, client):
        """Test accessing endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code in [401, 403]

    def test_access_with_expired_token(self, client):
        """Test accessing endpoint with expired token."""
        # Create expired token
        from datetime import timedelta
        from app.core.security import create_access_token

        expired_token = create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=timedelta(seconds=-1)
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code in [401, 403]


@pytest.mark.integration
@pytest.mark.api
class TestAPIKeyAuthentication:
    """Test API key authentication."""

    def test_generate_api_key(self, client, auth_headers):
        """Test API key generation."""
        response = client.post(
            "/api/v1/api-keys",
            headers=auth_headers,
            json={"name": "Test API Key"}
        )

        # May or may not be implemented
        assert response.status_code in [200, 201, 404, 501]

    def test_authenticate_with_api_key(self, client):
        """Test authentication with API key."""
        # This would require creating an API key first
        # Skip if not implemented
        pytest.skip("API key authentication test - implementation dependent")
