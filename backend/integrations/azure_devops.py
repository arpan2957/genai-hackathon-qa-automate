from typing import Dict, Any
from .base import ALMIntegration
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v6_0.work_item_tracking.models import JsonPatchOperation

from config import AZURE_DEVOPS_URL, AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_PAT

class AzureDevOpsIntegration(ALMIntegration):
    """
    Azure DevOps integration for creating work items.
    """

    def __init__(self):
        if not all([AZURE_DEVOPS_URL, AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_PAT]):
            raise ValueError("Azure DevOps credentials not found. Azure DevOps integration will be disabled.")
        
        credentials = BasicAuthentication('', AZURE_DEVOPS_PAT)
        self.connection = Connection(base_url=AZURE_DEVOPS_URL, creds=credentials)
        self.work_item_client = self.connection.get_client('azure.devops.v6_0.work_item_tracking.WorkItemTrackingClient')

    def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a work item in Azure DevOps.

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

            patch_document = [
                JsonPatchOperation(
                    op="add",
                    path="/fields/System.Title",
                    value=f"{issue_data['test_case'].test_case_id}: {issue_data['test_case'].title}"
                ),
                JsonPatchOperation(
                    op="add",
                    path="/fields/System.Description",
                    value=f"<h2>Test Case Details</h2>"
                            f"<b>Test Case ID:</b> {issue_data['test_case'].test_case_id}<br>"
                            f"<b>Title:</b> {issue_data['test_case'].title}<br>"
                            f"<b>Priority:</b> {issue_data['test_case'].priority}<br>"
                            f"<b>Type:</b> {issue_data['test_case'].type}<br>"
                            f"<b>Compliance:</b> {issue_data['test_case'].compliance_tag}<br>"
                            f"<h2>Test Steps</h2>"
                            f"{steps_str}<br>"
                            f"<h2>Traceability ID</h2>"
                            f"{issue_data['test_case'].traceability_id}"
                ),
            ]

            new_work_item = self.work_item_client.create_work_item(
                document=patch_document,
                project=AZURE_DEVOPS_PROJECT,
                type=issue_data['issue_type']
            )

            return {
                "issue_key": str(new_work_item.id),
                "url": new_work_item.url
            }

        except Exception as e:
            raise Exception(f"Failed to create Azure DevOps work item: {str(e)}")
