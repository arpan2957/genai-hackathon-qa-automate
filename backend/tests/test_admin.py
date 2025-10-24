import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from main import app
from security import get_current_user

# Override user dependency
async def override_get_current_user_non_admin():
    return {"uid": "test_user_uid", "email": "test@example.com"}

async def override_get_current_user_admin():
    return {"uid": "admin_user_uid", "email": "admin@example.com"}

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")


def test_trigger_finetuning_unauthorized(client):
    """Test that a non-admin user cannot trigger the fine-tuning job."""
    app.dependency_overrides[get_current_user] = override_get_current_user_non_admin
    response = client.post("/api/admin/trigger-finetuning")
    assert response.status_code == 403
    assert "User is not authorized" in response.json()["detail"]

@patch("database.db")
@patch("routers.admin.storage_client")
@patch("routers.admin.aiplatform.PipelineJob")
def test_trigger_finetuning_success(mock_pipeline_job, mock_storage_client, mock_db, client):
    """Test that an admin user can successfully trigger the fine-tuning job."""
    # Arrange
    app.dependency_overrides[get_current_user] = override_get_current_user_admin

    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = {
        "rating": "bad",
        "requirement": "Test requirement",
        "original_test_case": { "test_case_id": "TC-001" },
        "corrected_test_case": { "test_case_id": "TC-001-corrected" }
    }
    mock_db.collection.return_value.stream.return_value = [mock_doc]

    mock_storage_client.bucket.return_value.blob.return_value.upload_from_string.return_value = None

    mock_job = MagicMock()
    mock_job.resource_name = "projects/my-project/locations/us-central1/pipelineJobs/tune-text-model-20240101000000"
    mock_job.state = "PIPELINE_STATE_PENDING"
    mock_pipeline_job.return_value = mock_job

    # Act
    response = client.post("/api/admin/trigger-finetuning")

    # Assert
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "PIPELINE_STATE_PENDING"
    assert "Fine-tuning job has been successfully triggered" in response_json["message"]


