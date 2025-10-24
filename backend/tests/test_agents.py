
import pytest
from unittest.mock import MagicMock, patch
from agents.generation_agent import GenerationAgent

@pytest.fixture
def mock_generative_model():
    """Fixture to mock the genai.GenerativeModel."""
    with patch('google.generativeai.GenerativeModel') as mock_model_class:
        mock_model_instance = MagicMock()
        mock_model_class.return_value = mock_model_instance
        yield mock_model_instance

def test_segment_requirements(mock_generative_model):
    """Test that the segment_requirements method calls the AI model correctly."""
    # Arrange
    agent = GenerationAgent()
    mock_generative_model.generate_content.return_value.text = '["req1", "req2"]'
    document_text = "This is a test document."

    # Act
    result = agent.segment_requirements(document_text=document_text)

    # Assert
    mock_generative_model.generate_content.assert_called_once()
    assert 'Document Text to be Segmented' in mock_generative_model.generate_content.call_args[0][0]
    assert document_text in mock_generative_model.generate_content.call_args[0][0]
    assert result == '["req1", "req2"]'

def test_classify_requirements(mock_generative_model):
    """Test that the classify_requirements method calls the AI model correctly."""
    # Arrange
    agent = GenerationAgent()
    mock_generative_model.generate_content.return_value.text = '{"domain": "test"}'
    product_name = "Test Product"
    requirements = ["req1", "req2"]

    # Act
    result = agent.classify_requirements(product_name=product_name, requirements=requirements)

    # Assert
    mock_generative_model.generate_content.assert_called_once()
    assert 'Product Name' in mock_generative_model.generate_content.call_args[0][0]
    assert product_name in mock_generative_model.generate_content.call_args[0][0]
    assert 'Requirements' in mock_generative_model.generate_content.call_args[0][0]
    assert result == '{"domain": "test"}'

def test_generate_initial_test_cases(mock_generative_model):
    """Test that the generate_initial_test_cases method calls the AI model correctly."""
    # Arrange
    agent = GenerationAgent()
    mock_generative_model.generate_content.return_value.text = '[{"id": 1}]'
    requirement = "This is a test requirement."

    # Act
    result = agent.generate_initial_test_cases(requirement=requirement)

    # Assert
    mock_generative_model.generate_content.assert_called_once()
    assert 'Requirement to test' in mock_generative_model.generate_content.call_args[0][0]
    assert requirement in mock_generative_model.generate_content.call_args[0][0]
    assert result == '[{"id": 1}]'

def test_refine_test_cases(mock_generative_model):
    """Test that the refine_test_cases method calls the AI model correctly."""
    # Arrange
    agent = GenerationAgent()
    mock_generative_model.generate_content.return_value.text = '[{"id": 2}]'
    requirement = "Original requirement."
    test_cases = '[{"id": 1}]'
    refinement_prompt = "Make it better."

    # Act
    result = agent.refine_test_cases(requirement=requirement, test_cases=test_cases, refinement_prompt=refinement_prompt)

    # Assert
    mock_generative_model.generate_content.assert_called_once()
    assert 'Original Requirement' in mock_generative_model.generate_content.call_args[0][0]
    assert requirement in mock_generative_model.generate_content.call_args[0][0]
    assert 'Existing Test Cases' in mock_generative_model.generate_content.call_args[0][0]
    assert 'Refinement Prompt' in mock_generative_model.generate_content.call_args[0][0]
    assert refinement_prompt in mock_generative_model.generate_content.call_args[0][0]
    assert result == '[{"id": 2}]'
