from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any

from models import CreateIssueRequest, IntegrationIssueResponse
from security import get_current_user
from integrations import get_integration
from audit import log_audit_event

router = APIRouter()

@router.post("/api/integrations/{integration_name}/create-issue", response_model=IntegrationIssueResponse, tags=["Integrations"], summary="Create an Issue in an ALM Tool",
    description="Creates a new issue in a specified ALM tool from a single test case.")
async def create_issue(req: Request, integration_name: str, request_body: CreateIssueRequest, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        integration = get_integration(integration_name)
        issue_data = request_body.dict()
        created_issue = integration.create_issue(issue_data)
        
        log_audit_event(req, user, "create_alm_issue", details={
            "integration_name": integration_name,
            "issue_key": created_issue.get("issue_key"),
            "test_case_id": request_body.test_case.test_case_id
        })
        
        return created_issue
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
