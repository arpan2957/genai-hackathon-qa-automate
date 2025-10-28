from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import os
from google.cloud import bigquery

from models import FineTuningResponse, UserProfile, AuditLogEntry, AuditSummaryEntry
from security import is_admin
from database import db, storage_client, bq_client
from audit import log_audit_event
from config import PROJECT_ID, BIGQUERY_DATASET, AUDIT_TABLE
from google.cloud import aiplatform
from firebase_admin import auth

router = APIRouter()

MIN_FEEDBACK_THRESHOLD = 100

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
async def trigger_finetuning(req: Request, force: bool = False, user: dict = Depends(is_admin)):
    try:
        # 1. Check for currently active pipelines to prevent concurrent runs
        active_pipelines = aiplatform.PipelineJob.list(
            filter='state="PIPELINE_STATE_RUNNING" AND display_name~"tune-text-model-"'
        )
        if active_pipelines:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A fine-tuning pipeline is already in progress. Please wait for it to complete before starting a new one."
            )

        # 2. Query Firestore for new feedback data that hasn't been processed
        feedback_docs_query = db.collection('finetuning_data').where('processed_for_tuning', '!=', True)
        feedback_docs = list(feedback_docs_query.stream())

        # 3. Format the data
        training_data = []
        for doc in feedback_docs:
            data = doc.to_dict()
            if data.get('rating') == 'bad' and data.get('corrected_test_case'):
                training_example = {
                    "instruction": f"Requirement: {data['requirement']}\nOriginal Test Case: {json.dumps(data['original_test_case'])}",
                    "output": json.dumps(data['corrected_test_case'])
                }
                training_data.append(training_example)
        
        # 4. Check if there is enough new data, unless forced
        if not training_data:
            return FineTuningResponse(
                job_id="",
                status="NO_NEW_DATA",
                message="No new, unprocessed feedback data found to start a fine-tuning job."
            )

        if len(training_data) < MIN_FEEDBACK_THRESHOLD and not force:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail=f"Only {len(training_data)} new feedback examples found. A minimum of {MIN_FEEDBACK_THRESHOLD} is recommended. To proceed anyway, you can force the job."
            )

        # 5. Upload the data to Google Cloud Storage
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

        # 6. Create and run a fine-tuning job on Vertex AI
        job = run_finetuning_pipeline(gcs_uri=gcs_uri)
        log_audit_event(req, user, "trigger_finetuning", details={"job_id": job.resource_name, "gcs_uri": gcs_uri, "num_examples": len(training_data)})

        # 7. Mark the feedback documents as processed in a batch write
        batch = db.batch()
        for doc in feedback_docs:
            batch.update(doc.reference, {'processed_for_tuning': True})
        batch.commit()
        print(f"Marked {len(feedback_docs)} documents as processed.")

        return FineTuningResponse(
            job_id=job.resource_name,
            status=str(job.state),
            message=f"Fine-tuning job has been successfully triggered with {len(training_data)} new examples. Data uploaded to {gcs_uri}."
        )

    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTPException to keep status code and detail
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/admin/users", response_model=List[UserProfile], tags=["Admin"], summary="List All Users",
    description="Retrieves a list of all registered users.")
async def list_users(req: Request, user: dict = Depends(is_admin)):
    try:
        log_audit_event(req, user, "list_users")
        users = auth.list_users().users
        user_profiles = []
        for u in users:
            user_profiles.append(UserProfile(
                uid=u.uid,
                email=u.email,
                display_name=u.display_name,
                created_at=u.user_metadata.creation_timestamp
            ))
        return user_profiles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"], summary="Delete User and All Associated Data",
    description="Deletes a user from Firebase Authentication and all their associated data in Firestore and BigQuery.")
async def delete_user(req: Request, user_id: str, user: dict = Depends(is_admin)):
    try:
        # Log the admin action first
        log_audit_event(req, user, "delete_user", details={"deleted_user_id": user_id})

        # 1. Delete from Firebase Authentication
        auth.delete_user(user_id)

        # 2. Delete user's data from Firestore
        user_doc_ref = db.collection("users").document(user_id)
        
        # Delete subcollections
        for subcollection in ["finalized_test_cases", "knowledge_base"]:
            for doc in user_doc_ref.collection(subcollection).stream():
                doc.reference.delete()
        
        user_doc_ref.delete()

        # 3. Delete user's data from BigQuery
        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"
        query = f"DELETE FROM `{table_id}` WHERE user_id = @user_id"
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)])
        bq_client.query(query, job_config=job_config).result()

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/admin/audit-logs", response_model=List[AuditLogEntry], tags=["Admin"], summary="Get Detailed Audit Logs",
    description="Retrieves detailed audit logs with filtering capabilities.")
async def get_audit_logs(
    req: Request,
    user: dict = Depends(is_admin),
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    try:
        log_audit_event(req, user, "get_audit_logs", details={"filter_user_id": user_id, "filter_event_type": event_type, "filter_start_date": str(start_date), "filter_end_date": str(end_date)})
        
        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"
        query = f"SELECT * FROM `{table_id}` WHERE 1=1"
        params = []
        param_types = []

        if user_id:
            query += " AND user_id = @user_id"
            params.append(bigquery.ScalarQueryParameter("user_id", "STRING", user_id))
        if event_type:
            query += " AND event_type = @event_type"
            params.append(bigquery.ScalarQueryParameter("event_type", "STRING", event_type))
        if start_date:
            query += " AND timestamp >= @start_date"
            params.append(bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date))
        if end_date:
            query += " AND timestamp <= @end_date"
            params.append(bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date))

        query += " ORDER BY timestamp DESC LIMIT 1000"
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = bq_client.query(query, job_config=job_config)
        
        results = [dict(row) for row in query_job.result()]
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/admin/audit-summary", response_model=List[AuditSummaryEntry], tags=["Admin"], summary="Get Audit Summary Statistics",
    description="Retrieves aggregated statistics of audit events.")
async def get_audit_summary(
    req: Request,
    user: dict = Depends(is_admin),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    try:
        log_audit_event(req, user, "get_audit_summary", details={"filter_start_date": str(start_date), "filter_end_date": str(end_date)})

        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"
        query = f"""
            SELECT event_type, COUNT(*) as count
            FROM `{table_id}`
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND timestamp >= @start_date"
            params.append(bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date))
        if end_date:
            query += " AND timestamp <= @end_date"
            params.append(bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date))

        query += " GROUP BY event_type ORDER BY count DESC"

        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = bq_client.query(query, job_config=job_config)

        results = [dict(row) for row in query_job.result()]
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
