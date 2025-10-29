from fastapi import APIRouter, Depends, File, UploadFile, Response, status, HTTPException, Form, Request
from typing import List, Dict, Any, Optional
from datetime import datetime
import io
from docx import Document
from pypdf import PdfReader
from PIL import Image
import base64
import google.generativeai as genai

from models import KnowledgeBaseDocument, PostResponse
from security import get_current_user
from database import db, bq_client, storage_client
from config import PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE, GCS_BUCKET_NAME
from google.cloud import aiplatform
from audit import log_audit_event

router = APIRouter()

@router.post("/api/knowledge-base/documents", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["Knowledge Base"], summary="Upload a New Knowledge Base Document",
    description="Uploads a new document (text or image) to the user's knowledge base.")
async def create_knowledge_base_document(
    request: Request,
    file: Optional[UploadFile] = File(None),
    image_file: Optional[UploadFile] = File(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    if not file and not image_file:
        raise HTTPException(status_code=400, detail="Either a text file or an image file must be provided.")

    text_content = ""
    text_embedding_values = None
    image_url = None
    image_embedding_values = None
    document_type = 'text'
    filename = ""

    # Process text file if provided
    if file:
        content = await file.read()
        filename = file.filename.lower()

        if filename.endswith('.pdf'):
            try:
                reader = PdfReader(io.BytesIO(content))
                text_content = " ".join(page.extract_text() for page in reader.pages if page.extract_text())
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error parsing PDF file: {e}")
        
        elif filename.endswith('.docx'):
            try:
                doc = Document(io.BytesIO(content))
                text_content = "\n".join(para.text for para in doc.paragraphs if para.text)
            except Exception as e:
        
                raise HTTPException(status_code=400, detail=f"Error parsing DOCX file: {e}")

        elif filename.endswith('.txt'):
            try:
                text_content = content.decode('utf-8')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error decoding TXT file: {e}")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported text file extension. Please upload .pdf, .docx, or .txt")
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="Could not extract any text from the document. The file might be empty or scanned.")

        # Generate text embeddings
        text_embedding_model = aiplatform.TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
        text_embeddings = text_embedding_model.get_embeddings([text_content])
        text_embedding_values = [v.values for v in text_embeddings][0]
        document_type = 'text'

    # Process image file if provided
    if image_file:
        if not GCS_BUCKET_NAME:
            raise HTTPException(status_code=500, detail="GCS_BUCKET_NAME environment variable is not set for image uploads.")

        image_content = await image_file.read()
        image_filename = f"knowledge_base/{user['uid']}/{datetime.now().isoformat()}_{image_file.filename}"
        
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(image_filename)
        blob.upload_from_string(image_content, content_type=image_file.content_type)
        image_url = f"gs://{GCS_BUCKET_NAME}/{image_filename}"

        # Generate image embeddings using a multi-modal model
        try:
            aiplatform.init(project=PROJECT_ID, location="us-central1")
            model = aiplatform.MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
            image = aiplatform.Image(image_bytes=image_content)
            embeddings = model.get_embeddings(image=image)
            image_embedding_values = embeddings.image_embedding
        except Exception as e:
            # Placeholder in case embedding fails, log the error and continue
            print(f"Warning: Image embedding generation failed: {e}. Using placeholder.")
            image_embedding_values = [0] * 1408 # Dimension for multimodalembedding@001
        
        if not file: # If only image is uploaded
            filename = image_file.filename
            document_type = 'image'
        elif file: # If both text and image are uploaded
            document_type = 'multimodal'

    # Save to Firestore
    doc_data = {
        "filename": filename,
        "upload_date": datetime.now(),
        "user_id": user['uid'],
        "document_type": document_type
    }
    if text_content: doc_data["text_content"] = text_content # Store text content for retrieval
    if image_url: doc_data["image_url"] = image_url
    
    _, doc_ref = db.collection('users').document(user['uid']).collection('knowledge_base').add(doc_data)

    # Save to BigQuery
    rows_to_insert = [
        {
            "id": doc_ref.id,
            "filename": filename,
            "upload_date": doc_data["upload_date"].isoformat(),
            "user_id": user['uid'],
            "document_type": document_type
        }
    ]
    if text_embedding_values: rows_to_insert[0]["embedding"] = text_embedding_values
    if image_embedding_values: rows_to_insert[0]["image_embedding"] = image_embedding_values
    if text_content: rows_to_insert[0]["text_content"] = text_content # Store text content in BQ for retrieval
    if image_url: rows_to_insert[0]["image_url"] = image_url

    table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
    errors = bq_client.insert_rows_json(table_id, rows_to_insert)
    if errors:
        raise HTTPException(status_code=500, detail=f"Error inserting rows into BigQuery: {errors}")

    log_audit_event(
        request,
        user,
        "upload_knowledge_base_document",
        details={
            "document_id": doc_ref.id,
            "filename": filename,
            "document_type": document_type
        }
    )

    return PostResponse(id=doc_ref.id)

@router.get("/api/knowledge-base/documents", response_model=List[KnowledgeBaseDocument], tags=["Knowledge Base"], summary="Get All Knowledge Base Documents",
    description="Retrieves a list of all documents in the user's knowledge base.")
async def get_knowledge_base_documents(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
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
async def delete_knowledge_base_document(document_id: str, request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        # Get document data to check for image_url
        doc_ref = db.collection('users').document(user['uid']).collection('knowledge_base').document(document_id)
        doc_snapshot = doc_ref.get()
        if not doc_snapshot.exists:
            raise HTTPException(status_code=404, detail="Document not found in Firestore.")
        doc_data = doc_snapshot.to_dict()

        # Delete from Firestore
        doc_ref.delete()

        # Delete from BigQuery
        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
        query = f"DELETE FROM `{table_id}` WHERE id = '{document_id}'"
        bq_client.query(query).result()

        # Delete image from GCS if it exists
        if "image_url" in doc_data and doc_data["image_url"]:
            gcs_path = doc_data["image_url"].replace(f"gs://{GCS_BUCKET_NAME}/", "")
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(gcs_path)
            if blob.exists():
                blob.delete()
                print(f"Deleted image {gcs_path} from GCS.")

        log_audit_event(
            request,
            user,
            "delete_knowledge_base_document",
            details={
                "document_id": document_id
            }
        )

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))