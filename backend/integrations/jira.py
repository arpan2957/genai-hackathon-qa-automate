from typing import Dict, Any
from atlassian import Jira
from config import JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN
from .base import ALMIntegration

class JiraIntegration(ALMIntegration):
    """
    Jira integration for creating issues.
    """

    def __init__(self):
        if not all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]):
            raise ValueError("Jira credentials not found. Jira integration will be disabled.")
        self.jira = Jira(url=JIRA_URL, username=JIRA_USERNAME, password=JIRA_API_TOKEN, cloud=True)

    def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an issue in Jira.

        Args:
            issue_data: A dictionary containing the issue data.

        Returns:
            A dictionary containing the created issue's information.
        """
        try:
            # Format the test case steps into a string for the Jira description
            steps_str = ""
            if isinstance(issue_data['test_case'].steps, list):
                steps_str = "\n".join([f"Step {s['step']}: {s['action']}" for s in issue_data['test_case'].steps])
            else:
                # Improved formatting for manual test case steps
                manual_steps = str(issue_data['test_case'].steps).split('\n')
                steps_str = "\n".join([f"- {line.strip()}" for line in manual_steps if line.strip()])

            jira_issue_data = {
                "project": {"key": issue_data['project_key']},
                "summary": f"{issue_data['test_case'].test_case_id}: {issue_data['test_case'].title}",
                "description": f"h2. Test Case Details\n"
                f"*Test Case ID:* {issue_data['test_case'].test_case_id}\n"
                f"*Title:* {issue_data['test_case'].title}\n"
                f"*Priority:* {issue_data['test_case'].priority}\n"
                f"*Type:* {issue_data['test_case'].type}\n"
                f"*Compliance:* {issue_data['test_case'].compliance_tag}\n"
                f"h2. Test Steps\n"
                f"{steps_str}\n"
                f"h2. Traceability ID\n"
                f"{issue_data['test_case'].traceability_id}",
                "issuetype": {"name": issue_data['issue_type']},
            }
            
            new_issue = self.jira.issue_create(fields=jira_issue_data)
            
            return {"issue_key": new_issue['key'], "url": f"{JIRA_URL}/browse/{new_issue['key']}"}

        except Exception as e:
            # Catch potential errors from the Jira API (e.g., project not found, invalid credentials)
            raise Exception(f"Failed to create Jira issue: {str(e)}")
