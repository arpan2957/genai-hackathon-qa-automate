from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union, Optional, Literal
from datetime import datetime

class TestCase(BaseModel):
    test_case_id: str
    title: str
    type: str
    priority: str
    steps: Union[str, List[Dict[str, Any]]]
    compliance_tag: str
    traceability_id: Optional[str] = None

class RequirementRequest(BaseModel):
    requirement: str = None
    refinement_prompt: str = None
    test_cases: List[TestCase] = None
    document_text: str = None
    product_name: str = None
    requirement_id: str = None
    image_data: str = None

class ManualTestCaseDetailsRequest(BaseModel):
    title: str
    steps: str
    product_name: str = None
    requirement_id: str = None

class ManualTestCaseDetailsResponse(BaseModel):
    test_case_id: str
    compliance_tag: str
    traceability_id: str
    domain: str

class FeedbackRequest(BaseModel):
    requirement: str
    original_test_case: TestCase
    corrected_test_case: Optional[TestCase] = None
    rating: str


class CreateIssueRequest(BaseModel):
    test_case: TestCase
    project_key: Optional[str] = None
    issue_type: str = "Task"
    extra_fields: Optional[Dict[str, Any]] = None

class IntegrationIssueResponse(BaseModel):
    issue_key: str
    url: str


class DomainGroup(BaseModel):
    domain: str
    test_cases: List[TestCase]

class GenerateResponse(BaseModel):
    product_name: str = "General Product"
    domains: List[DomainGroup]

class CreateFinalizedCasesRequest(GenerateResponse):
    requirement: str

class FinalizedCasesDoc(CreateFinalizedCasesRequest):
    id: str
    requirement: Optional[str] = None

class KnowledgeBaseDocument(BaseModel):
    id: str
    filename: str
    upload_date: datetime
    image_url: Optional[str] = None
    image_embedding: Optional[List[float]] = None
    document_type: Literal['text', 'image', 'multimodal'] = 'text'
    detected_frameworks: Optional[List[Dict[str, Any]]] = None

class PostResponse(BaseModel):
    id: str

class UploadResponse(BaseModel):
    filename: str
    text: str

class FineTuningResponse(BaseModel):
    job_id: str
    status: str
    message: str

class WebhookRegistration(BaseModel):
    url: str
    events: List[str] = ["test_case_generated"]

class UserProfile(BaseModel):
    uid: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    created_at: Optional[int] = None

class AuditLogEntry(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    event_type: Optional[str] = None
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    event_details: Optional[str] = None

class AuditSummaryEntry(BaseModel):
    event_type: str
    count: int
