from fastapi import APIRouter, Depends, Request, status, HTTPException
from typing import Dict, Any
from datetime import datetime

from models import FeedbackRequest
from security import get_current_user
from database import get_db
from audit import log_audit_event

router = APIRouter()

@router.post("/api/feedback", status_code=status.HTTP_201_CREATED, tags=["Feedback"], summary="Submit Feedback for a Generated Test Case",
    description="Submits feedback on the quality of a generated test case, which will be used for future model fine-tuning.")
async def submit_feedback(request_body: FeedbackRequest, req: Request, user: Dict[str, Any] = Depends(get_current_user), db=Depends(get_db)):
    try:
        feedback_data = request_body.dict()
        feedback_data['user_id'] = user['uid']
        feedback_data['timestamp'] = datetime.now()
        db.collection('finetuning_data').add(feedback_data)
        
        log_audit_event(req, user, "submit_feedback", details={
            "test_case_id": request_body.original_test_case.test_case_id,
            "rating": request_body.rating
        })
        
        return {"message": "Feedback submitted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
