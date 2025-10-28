from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import json
from datetime import datetime
import os

from models import FineTuningResponse, UserProfile
from security import is_admin
from database import db, storage_client, bq_client
from config import PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE, AUDIT_TABLE
from google.cloud import aiplatform
from firebase_admin import auth

router = APIRouter()

def run_finetuning_pipeline(gcs_uri: str) -> aiplatform.PipelineJob:
    # The display name for the pipeline job
    display_name = f"tune-text-model-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # The path to the pipeline template. This is a predefined template for tuning text models.
    pipeline_path = "https://us-kfp.pkg.dev/ml-pipeline/large-language-model-pipelines/tune-text-model/v1.1.0"

    # The parameters for the pipeline. This is where we specify the model, training data, etc.
    pipeline_parameters = {
        "train_steps": 300,
        "project": PROJECT_ID,
        "location": "us-central1",
        "dataset_uri": gcs_uri,
        "large_model_reference": "gemini-1.0-pro-001",
        "model_display_name": f"tuned-gemini-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }

    # Create and run the pipeline job.
    job = aiplatform.PipelineJob(
        display_name=display_name,
        template_path=pipeline_path,
        parameter_values=pipeline_parameters,
        enable_caching=False,
    )

    job.submit()

    return job

@router.post("/api/admin/trigger-finetuning", response_model=FineTuningResponse, tags=["Admin"], summary="Trigger a Model Fine-Tuning Job",
    description="Starts a new fine-tuning job on Vertex AI using the collected feedback data.")
async def trigger_finetuning(is_admin: bool = Depends(is_admin)):
    try:
        # 1. Query Firestore for feedback data
        feedback_docs = db.collection('finetuning_data').stream()

        # 2. Format the data
        training_data = []
        for doc in feedback_docs:
            data = doc.to_dict()
            if data.get('rating') == 'bad' and data.get('corrected_test_case'):
                training_example = {
                    "instruction": f"Requirement: {data['requirement']}\nOriginal Test Case: {json.dumps(data['original_test_case'])}",
                    "output": json.dumps(data['corrected_test_case'])
                }
                training_data.append(training_example)
        
        if not training_data:
            return FineTuningResponse(
                job_id="",
                status="NO_DATA",
                message="No valid feedback data found to start a fine-tuning job."
            )

        # 3. Upload the data to Google Cloud Storage
        GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
        if not GCS_BUCKET_NAME:
            raise HTTPException(status_code=500, detail="GCS_BUCKET_NAME environment variable is not set.")

        jsonl_data = "\n".join(json.dumps(item) for item in training_data)
        
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_name = f"finetuning-data/training-data-{datetime.now().strftime('%Y%m%d%H%M%S')}.jsonl"
        blob = bucket.blob(blob_name)
        
        blob.upload_from_string(jsonl_data, content_type='application/jsonl')
        
        gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
        print(f"Training data uploaded to {gcs_uri}")

        # 4. Create and run a fine-tuning job on Vertex AI
        job = run_finetuning_pipeline(gcs_uri=gcs_uri)

        return FineTuningResponse(
            job_id=job.resource_name,
            status=str(job.state),
            message=f"Fine-tuning job has been successfully triggered with {len(training_data)} examples. Data uploaded to {gcs_uri}."
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/admin/users", response_model=List[UserProfile], tags=["Admin"], summary="List All Users",
    description="Retrieves a list of all registered users.")
async def list_users(is_admin: bool = Depends(is_admin)):
    try:
        users = auth.list_users().users
        user_profiles = []
        for user in users:
            user_profiles.append(UserProfile(
                uid=user.uid,
                email=user.email,
                display_name=user.display_name,
                created_at=user.user_metadata.creation_timestamp
            ))
        return user_profiles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"], summary="Delete User and All Associated Data",
    description="Deletes a user from Firebase Authentication and all their associated data in Firestore and BigQuery.")
async def delete_user(user_id: str, is_admin: bool = Depends(is_admin)):
    try:
        # 1. Delete from Firebase Authentication
        auth.delete_user(user_id)

        # 2. Delete user's data from Firestore
        user_doc_ref = db.collection("users").document(user_id)
        
        # Delete finalized_test_cases subcollection
        for doc in user_doc_ref.collection("finalized_test_cases").stream():
            doc.reference.delete()
        
        # Delete knowledge_base subcollection
        for doc in user_doc_ref.collection("knowledge_base").stream():
            doc.reference.delete()
        
        # Delete the user's main document
        user_doc_ref.delete()

        # 3. Delete user's data from BigQuery
        # Delete from knowledge_base table
        kb_table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
        kb_query = f"DELETE FROM `{kb_table_id}` WHERE user_id = '{user_id}'"
        bq_client.query(kb_query).result()

        # Delete from audit_log table (anonymized user_id might be stored here)
        audit_table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"
        audit_query = f"DELETE FROM `{audit_table_id}` WHERE user_id = '{user_id}'"
        bq_client.query(audit_query).result()

        return status.HTTP_204_NO_CONTENT
    except auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
