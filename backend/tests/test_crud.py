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


@pytest.fixture
def sample_payload():
    """Provide a sample GenerateResponse payload."""
    return {
        "requirement": "The user must be able to log in with a valid username and password.",
        "product_name": "Test Product",
        "domains": [
            {
                "domain": "Authentication",
                "test_cases": [
                    {
                        "test_case_id": "TC-001",
                        "title": "Successful Login",
                        "type": "Positive",
                        "priority": "High",
                        "steps": "1. Go to login page\n2. Enter valid credentials\n3. Click login",
                        "compliance_tag": "ISO-27001",
                        "traceability_id": None,
                    }
                ],
            }
        ],
    }


def test_create_finalized_cases(client, mock_db, sample_payload):
    """Test POST /api/finalized-cases - successful creation."""
    # Arrange
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "new_doc_id_123"
    mock_db.collection.return_value.document.return_value.collection.return_value.add.return_value = (
        None,
        mock_doc_ref,
    )

    # Act
    response = client.post("/api/finalized-cases", json=sample_payload)

    # Assert
    assert response.status_code == 201
    assert response.json() == {"id": "new_doc_id_123"}
    mock_db.collection.assert_called_with("users")
    mock_db.collection.return_value.document.assert_called_with("test_user_uid")
    mock_db.collection.return_value.document.return_value.collection.assert_called_with(
        "finalized_cases"
    )
    mock_db.collection.return_value.document.return_value.collection.return_value.add.assert_called_once_with(
        sample_payload
    )


def test_get_finalized_cases(client, mock_db, sample_payload):
    """Test GET /api/finalized-cases - successful retrieval."""
    # Arrange
    mock_doc = MagicMock()
    mock_doc.id = "doc_id_abc"
    mock_doc.to_dict.return_value = sample_payload
    mock_db.collection.return_value.document.return_value.collection.return_value.stream.return_value = [
        mock_doc
    ]

    # Act
    response = client.get("/api/finalized-cases")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["id"] == "doc_id_abc"
    assert response_data[0]["product_name"] == "Test Product"
    mock_db.collection.assert_called_with("users")
    mock_db.collection.return_value.document.assert_called_with("test_user_uid")
    mock_db.collection.return_value.document.return_value.collection.assert_called_with(
        "finalized_cases"
    )


def test_update_finalized_cases(client, mock_db, sample_payload):
    """Test PUT /api/finalized-cases/{doc_id} - successful update."""
    # Arrange
    doc_id = "doc_to_update_456"
    mock_users_collection = mock_db.collection.return_value
    mock_user_doc = mock_users_collection.document.return_value
    mock_cases_collection = mock_user_doc.collection.return_value
    mock_case_doc = mock_cases_collection.document.return_value

    # Act
    response = client.put(f"/api/finalized-cases/{doc_id}", json=sample_payload)

    # Assert
    assert response.status_code == 204
    mock_db.collection.assert_called_once_with("users")
    mock_users_collection.document.assert_called_once_with("test_user_uid")
    mock_user_doc.collection.assert_called_once_with("finalized_cases")
    mock_cases_collection.document.assert_called_once_with(doc_id)
    mock_case_doc.set.assert_called_once_with(sample_payload)


def test_delete_finalized_cases(client, mock_db):
    """Test DELETE /api/finalized-cases/{doc_id} - successful deletion."""
    # Arrange
    doc_id = "doc_to_delete_789"
    mock_users_collection = mock_db.collection.return_value
    mock_user_doc = mock_users_collection.document.return_value
    mock_cases_collection = mock_user_doc.collection.return_value
    mock_case_doc = mock_cases_collection.document.return_value

    # Act
    response = client.delete(f"/api/finalized-cases/{doc_id}")

    # Assert
    assert response.status_code == 204
    mock_db.collection.assert_called_once_with("users")
    mock_users_collection.document.assert_called_once_with("test_user_uid")
    mock_user_doc.collection.assert_called_once_with("finalized_cases")
    mock_cases_collection.document.assert_called_once_with(doc_id)
    mock_case_doc.delete.assert_called_once()


def test_get_finalized_cases_db_error(client, mock_db):
    """Test GET /api/finalized-cases when a database error occurs."""
    # Arrange
    error_message = "Firestore is down"
    mock_db.collection.return_value.document.return_value.collection.return_value.stream.side_effect = (
        Exception(error_message)
    )

    # Act
    response = client.get("/api/finalized-cases")

    # Assert
    assert response.status_code == 500
    assert error_message in response.json()["detail"]