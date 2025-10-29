import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import base64

# Mock firebase admin and firestore
modules = {
    'firebase_admin': MagicMock(),
    'firebase_admin.credentials': MagicMock(),
    'firebase_admin.firestore': MagicMock(),
    'google.cloud.firestore': MagicMock(),
}

# Since we are using a dependency now, we can patch the dependency getter
from main import app
from security import get_current_user
from utils import get_generation_agent

from fastapi import Request

# Override user dependency
async def override_get_current_user(request: Request):
    return {"uid": "test_user_uid"}

@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)

@pytest.fixture
def mock_agent():
    mock = MagicMock()
    app.dependency_overrides[get_generation_agent] = lambda: mock
    return mock

@pytest.fixture
def mock_embedding_model(mocker):
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1] * 768  # Mock embedding vector

    mock_model = MagicMock()
    mock_model.get_embeddings.return_value = [mock_embedding]

    mocker.patch('routers.generation.TextEmbeddingModel.from_pretrained', return_value=mock_model)
    return mock_model

def test_generate_single_requirement_success(client, mock_agent, mock_embedding_model):
    """Test successful generation for a single requirement."""
    # Arrange
    mock_agent.classify_requirements.return_value = '{"product_name": "General Product", "domains": {"General": ["A user must be able to log in."]}}'
    mock_agent.generate_initial_test_cases.return_value = '[{"test_case_id": "TC-001", "title": "Test Title", "type": "Positive", "priority": "High", "steps": "Steps", "compliance_tag": "HIPAA"}]'

    payload = {"requirement": "A user must be able to log in."}

    # Act
    response = client.post("/api/generate", json=payload)

    # Assert
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["product_name"] == "General Product"
    assert len(response_json["domains"]) == 1
    assert response_json["domains"][0]["domain"] == "General"
    assert len(response_json["domains"][0]["test_cases"]) == 1
    assert response_json["domains"][0]["test_cases"][0]["test_case_id"] == "TC-001"
    # Check that generate_initial_test_cases was called with context
    mock_agent.generate_initial_test_cases.assert_called_once()
    call_args = mock_agent.generate_initial_test_cases.call_args[1]
    assert "requirement" in call_args
    assert "A user must be able to log in." in call_args["requirement"]
    assert "Context:" in call_args["requirement"]

def test_generate_document_upload_success(client, mock_agent):
    """Test successful generation from an uploaded document."""
    # Arrange
    mock_agent.segment_requirements.return_value = '["Req 1 from doc", "Req 2 from doc"]'
    mock_agent.classify_requirements.return_value = '{"product_name": "Doc Product", "domains": {"Authentication": ["Req 1 from doc"], "UI/UX": ["Req 2 from doc"]}}'
    mock_agent.generate_initial_test_cases.side_effect = [
        '[{"test_case_id": "TC-001", "title": "Auth Test", "type": "Positive", "priority": "High", "steps": "Steps", "compliance_tag": "HIPAA"}]',
        '[{"test_case_id": "TC-002", "title": "UI Test", "type": "Negative", "priority": "Medium", "steps": "Steps", "compliance_tag": "WCAG"}]'
    ]

    payload = {
        "document_text": "This is the content of the document.",
        "product_name": "Doc Product"
    }

    # Act
    response = client.post("/api/generate", json=payload)

    # Assert
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["product_name"] == "Doc Product"
    assert len(response_json["domains"]) == 2

def test_generate_ai_api_error(client, mock_agent, mock_embedding_model):
    """Test that a 500 error is raised on AI API failure."""
    # Arrange
    mock_agent.classify_requirements.return_value = '{"product_name": "General Product", "domains": {"General": ["test requirement"]}}'
    mock_agent.generate_initial_test_cases.side_effect = Exception("AI API is down")
    
    payload = {"requirement": "test requirement"}

    # Act
    response = client.post("/api/generate", json=payload)

    # Assert
    assert response.status_code == 500
    assert "AI API is down" in response.json()["detail"]

def test_generate_invalid_json_from_ai(client, mock_agent, mock_embedding_model):
    """Test that a 500 error is raised when the AI returns invalid JSON."""
    # Arrange
    mock_agent.classify_requirements.return_value = '{"product_name": "General Product", "domains": {"General": ["test requirement"]}}'
    mock_agent.generate_initial_test_cases.return_value = 'this is not json'
    
    payload = {"requirement": "test requirement"}

    # Act
    response = client.post("/api/generate", json=payload)

    # Assert
    assert response.status_code == 500
    assert "Expecting value: line 1 column 1 (char 0)" in response.json()["detail"]

def test_generate_invalid_request(client):
    """Test that a 400 error is raised for an invalid request payload."""
    # Act
    response = client.post("/api/generate", json={})

    # Assert
    assert response.status_code == 400
    assert "Either 'document_text' or 'requirement' must be provided." in response.json()["detail"]

@patch("routers.generation.genai.GenerativeModel")
@patch("routers.generation.Image.open")
@patch("routers.generation.base64.b64decode", side_effect=base64.b64decode)
def test_generate_multimodal_success(mock_b64decode, mock_image_open, mock_genai_model, client):
    """Test successful generation from an image upload."""
    # Arrange
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.return_value.text = '[{"test_case_id": "TC-IMG-001", "title": "Image Test", "type": "Positive", "priority": "High", "steps": "Steps", "compliance_tag": "UI"}]'
    mock_genai_model.return_value = mock_model_instance

    payload = {
        "requirement": "Generate test cases for this UI mockup.",
        "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    }

    # Act
    response = client.post("/api/generate", json=payload)

    # Assert
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json["domains"]) == 1
    assert response_json["domains"][0]["domain"] == "General"
    assert len(response_json["domains"][0]["test_cases"]) == 1
    assert response_json["domains"][0]["test_cases"][0]["test_case_id"] == "TC-IMG-001"
