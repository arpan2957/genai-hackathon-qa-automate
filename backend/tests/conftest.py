import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session", autouse=True)
def mock_google_auth():
    mock_credentials = MagicMock()
    mock_credentials.before_request = MagicMock()
    with patch('google.auth.default', return_value=(mock_credentials, "test-project")) as mock:
        yield mock

@pytest.fixture(scope="session", autouse=True)
def create_test_dataset_and_table():
    from database import create_bigquery_dataset_and_table
    create_bigquery_dataset_and_table()

@pytest.fixture(autouse=True)
def cleanup_dependency_overrides():
    from main import app
    yield
    app.dependency_overrides = {}
