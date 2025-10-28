import hashlib
import json
from datetime import datetime
from fastapi import Request
from google.cloud import bigquery
from config import PROJECT_ID, BIGQUERY_DATASET, GDPR_COMPLIANT, GDPR_SECRET_KEY, AUDIT_TABLE


# BigQuery Table Schema for 'audit_log':
# This schema is a recommendation. BigQuery can often infer schema from JSON, 
# but explicit definition is good practice for production.
# CREATE TABLE `your-gcp-project-id.knowledge_base.audit_log` (
#   user_id STRING,
#   event_type STRING,
#   timestamp TIMESTAMP,
#   document_id STRING, # Optional, for knowledge base or finalized cases
#   test_case_id STRING, # Optional, for test case specific events
#   filename STRING, # Optional, for knowledge base uploads
#   integration_name STRING, # Optional, for ALM integrations
#   issue_key STRING, # Optional, for ALM integrations
#   rating STRING, # Optional, for feedback
#   email STRING # Optional, for user login (anonymized if GDPR_COMPLIANT)
# );

# BigQuery Table Schema for 'knowledge_base.documents':
# CREATE TABLE `your-gcp-project-id.knowledge_base.documents` (
#   id STRING,
#   filename STRING,
#   upload_date TIMESTAMP,
#   user_id STRING,
#   document_type STRING, # 'text', 'image', 'multimodal'
#   text_content STRING, # Full text content
#   embedding ARRAY<FLOAT>, # Text embedding
#   image_url STRING, # GCS URL for image
#   image_embedding ARRAY<FLOAT> # Image embedding
# );

def _anonymize_data(data: str, secret_key: str) -> str:
    """
    Generates a consistent, anonymized hash for a given data string.
    """
    if not data:
        return None
    hashed_data = hashlib.sha256((data + secret_key).encode('utf-8')).hexdigest()
    return hashed_data

def log_audit_event(request: Request, user: dict, event_type: str, details: dict = None):
    """
    Constructs and logs an audit event to BigQuery, including request info.

    Args:
        request: The FastAPI Request object to get IP and user agent.
        user: The authenticated user dictionary.
        event_type: The type of event being logged.
        details: An optional dictionary of additional event-specific data.
    """
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"

        event_data = {
            "user_id": user.get("uid"),
            "email": user.get("email"),
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "event_details": json.dumps(details) if details else None
        }

        # Merge specific details into the top-level for direct querying
        if details:
            event_data.update(details)

        if GDPR_COMPLIANT:
            if 'email' in event_data and event_data['email']:
                event_data['email'] = _anonymize_data(event_data['email'], GDPR_SECRET_KEY)
            if 'user_id' in event_data and event_data['user_id']:
                event_data['user_id'] = _anonymize_data(event_data['user_id'], GDPR_SECRET_KEY)

        print(f"Logging to BigQuery: {event_data}")
        errors = client.insert_rows_json(table_id, [event_data])
        if errors:
            print(f"Encountered errors while inserting rows: {errors}")
    except Exception as e:
        print(f"Failed to log audit event: {e}")
