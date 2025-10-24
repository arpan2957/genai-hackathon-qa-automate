from google.cloud import bigquery
from config import PROJECT_ID, BIGQUERY_DATASET, GDPR_COMPLIANT

AUDIT_TABLE = 'audit_log'

def log_audit_event(event_data: dict):
    """
    Logs an audit event to BigQuery.

    Args:
        event_data: A dictionary containing the event data.
    """
    try:
        if GDPR_COMPLIANT:
            if 'email' in event_data:
                event_data['email'] = 'anonymized_email'
            if 'user_id' in event_data:
                event_data['user_id'] = 'anonymized_user_id'

        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"

        errors = client.insert_rows_json(table_id, [event_data])
        if errors:
            print(f"Encountered errors while inserting rows: {errors}")
    except Exception as e:
        print(f"Failed to log audit event: {e}")
