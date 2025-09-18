import os

import json
from typing import List, Dict, Any, Union, Optional
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Response, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime

from docx import Document
from pypdf import PdfReader
import io
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, auth, firestore

from atlassian import Jira

from agents.test_case_agent import TestCaseAgent

# Load environment variables from .env file
load_dotenv()

# --- AI Configuration ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("ERROR: GOOGLE_API_KEY not found in the backend/.env file")

GENAI_MODEL = os.getenv("GENAI_MODEL", "gemini-2.5-flash")
genai.configure(api_key=api_key)

# --- Jira Configuration ---
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

jira = None
if all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]):
    jira = Jira(url=JIRA_URL, username=JIRA_USERNAME, password=JIRA_API_TOKEN, cloud=True)
else:
    print("Warning: JIRA credentials not found. Jira integration will be disabled.")

# --- Firebase Admin SDK Initialization ---
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- FastAPI App Initialization ---
app = FastAPI(
    title="AI Test Case Generator API",
    description="API for generating, managing, and exporting test cases using AI.",
    version="1.2.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        return auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication credentials: {e}", headers={"WWW-Authenticate": "Bearer"})

# --- Pydantic Models ---

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

class JiraIssueRequest(BaseModel):
    test_case: TestCase
    project_key: str
    issue_type: str = "Task"

class DomainGroup(BaseModel):
    domain: str
    test_cases: List[TestCase]

class GenerateResponse(BaseModel):
    product_name: str = "General Product"
    domains: List[DomainGroup]

class FinalizedCasesDoc(GenerateResponse):
    id: str

class PostResponse(BaseModel):
    id: str

class UploadResponse(BaseModel):
    filename: str
    text: str

# ... other models

# --- Utility Functions ---
def _clean_json_response(response_text: str) -> str:
    if '```json' in response_text:
        response_text = response_text.split('```json', 1)[1].rsplit('```', 1)[0]
    return response_text.strip()

# --- Agent Dependency ---
def get_test_case_agent():
    return TestCaseAgent(model_name=GENAI_MODEL)

# --- API Endpoints ---

@app.post("/api/generate", response_model=GenerateResponse, tags=["AI Generation"], summary="Generate Test Cases",
    description="Generates test cases from either a single requirement string or a full document's text.")
async def generate_test_cases(request: RequirementRequest, user: Dict[str, Any] = Depends(get_current_user), agent: TestCaseAgent = Depends(get_test_case_agent)):
    try:
        product_name = request.product_name or "General Product"
        requirements = []

        if request.document_text:
            segmented_text = agent.segment_requirements(document_text=request.document_text)
            requirements = json.loads(_clean_json_response(segmented_text))
        elif request.requirement:
            requirements = [request.requirement]
        else:
            raise HTTPException(status_code=400, detail="Either 'document_text' or 'requirement' must be provided.")

        if not requirements:
            return GenerateResponse(product_name=product_name, domains=[])

        classified_text = agent.classify_requirements(product_name=product_name, requirements=requirements)
        classified_data = json.loads(_clean_json_response(classified_text))
        
        final_domains = []
        for domain, reqs in classified_data.get("domains", {}).items():
            domain_test_cases = []
            for req in reqs:
                tc_text = agent.generate_initial_test_cases(requirement=req)
                tc_data = json.loads(_clean_json_response(tc_text))
                for tc in tc_data:
                    tc['traceability_id'] = f"{request.requirement_id}-{tc['test_case_id']}" if request.requirement_id else tc['test_case_id']
                domain_test_cases.extend([TestCase.model_validate(tc) for tc in tc_data])
            if domain_test_cases:
                final_domains.append(DomainGroup(domain=domain, test_cases=domain_test_cases))
        
        # Fallback for requirements that might not get classified
        classified_reqs = {req for domain_reqs in classified_data.get("domains", {}).values() for req in domain_reqs}
        unclassified_reqs = [req for req in requirements if req not in classified_reqs]
        
        if unclassified_reqs:
            unclassified_test_cases = []
            for req in unclassified_reqs:
                tc_text = agent.generate_initial_test_cases(requirement=req)
                tc_data = json.loads(_clean_json_response(tc_text))
                unclassified_test_cases.extend([TestCase.model_validate(tc) for tc in tc_data])
            if unclassified_test_cases:
                final_domains.append(DomainGroup(domain="General", test_cases=unclassified_test_cases))

        return GenerateResponse(product_name=classified_data.get("product_name", product_name), domains=final_domains)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-manual-test-case-details", response_model=ManualTestCaseDetailsResponse, tags=["AI Generation"], summary="Generate Manual Test Case Details",
    description="Generates AI-driven details (compliance tag, test case ID, traceability ID) for a manually created test case.")
