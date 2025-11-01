"""
Tests for security fixes implemented in admin functionality.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import json

from main import app
from security import is_admin
from validation import (
    validate_user_id, validate_email, validate_event_type, 
    validate_filter_params, ValidationError, sanitize_string
)

# Override the admin dependency for all tests in this file
@pytest.fixture(autouse=True)
def override_admin_dependency():
    def mock_admin_user():
        return {"uid": "test_admin_uid", "email": "admin@test.com", "admin": True}
    
    app.dependency_overrides[is_admin] = mock_admin_user
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    return TestClient(app)

class TestInputValidation:
    """Test input validation functions."""
    
    def test_validate_user_id_valid(self):
        """Test valid user ID validation."""
        valid_uid = "abc123def456ghi789"
        result = validate_user_id(valid_uid)
        assert result == valid_uid
    
    def test_validate_user_id_invalid_length(self):
        """Test user ID validation with invalid length."""
        with pytest.raises(ValidationError, match="Invalid user ID length"):
            validate_user_id("short")
        
        with pytest.raises(ValidationError, match="Invalid user ID length"):
            validate_user_id("a" * 200)  # Too long
    
    def test_validate_user_id_invalid_format(self):
        """Test user ID validation with invalid characters."""
        with pytest.raises(ValidationError, match="Invalid user ID format"):
            validate_user_id("user@domain.com")
        
        with pytest.raises(ValidationError, match="Invalid user ID format"):
            validate_user_id("user-with-special-chars!")
    
    def test_validate_email_valid(self):
        """Test valid email validation."""
        valid_email = "test@example.com"
        result = validate_email(valid_email)
        assert result == valid_email.lower()
    
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        with pytest.raises(ValidationError, match="Invalid email format"):
            validate_email("invalid-email")
        
        with pytest.raises(ValidationError, match="Invalid email format"):
            validate_email("@domain.com")
    
    def test_validate_event_type_valid(self):
        """Test valid event type validation."""
        valid_event = "user_login"
        result = validate_event_type(valid_event)
        assert result == valid_event
    
    def test_validate_event_type_invalid(self):
        """Test invalid event type validation."""
        with pytest.raises(ValidationError, match="Event type must be alphanumeric"):
            validate_event_type("user login")  # Space not allowed
        
        with pytest.raises(ValidationError, match="Event type must be alphanumeric"):
            validate_event_type("user@login")  # Special chars not allowed
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        dirty_string = "<script>alert('xss')</script>Hello World"
        clean_string = sanitize_string(dirty_string)
        assert "<script>" not in clean_string
        assert "Hello World" in clean_string
    
    def test_sanitize_string_length_limit(self):
        """Test string length validation."""
        long_string = "a" * 2000
        with pytest.raises(ValidationError, match="String too long"):
            sanitize_string(long_string, max_length=1000)
    
    def test_validate_filter_params(self):
        """Test filter parameter validation."""
        params = validate_filter_params(
            user_id="validuserid123",
            event_type="user_login",
            start_date="2023-01-01T00:00:00.000Z",
            end_date="2023-12-31T23:59:59.999Z"
        )
        
        assert params['user_id'] == "validuserid123"
        assert params['event_type'] == "user_login"
        assert params['start_date'] == "2023-01-01T00:00:00.000Z"
        assert params['end_date'] == "2023-12-31T23:59:59.999Z"
    
    def test_validate_filter_params_invalid_date(self):
        """Test filter parameter validation with invalid date."""
        with pytest.raises(ValidationError, match="Invalid start_date format"):
            validate_filter_params(start_date="invalid-date")

class TestAdminEndpointSecurity:
    """Test admin endpoint security improvements."""
    
    @patch("routers.admin.validate_admin_request")
    @patch("routers.admin.validate_user_id")
    @patch("routers.admin.auth.delete_user")
    @patch("routers.admin.db")
    @patch("routers.admin.bq_client")
    def test_delete_user_with_validation(self, mock_bq, mock_db, mock_auth_delete, 
                                       mock_validate_user_id, mock_validate_request, client):
        """Test user deletion with input validation."""
        mock_validate_user_id.return_value = "validuserid123"
        mock_validate_request.return_value = {"ip_address": "127.0.0.1", "user_agent": "test"}
        
        response = client.delete("/api/admin/users/validuserid123")
        
        # Should call validation functions
        mock_validate_request.assert_called_once()
        mock_validate_user_id.assert_called_once_with("validuserid123")
        
        # Should proceed with deletion using validated ID
        mock_auth_delete.assert_called_once_with("validuserid123")
        assert response.status_code == 204
    
    @patch("routers.admin.validate_user_id")
    def test_delete_user_validation_error(self, mock_validate_user_id, client):
        """Test user deletion with validation error."""
        mock_validate_user_id.side_effect = ValidationError("Invalid user ID format")
        
        response = client.delete("/api/admin/users/invalid@user")
        
        assert response.status_code == 400
        assert "Validation error" in response.json()["detail"]
    
    @patch("routers.admin.validate_admin_request")
    @patch("routers.admin.validate_filter_params")
    @patch("routers.admin.bq_client")
    def test_audit_logs_with_validation(self, mock_bq, mock_validate_filters, 
                                      mock_validate_request, client):
        """Test audit logs endpoint with input validation."""
        mock_validate_request.return_value = {"ip_address": "127.0.0.1", "user_agent": "test"}
        mock_validate_filters.return_value = {"user_id": "validuserid123"}
        
        # Mock BigQuery response with proper AuditLogEntry format
        from datetime import datetime
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = [{
            "user_id": "validuserid123",
            "email": "test@example.com",
            "event_type": "login",
            "timestamp": datetime.now(),
            "ip_address": "127.0.0.1",
            "user_agent": "test-agent",
            "event_details": "{}"
        }]
        mock_bq.query.return_value = mock_query_job
        
        response = client.get("/api/admin/audit-logs?user_id=validuserid123")
        
        # Should call validation functions
        mock_validate_request.assert_called_once()
        mock_validate_filters.assert_called_once()
        
        assert response.status_code == 200
    
    def test_admin_verify_status_endpoint(self, client):
        """Test the new admin verification endpoint."""
        response = client.get("/api/admin/verify-status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["admin"] is True

class TestErrorHandling:
    """Test improved error handling without information leakage."""
    
    @patch("routers.admin.auth.delete_user")
    def test_delete_user_generic_error_message(self, mock_auth_delete, client):
        """Test that generic error messages are returned instead of stack traces."""
        # Simulate an unexpected error
        mock_auth_delete.side_effect = Exception("Database connection failed")
        
        response = client.delete("/api/admin/users/validuserid123")
        
        assert response.status_code == 500
        # Should return generic error message, not the actual exception
        assert response.json()["detail"] == "Failed to delete user"
        # Should NOT contain the actual error message
        assert "Database connection failed" not in response.json()["detail"]
    
    @patch("routers.admin.bq_client")
    def test_audit_logs_generic_error_message(self, mock_bq, client):
        """Test that audit logs endpoint returns generic error messages."""
        # Simulate BigQuery error
        mock_bq.query.side_effect = Exception("BigQuery quota exceeded")
        
        response = client.get("/api/admin/audit-logs")
        
        assert response.status_code == 500
        # Should return generic error message
        assert response.json()["detail"] == "Failed to retrieve audit logs"
        # Should NOT contain the actual error message
        assert "BigQuery quota exceeded" not in response.json()["detail"]

class TestFrontendSecurityIntegration:
    """Test frontend security improvements."""
    
    def test_admin_verification_endpoint_exists(self, client):
        """Test that the admin verification endpoint exists and works."""
        response = client.get("/api/admin/verify-status")
        assert response.status_code == 200
        
        data = response.json()
        assert "admin" in data
        assert data["admin"] is True
    
    def test_admin_verification_unauthorized(self):
        """Test admin verification with unauthorized user."""
        # Remove the admin override for this test
        app.dependency_overrides = {}
        
        client = TestClient(app)
        response = client.get("/api/admin/verify-status")
        
        # Should return 401 because no valid token
        assert response.status_code == 401
        
        # Restore override for other tests
        def mock_admin_user():
            return {"uid": "test_admin_uid", "email": "admin@test.com", "admin": True}
        app.dependency_overrides[is_admin] = mock_admin_user

@pytest.mark.parametrize("malicious_input,expected_error", [
    ("<script>alert('xss')</script>", "Invalid user ID format"),
    ("'; DROP TABLE users; --", "Invalid user ID format"),
    ("../../../etc/passwd", "Invalid user ID format"),
    ("user@domain.com", "Invalid user ID format"),
    ("a" * 200, "Invalid user ID length"),
])
def test_malicious_input_validation(malicious_input, expected_error):
    """Test that malicious inputs are properly validated and rejected."""
    with pytest.raises(ValidationError, match=expected_error):
        validate_user_id(malicious_input)

def test_request_size_validation():
    """Test that large requests are rejected."""
    from validation import validate_request_size
    from fastapi import Request, HTTPException
    
    # Mock a request with large content
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"content-length": "20971520"}  # 20MB
    
    with pytest.raises(HTTPException) as exc_info:
        validate_request_size(mock_request, max_size=10*1024*1024)  # 10MB limit
    
    assert exc_info.value.status_code == 413
    assert "Request too large" in str(exc_info.value.detail)
