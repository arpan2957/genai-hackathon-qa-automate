from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request
from typing import Dict, Any
import io
from docx import Document
from pypdf import PdfReader

from models import UploadResponse
from security import get_current_user
from audit import log_audit_event

router = APIRouter()

@router.post("/api/upload", response_model=UploadResponse, tags=["File Handling"], summary="Upload and Parse Document",
    description="Uploads a .pdf, .docx, or .txt file, extracts the text content, and returns it.")
async def upload_document(req: Request, user: Dict[str, Any] = Depends(get_current_user), file: UploadFile = File(...)):
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

        log_audit_event(req, user, "upload_document", details={"filename": file.filename})

        return UploadResponse(filename=file.filename, text=text)
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while processing the file: {str(e)}")