async def generate_manual_test_case_details(request: ManualTestCaseDetailsRequest, user: Dict[str, Any] = Depends(get_current_user), agent: TestCaseAgent = Depends(get_test_case_agent)):
    try:
        # Combine title and steps to form a requirement for the AI agent
        requirement_text = f"Title: {request.title}\nSteps: {request.steps}"
        
        # Use the AI to generate initial test cases (we only need one for details)
        tc_text = agent.generate_initial_test_cases(requirement=requirement_text)
        tc_data = json.loads(_clean_json_response(tc_text))

        if not tc_data:
            raise HTTPException(status_code=500, detail="AI failed to generate test case details.")

        # Take the first generated test case to extract details
        first_tc = tc_data[0]

        # Classify the domain using the AI agent
        classified_text = agent.classify_requirements(product_name=request.product_name or "General Product", requirements=[requirement_text])
        classified_data = json.loads(_clean_json_response(classified_text))
        
        # Extract the domain, defaulting to "General" if classification fails or is empty
        classified_domain = "General"
        if classified_data and "domains" in classified_data:
            # Get the first domain that has requirements, or default to "General"
            for domain_name, reqs in classified_data["domains"].items():
                if reqs:
                    classified_domain = domain_name
                    break

        # Generate traceability_id
        traceability_id = f"{request.requirement_id}-{first_tc['test_case_id']}" if request.requirement_id else first_tc['test_case_id']

        return ManualTestCaseDetailsResponse(
            test_case_id=first_tc['test_case_id'],
            compliance_tag=first_tc['compliance_tag'],
            traceability_id=traceability_id,
            domain=classified_domain
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload", response_model=UploadResponse, tags=["File Handling"], summary="Upload and Parse Document",
    description="Uploads a .pdf, .docx, or .txt file, extracts the text content, and returns it.")
async def upload_document(user: Dict[str, Any] = Depends(get_current_user), file: UploadFile = File(...)):
    """
    Handles file uploads, parsing the text from PDF, DOCX, or TXT files.
    """
    content = await file.read()
    text = ""
    filename = file.filename.lower()

    try:
        if filename.endswith('.pdf'):
            try:
                reader = PdfReader(io.BytesIO(content))
                text = " ".join(page.extract_text() for page in reader.pages if page.extract_text())
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error parsing PDF file: {e}")
        
        elif filename.endswith('.docx'):
            try:
                doc = Document(io.BytesIO(content))
                text = "\n".join(para.text for para in doc.paragraphs if para.text)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error parsing DOCX file: {e}")

        elif filename.endswith('.txt'):
            try:
                text = content.decode('utf-8')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error decoding TXT file: {e}")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file extension. Please upload .pdf, .docx, or .txt")
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract any text from the document. The file might be empty or scanned.")

        return UploadResponse(filename=file.filename, text=text)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while processing the file: {str(e)}")



# --- Finalized Cases CRUD ---

@app.get("/api/finalized-cases", response_model=List[FinalizedCasesDoc], tags=["Finalized Cases"], summary="Get All Finalized Test Case Documents",
    description="Retrieves a list of all test case documents that have been finalized by the user.")
