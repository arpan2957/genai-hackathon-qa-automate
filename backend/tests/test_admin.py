import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, call

from main import app
from security import is_admin

# Override the admin dependency for all tests in this file
@pytest.fixture(autouse=True)
def override_admin_dependency():
    app.dependency_overrides[is_admin] = lambda: True
    yield
    app.dependency_overrides = {}

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")

# Mock document data to be reused across tests
@pytest.fixture
def mock_feedback_docs():
    docs = []
    for i in range(150):
        mock_doc = MagicMock()
        mock_doc.reference = f"doc_ref_{i}"
        mock_doc.to_dict.return_value = {
            "rating": "bad",
            "requirement": f"Test requirement {i}",
            "original_test_case": { "test_case_id": f"TC-{i}" },
            "corrected_test_case": { "test_case_id": f"TC-{i}-corrected" }
        }
        docs.append(mock_doc)
    return docs


@patch("routers.admin.aiplatform.PipelineJob.list")
def test_trigger_finetuning_when_pipeline_is_running(mock_pipeline_list, client):
    """Test that a 409 Conflict is returned if a pipeline is already running."""
    # Arrange
    mock_pipeline_list.return_value = [MagicMock()] # Return a list with one mock job

    # Act
    response = client.post("/api/admin/trigger-finetuning")

    # Assert
    assert response.status_code == 409
    assert "A fine-tuning pipeline is already in progress" in response.json()["detail"]


@patch("routers.admin.aiplatform.PipelineJob.list")
@patch("routers.admin.db")
def test_trigger_finetuning_insufficient_data(mock_db, mock_pipeline_list, client, mock_feedback_docs):
    """Test that a 428 Precondition Required is returned if there are not enough new documents."""
    # Arrange
    mock_pipeline_list.return_value = [] # No active pipelines
    # Return only 50 documents, which is below the threshold of 100
    mock_db.collection.return_value.where.return_value.stream.return_value = mock_feedback_docs[:50]

    # Act
    response = client.post("/api/admin/trigger-finetuning")

    # Assert
    assert response.status_code == 428
    assert "Only 50 new feedback examples found" in response.json()["detail"]


@patch("routers.admin.run_finetuning_pipeline")
@patch("routers.admin.aiplatform.PipelineJob.list")
@patch("routers.admin.db")
@patch("routers.admin.storage_client")
def test_trigger_finetuning_force_override(mock_storage_client, mock_db, mock_pipeline_list, mock_run_pipeline, client, mock_feedback_docs):
    """Test that using force=true bypasses the data threshold check."""
    # Arrange
    mock_pipeline_list.return_value = []
    mock_db.collection.return_value.where.return_value.stream.return_value = mock_feedback_docs[:50]
    mock_db.batch.return_value.commit.return_value = None

    mock_job = MagicMock()
    mock_job.resource_name = "test-job-resource"
    mock_job.state = "PIPELINE_STATE_PENDING"
    mock_run_pipeline.return_value = mock_job

    # Act
    response = client.post("/api/admin/trigger-finetuning?force=true")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "PIPELINE_STATE_PENDING"
    assert "triggered with 50 new examples" in response.json()["message"]


@patch("routers.admin.run_finetuning_pipeline")
@patch("routers.admin.aiplatform.PipelineJob.list")
@patch("routers.admin.db")
@patch("routers.admin.storage_client")
def test_trigger_finetuning_success_and_flags_data(mock_storage_client, mock_db, mock_pipeline_list, mock_run_pipeline, client, mock_feedback_docs):
    """Test a successful run and verify that feedback documents are flagged as processed."""
    # Arrange
    mock_pipeline_list.return_value = []
    mock_db.collection.return_value.where.return_value.stream.return_value = mock_feedback_docs
    
    mock_batch = MagicMock()
    mock_db.batch.return_value = mock_batch

    mock_job = MagicMock()
    mock_job.resource_name = "test-job-resource"
    mock_job.state = "PIPELINE_STATE_PENDING"
    mock_run_pipeline.return_value = mock_job

    # Act
    response = client.post("/api/admin/trigger-finetuning")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "PIPELINE_STATE_PENDING"
    assert "triggered with 150 new examples" in response.json()["message"]

    # Verify that the batch update was called to flag documents
    mock_db.batch.assert_called_once()
    # Check that update was called for each document reference
    expected_calls = [call.update(doc.reference, {'processed_for_tuning': True}) for doc in mock_feedback_docs]
    mock_batch.assert_has_calls(expected_calls, any_order=True)
    mock_batch.commit.assert_called_once()
