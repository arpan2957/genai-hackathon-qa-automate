import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from main import app
from security import get_current_user
from database import get_db


@pytest.fixture
def mock_db():
    return MagicMock()


async def override_get_current_user():
    return {"uid": "test_user_uid"}


@pytest.fixture
def client(mock_db):
    """Create a TestClient instance."""

    def override_get_db():
        return mock_db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_submit_feedback_success(client, mock_db):
    """Test successful submission of feedback."""
    # Arrange
    payload = {
        "requirement": "A user must be able to log in.",
        "original_test_case": {
            "test_case_id": "TC-001",
            "title": "Test Title",
            "type": "Positive",
            "priority": "High",
            "steps": "Steps",
            "compliance_tag": "HIPAA",
        },
        "rating": "good",
    }

    # Act
    response = client.post("/api/feedback", json=payload)

    # Assert
    assert response.status_code == 201
    assert response.json() == {"message": "Feedback submitted successfully."}
    mock_db.collection.assert_called_once_with("finetuning_data")
    mock_db.collection.return_value.add.assert_called_once()
