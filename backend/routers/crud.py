from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import List, Dict, Any

from models import CreateFinalizedCasesRequest, FinalizedCasesDoc
from security import get_current_user
from database import get_db
from audit import log_audit_event

router = APIRouter()

@router.post("/api/finalized-cases", status_code=status.HTTP_201_CREATED, tags=["Test Cases"], summary="Finalize Test Cases",
    description="Saves a generated test case document to the user's finalized collection in Firestore.")
async def create_finalized_cases(req: Request, request_body: CreateFinalizedCasesRequest, user: Dict[str, Any] = Depends(get_current_user), db = Depends(get_db)):
    try:
        user_id = user["uid"]
        doc_ref = db.collection('users').document(user_id).collection('finalized_cases').document()
        doc_ref.set(request_body.model_dump())
        
        log_audit_event(req, user, "create_finalized_cases", details={
            "document_id": doc_ref.id,
            "product_name": request_body.product_name
        })
        
        return {"id": doc_ref.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/finalized-cases", response_model=List[FinalizedCasesDoc], tags=["Test Cases"], summary="Get All Finalized Cases",
    description="Retrieves all finalized test case documents for the authenticated user.")
async def get_finalized_cases(request: Request, user: Dict[str, Any] = Depends(get_current_user), db = Depends(get_db)):
    try:
        docs_ref = db.collection('users').document(user['uid']).collection('finalized_cases').stream()
        cases = []
        for doc in docs_ref:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            cases.append(FinalizedCasesDoc(**doc_data))
        return cases
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/finalized-cases/{doc_id}", status_code=status.HTTP_200_OK, tags=["Test Cases"], summary="Update a Finalized Document",
    description="Updates an entire finalized test case document.")
async def update_finalized_cases(req: Request, doc_id: str, request_body: CreateFinalizedCasesRequest, user: Dict[str, Any] = Depends(get_current_user), db = Depends(get_db)):
    try:
        user_id = user["uid"]
        doc_ref = db.collection('users').document(user_id).collection('finalized_cases').document(doc_id)
        doc_ref.set(request_body.model_dump(), merge=True)
        
        log_audit_event(req, user, "update_finalized_cases", details={"document_id": doc_id})
        
        return {"id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/test-cases/{doc_id}/{case_id}", tags=["Test Cases"], summary="Delete a Test Case",
    description="Deletes a specific test case from a finalized document for the authenticated user.")
async def delete_test_case(req: Request, doc_id: str, case_id: str, user: Dict[str, Any] = Depends(get_current_user), db = Depends(get_db)):
    try:
        user_id = user["uid"]
        doc_ref = db.collection("users").document(user_id).collection("finalized_cases").document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Document not found")

        doc_data = doc.to_dict()
        updated_domains = []
        case_found = False

        for domain_group in doc_data.get("domains", []):
            updated_test_cases = [tc for tc in domain_group.get("test_cases", []) if tc.get("test_case_id") != case_id]
            if len(updated_test_cases) < len(domain_group.get("test_cases", [])):
                case_found = True
            if updated_test_cases:
                updated_domains.append({"domain": domain_group["domain"], "test_cases": updated_test_cases})

        if not case_found:
            raise HTTPException(status_code=404, detail="Test case not found in document")

        if not updated_domains:
            # If no domains left, delete the entire document
            doc_ref.delete()
            log_audit_event(req, user, "delete_document", details={"document_id": doc_id})
        else:
            doc_ref.update({"domains": updated_domains})
            log_audit_event(req, user, "delete_test_case", details={
                "document_id": doc_id,
                "test_case_id": case_id
            })

        return {"message": "Test case deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
