from fastapi import APIRouter, Depends, File, UploadFile, Response, status, HTTPException
from typing import List, Dict, Any
from datetime import datetime
import io
from docx import Document
from pypdf import PdfReader

from models import *
from security import get_current_user
from database import db, bq_client
from config import PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE
from google.cloud import aiplatform

router = APIRouter()

@router.post("/api/knowledge-base/documents", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["Knowledge Base"], summary="Upload a New Knowledge Base Document",
    description="Uploads a new document to the user's knowledge base.")
async def create_knowledge_base_document(file: UploadFile = File(...), user: Dict[str, Any] = Depends(get_current_user)):
    try:
        content = await file.read()
        text = ""
        filename = file.filename.lower()

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

        # Generate embeddings
        model = aiplatform.TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
        embeddings = model.get_embeddings([text])
        embedding_values = [v.values for v in embeddings][0]

        # Save to Firestore
        doc_data = {
            "filename": file.filename,
            "upload_date": datetime.now(),
            "user_id": user['uid']
        }
        _, doc_ref = db.collection('users').document(user['uid']).collection('knowledge_base').add(doc_data)

        # Save to BigQuery
        rows_to_insert = [
            {
                "id": doc_ref.id,
                "filename": file.filename,
                "upload_date": doc_data["upload_date"].isoformat(),
                "user_id": user['uid'],
                "embedding": embedding_values
            }
        ]
        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
        errors = bq_client.insert_rows_json(table_id, rows_to_insert)
        if errors:
            raise HTTPException(status_code=500, detail=f"Error inserting rows into BigQuery: {errors}")

        return PostResponse(id=doc_ref.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/knowledge-base/documents", response_model=List[KnowledgeBaseDocument], tags=["Knowledge Base"], summary="Get All Knowledge Base Documents",
    description="Retrieves a list of all documents in the user's knowledge base.")
async def get_knowledge_base_documents(user: Dict[str, Any] = Depends(get_current_user)):
    try:
        docs_ref = db.collection('users').document(user['uid']).collection('knowledge_base').stream()
        documents = []
        for doc in docs_ref:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            documents.append(KnowledgeBaseDocument.model_validate(doc_data))
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/knowledge-base/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Knowledge Base"], summary="Delete a Knowledge Base Document",
    description="Deletes a document from the user's knowledge base.")
async def delete_knowledge_base_document(document_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        # Delete from Firestore
        db.collection('users').document(user['uid']).collection('knowledge_base').document(document_id).delete()

        # Delete from BigQuery
        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
        query = f"DELETE FROM `{table_id}` WHERE id = '{document_id}'"
        bq_client.query(query)

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
