import pytest
from unittest.mock import MagicMock, patch

from integrations import get_integration
from integrations.jira import JiraIntegration
from integrations.azure_devops import AzureDevOpsIntegration
from integrations.polarion import PolarionIntegration

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for all integration tests."""
    monkeypatch.setenv("JIRA_URL", "https://test.atlassian.net")
    monkeypatch.setenv("JIRA_USERNAME", "test@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "test_token")
    monkeypatch.setenv("AZURE_DEVOPS_URL", "https://dev.azure.com/test")
    monkeypatch.setenv("AZURE_DEVOPS_PROJECT", "TestProject")
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "test_pat")
    monkeypatch.setenv("POLARION_URL", "https://polarion.test.com")
    monkeypatch.setenv("POLARION_USERNAME", "test_user")
    monkeypatch.setenv("POLARION_PASSWORD", "test_pass")
    monkeypatch.setenv("POLARION_PROJECT_ID", "TestProject")


@pytest.fixture
def mock_jira():
    with patch('integrations.jira.Jira') as mock_jira_class:
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance
        yield mock_jira_instance

@pytest.fixture
def mock_azure_devops():
    with patch('integrations.azure_devops.Connection') as mock_ado_connection_class:
        mock_ado_connection_instance = MagicMock()
        mock_ado_connection_class.return_value = mock_ado_connection_instance
        mock_work_item_client = MagicMock()
        mock_ado_connection_instance.get_client.return_value = mock_work_item_client
        yield mock_work_item_client

@pytest.fixture
def mock_polarion():
    with patch('integrations.polarion.PolarionClient') as mock_polarion_class:
        mock_polarion_instance = MagicMock()
        mock_polarion_class.return_value = mock_polarion_instance
        yield mock_polarion_instance

def test_get_integration():
    with patch('integrations.jira.JIRA_URL', 'https://test.atlassian.net'), \
         patch('integrations.jira.JIRA_USERNAME', 'test@example.com'), \
         patch('integrations.jira.JIRA_API_TOKEN', 'test_token'), \
         patch('integrations.jira.Jira') as mock_jira_class, \
         patch('integrations.azure_devops.AZURE_DEVOPS_URL', 'https://dev.azure.com/test'), \
         patch('integrations.azure_devops.AZURE_DEVOPS_PROJECT', 'TestProject'), \
         patch('integrations.azure_devops.AZURE_DEVOPS_PAT', 'test_pat'), \
         patch('integrations.azure_devops.Connection') as mock_ado_connection, \
         patch('integrations.polarion.POLARION_URL', 'https://polarion.test.com'), \
         patch('integrations.polarion.POLARION_USERNAME', 'test_user'), \
         patch('integrations.polarion.POLARION_PASSWORD', 'test_pass'), \
         patch('integrations.polarion.POLARION_PROJECT_ID', 'TestProject'), \
         patch('integrations.polarion.PolarionClient') as mock_polarion_client:
        
        # Mock Jira
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance
        
        # Mock Azure DevOps Connection
        mock_connection_instance = MagicMock()
        mock_work_item_client = MagicMock()
        mock_connection_instance.get_client.return_value = mock_work_item_client
        mock_ado_connection.return_value = mock_connection_instance
        
        # Mock Polarion Client
        mock_polarion_instance = MagicMock()
        mock_polarion_client.return_value = mock_polarion_instance
        
        assert isinstance(get_integration('jira'), JiraIntegration)
        assert isinstance(get_integration('azure_devops'), AzureDevOpsIntegration)
        assert isinstance(get_integration('polarion'), PolarionIntegration)
        with pytest.raises(ValueError):
            get_integration('unknown')

def test_jira_create_issue(mock_jira):
    jira_integration = JiraIntegration()
    mock_jira.issue_create.return_value = {'key': 'PROJ-123'}
    issue_data = {
        'test_case': MagicMock(test_case_id='TC-001', title='Test Title', priority='High', type='Positive', compliance_tag='HIPAA', traceability_id='REQ-001', steps=[{'step': 1, 'action': 'Do something'}]),
        'project_key': 'PROJ',
        'issue_type': 'Task'
    }
    result = jira_integration.create_issue(issue_data)
    assert result['issue_key'] == 'PROJ-123'

def test_azure_devops_create_issue(mock_azure_devops):
    with patch('integrations.azure_devops.AZURE_DEVOPS_URL', 'https://dev.azure.com/test'), \
         patch('integrations.azure_devops.AZURE_DEVOPS_PROJECT', 'TestProject'), \
         patch('integrations.azure_devops.AZURE_DEVOPS_PAT', 'test_pat'):
        ado_integration = AzureDevOpsIntegration()
        mock_azure_devops.create_work_item.return_value = MagicMock(id=456, url='http://ado.com/proj/wi/456')
        issue_data = {
            'test_case': MagicMock(test_case_id='TC-001', title='Test Title', priority='High', type='Positive', compliance_tag='HIPAA', traceability_id='REQ-001', steps=[{'step': 1, 'action': 'Do something'}]),
            'issue_type': 'Task'
        }
        result = ado_integration.create_issue(issue_data)
        assert result['issue_key'] == '456'

def test_polarion_create_issue(mock_polarion):
    with patch('integrations.polarion.POLARION_URL', 'https://polarion.test.com'), \
         patch('integrations.polarion.POLARION_USERNAME', 'test_user'), \
         patch('integrations.polarion.POLARION_PASSWORD', 'test_pass'), \
         patch('integrations.polarion.POLARION_PROJECT_ID', 'TestProject'):
        polarion_integration = PolarionIntegration()
        mock_polarion.create_work_item.return_value = MagicMock(id='PROJ-789', url='http://polarion.com/proj/wi/789')
        issue_data = {
            'test_case': MagicMock(test_case_id='TC-001', title='Test Title', priority='High', type='Positive', compliance_tag='HIPAA', traceability_id='REQ-001', steps=[{'step': 1, 'action': 'Do something'}])
        }
        result = polarion_integration.create_issue(issue_data)
        assert result['issue_key'] == 'PROJ-789'
