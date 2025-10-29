import os
import datetime
from google.cloud import bigquery, storage
import firebase_admin
from firebase_admin import credentials, firestore
from unittest.mock import MagicMock
from config import PROJECT_ID, BIGQUERY_DATASET, AUDIT_TABLE

bq_client = None
storage_client = None
db = None

def init_db():
    global db, bq_client, storage_client
    if "PYTEST_CURRENT_TEST" not in os.environ:
        print("Initializing clients...")
        try:
            # Initialize Firebase
            if not firebase_admin._apps:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {
                    'projectId': PROJECT_ID,
                })
            db = firestore.client()

            # Initialize BigQuery and Storage
            bq_client = bigquery.Client(project=PROJECT_ID)
            storage_client = storage.Client(project=PROJECT_ID)
            print("Clients initialized successfully.")

            # Create BigQuery dataset and audit table if they don't exist
            dataset_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}"
            try:
                bq_client.get_dataset(dataset_id)
            except Exception:
                dataset = bigquery.Dataset(dataset_id)
                bq_client.create_dataset(dataset, timeout=30)

            table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"
            try:
                bq_client.get_table(table_id)
            except Exception:
                schema = [
                    bigquery.SchemaField("user_id", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("email", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("event_type", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
                    bigquery.SchemaField("ip_address", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("user_agent", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("document_id", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("test_case_id", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("filename", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("integration_name", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("issue_key", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("rating", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("event_details", "STRING", mode="NULLABLE"),
                ]
                table = bigquery.Table(table_id, schema=schema)
                bq_client.create_table(table)

        except Exception as e:
            print(f"Error initializing clients or creating BigQuery table: {e}")
            raise
    else:
        print("PYTEST_CURRENT_TEST is set, using MagicMock for clients.")
        db = MagicMock()
        bq_client = MagicMock()
        storage_client = MagicMock()

def get_db():
    return db

def get_bq_client():
    return bq_client

def log_event(user_id: str, email: str, event_type: str, details: dict):
    """Logs an audit event to BigQuery."""
    if bq_client:
        try:
            table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"
            row_to_insert = {
                "user_id": user_id,
                "email": email,
                "event_type": event_type,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                **details
            }
            errors = bq_client.insert_rows_json(table_id, [row_to_insert])
            if errors:
                print(f"Encountered errors while inserting rows: {errors}")
        except Exception as e:
            print(f"Failed to log event to BigQuery: {e}")


def create_bigquery_dataset_and_table():
    """Create BigQuery dataset and table for testing purposes."""
    global bq_client
    if not bq_client:
        bq_client = MagicMock()
    
    # For testing, we'll just use a mock client
    # In real scenarios, this would create actual BigQuery resources
    print("Mock BigQuery dataset and table created for testing.")

def close_db_connection():
    # No explicit close needed for these clients
    pass
