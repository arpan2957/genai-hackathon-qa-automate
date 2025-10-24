from typing import Dict, Any
from .base import ALMIntegration
from polarion_rest_api_client import PolarionClient

from config import POLARION_URL, POLARION_USERNAME, POLARION_PASSWORD, POLARION_PROJECT_ID

class PolarionIntegration(ALMIntegration):
    """
    Polarion integration for creating work items.
    """

    def __init__(self):
        if not all([POLARION_URL, POLARION_USERNAME, POLARION_PASSWORD, POLARION_PROJECT_ID]):
            raise ValueError("Polarion credentials not found. Polarion integration will be disabled.")
        
        self.client = PolarionClient(POLARION_URL, POLARION_USERNAME, POLARION_PASSWORD)

    def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a work item in Polarion.

        Args:
            issue_data: A dictionary containing the issue data.

        Returns:
            A dictionary containing the created work item's information.
        """
        try:
            steps_str = ""
            if isinstance(issue_data['test_case'].steps, list):
                steps_str = "<br>".join([f"Step {s['step']}: {s['action']}" for s in issue_data['test_case'].steps])
            else:
                manual_steps = str(issue_data['test_case'].steps).split('\n')
                steps_str = "<br>".join([f"- {line.strip()}" for line in manual_steps if line.strip()])

            work_item = self.client.create_work_item(
                project_id=POLARION_PROJECT_ID,
                type="task",
                title=f"{issue_data['test_case'].test_case_id}: {issue_data['test_case'].title}",
                description=f"<h2>Test Case Details</h2>"
                            f"<b>Test Case ID:</b> {issue_data['test_case'].test_case_id}<br>"
                            f"<b>Title:</b> {issue_data['test_case'].title}<br>"
                            f"<b>Priority:</b> {issue_data['test_case'].priority}<br>"
                            f"<b>Type:</b> {issue_data['test_case'].type}<br>"
                            f"<b>Compliance:</b> {issue_data['test_case'].compliance_tag}<br>"
                            f"<h2>Test Steps</h2>"
                            f"{steps_str}<br>"
                            f"<h2>Traceability ID</h2>"
                            f"{issue_data['test_case'].traceability_id}"
            )

            return {
                "issue_key": work_item.id,
                "url": work_item.url
            }

        except Exception as e:
            raise Exception(f"Failed to create Polarion work item: {str(e)}")