async def get_finalized_cases(user: Dict[str, Any] = Depends(get_current_user)):
    try:
        docs_ref = db.collection('users').document(user['uid']).collection('finalized_cases').stream()
        cases = []
        for doc in docs_ref:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            cases.append(FinalizedCasesDoc.model_validate(doc_data))
        return cases
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/finalized-cases", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["Finalized Cases"], summary="Create a New Finalized Document",
    description="Saves a new collection of generated test cases as a finalized document.")
async def create_finalized_cases(payload: GenerateResponse, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        _, doc_ref = db.collection('users').document(user['uid']).collection('finalized_cases').add(payload.model_dump())
        return PostResponse(id=doc_ref.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/finalized-cases/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Finalized Cases"], summary="Update a Finalized Document",
    description="Updates an existing finalized test case document. Used for actions like deleting a single test case from a document.")
async def update_finalized_cases(doc_id: str, payload: GenerateResponse, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        db.collection('users').document(user['uid']).collection('finalized_cases').document(doc_id).set(payload.model_dump())
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/finalized-cases/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Finalized Cases"], summary="Delete a Finalized Document",
    description="Deletes an entire finalized test case document and all its contents.")
async def delete_finalized_cases(doc_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        db.collection('users').document(user['uid']).collection('finalized_cases').document(doc_id).delete()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/test-cases/{doc_id}/{case_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Finalized Cases"], summary="Delete a Single Test Case",
    description="Deletes a single test case from within a finalized document.")
async def delete_test_case(doc_id: str, case_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        doc_ref = db.collection('users').document(user['uid']).collection('finalized_cases').document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Document not found")

        doc_data = doc.to_dict()
        
        # Filter out the test case
        new_domains = []
        for domain_group in doc_data.get("domains", []):
            filtered_test_cases = [tc for tc in domain_group.get("test_cases", []) if tc.get("test_case_id") != case_id]
            if filtered_test_cases: # Only keep domain if it has test cases
                new_domains.append({
                    "domain": domain_group.get("domain"),
                    "test_cases": filtered_test_cases
                })

        # If all domains are empty, delete the document
        if not new_domains:
            doc_ref.delete()
        else:
            doc_ref.update({"domains": new_domains})
            
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ... other endpoints like /api/upload, /api/history etc.

# --- Jira Integration ---
@app.post("/api/jira/create-issue", tags=["Jira Integration"], summary="Create a Jira Issue from a Test Case",
    description="Creates a new issue in a specified Jira project from a single test case.")
async def create_jira_issue(request: JiraIssueRequest, user: Dict[str, Any] = Depends(get_current_user)):
    if not jira:
        raise HTTPException(status_code=503, detail="Jira integration is not configured on the server.")
    
    try:
        # Format the test case steps into a string for the Jira description
        steps_str = ""
        if isinstance(request.test_case.steps, list):
            steps_str = "\n".join([f"Step {s['step']}: {s['action']} -> {s['expected_result']}" for s in request.test_case.steps])
        else:
            # Improved formatting for manual test case steps
            manual_steps = str(request.test_case.steps).split('\n')
            steps_str = "\n".join([f"- {line.strip()}" for line in manual_steps if line.strip()])

        issue_data = {
            "project": {"key": request.project_key},
            "summary": f"{request.test_case.test_case_id}: {request.test_case.title}",
            "description": f"h2. Test Case Details\n"
            f"*Test Case ID:* {request.test_case.test_case_id}\n"
            f"*Title:* {request.test_case.title}\n"
            f"*Priority:* {request.test_case.priority}\n"
            f"*Type:* {request.test_case.type}\n"
            f"*Compliance:* {request.test_case.compliance_tag}\n"
            f"h2. Test Steps\n"
            f"{steps_str}\n"
            f"h2. Traceability ID\n"
            f"{request.test_case.traceability_id}",
            "issuetype": {"name": request.issue_type},
        }
        
        new_issue = jira.issue_create(fields=issue_data)
        
        return {"issue_key": new_issue['key'], "url": f"{JIRA_URL}/browse/{new_issue['key']}"}

    except Exception as e:
        # Catch potential errors from the Jira API (e.g., project not found, invalid credentials)
        raise HTTPException(status_code=500, detail=f"Failed to create Jira issue: {str(e)}")
