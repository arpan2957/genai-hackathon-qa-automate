from fastapi import APIRouter, Depends, Response, status, HTTPException
from typing import List, Dict, Any

from models import *
from security import get_current_user
from database import get_db

router = APIRouter()

@router.get("/api/finalized-cases", response_model=List[FinalizedCasesDoc], tags=["Finalized Cases"], summary="Get All Finalized Test Case Documents",
    description="Retrieves a list of all test case documents that have been finalized by the user.")
async def get_finalized_cases(user: Dict[str, Any] = Depends(get_current_user), db = Depends(get_db)):
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

@router.post("/api/finalized-cases", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["Finalized Cases"], summary="Create a New Finalized Document",
    description="Saves a new collection of generated test cases as a finalized document.")
async def create_finalized_cases(payload: CreateFinalizedCasesRequest, user: Dict[str, Any] = Depends(get_current_user), db = Depends(get_db)):
    try:
        _, doc_ref = db.collection('users').document(user['uid']).collection('finalized_cases').add(payload.model_dump())
        return PostResponse(id=doc_ref.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/finalized-cases/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Finalized Cases"], summary="Update a Finalized Document",
    description="Updates an existing finalized test case document. Used for actions like deleting a single test case from a document.")
async def update_finalized_cases(doc_id: str, payload: CreateFinalizedCasesRequest, user: Dict[str, Any] = Depends(get_current_user), db = Depends(get_db)):
    try:
        db.collection('users').document(user['uid']).collection('finalized_cases').document(doc_id).set(payload.model_dump())
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/finalized-cases/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Finalized Cases"], summary="Delete a Finalized Document",
    description="Deletes an entire finalized test case document and all its contents.")
async def delete_finalized_cases(doc_id: str, user: Dict[str, Any] = Depends(get_current_user), db = Depends(get_db)):
    try:
        db.collection('users').document(user['uid']).collection('finalized_cases').document(doc_id).delete()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/test-cases/{doc_id}/{case_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Finalized Cases"], summary="Delete a Single Test Case",
    description="Deletes a single test case from within a finalized document.")
async def delete_test_case(doc_id: str, case_id: str, user: Dict[str, Any] = Depends(get_current_user), db = Depends(get_db)):
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
