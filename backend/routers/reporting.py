from google.cloud import bigquery
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from security import get_current_user
from database import get_bq_client
from config import PROJECT_ID, BIGQUERY_DATASET, AUDIT_TABLE

router = APIRouter()

@router.get("/api/reports/audit-logs", tags=["Reporting"], summary="Get Audit Logs",
    description="Retrieves audit logs from BigQuery with optional filters.")
async def get_audit_logs(
    user: Dict[str, Any] = Depends(get_current_user),
    bq_client: bigquery.Client = Depends(get_bq_client),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g., 'user_login', 'create_finalized_cases')"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering logs (e.g., '2023-01-01T00:00:00')"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering logs (e.g., '2023-01-31T23:59:59')"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    try:
        user_id = user["uid"]
        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"

        query_parts = [f"SELECT * FROM `{table_id}` WHERE user_id = @user_id"]
        query_params = [
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
        ]

        if event_type:
            query_parts.append("AND event_type = @event_type")
            query_params.append(bigquery.ScalarQueryParameter("event_type", "STRING", event_type))
        
        if start_date:
            query_parts.append("AND timestamp >= @start_date")
            query_params.append(bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date))
        
        if end_date:
            query_parts.append("AND timestamp <= @end_date")
            query_params.append(bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date))
        
        query_parts.append("ORDER BY timestamp DESC")
        query_parts.append(f"LIMIT {limit} OFFSET {offset}")

        query_job = bq_client.query(" ".join(query_parts), job_config=bigquery.QueryJobConfig(query_parameters=query_params))
        
        results = []
        for row in query_job:
            results.append(dict(row))
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reports/summary", tags=["Reporting"], summary="Get Audit Summary",
    description="Provides a summary of audit events for the authenticated user.")
async def get_audit_summary(
    user: Dict[str, Any] = Depends(get_current_user),
    bq_client: bigquery.Client = Depends(get_bq_client),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering logs (e.g., '2023-01-01T00:00:00')"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering logs (e.g., '2023-01-31T23:59:59')")
):
    try:
        user_id = user["uid"]
        table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{AUDIT_TABLE}"

        query_parts = [
            f"SELECT event_type, COUNT(*) as count FROM `{table_id}` WHERE user_id = @user_id"
        ]
        query_params = [
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
        ]

        if start_date:
            query_parts.append("AND timestamp >= @start_date")
            query_params.append(bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date))
        
        if end_date:
            query_parts.append("AND timestamp <= @end_date")
            query_params.append(bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date))
        
        query_parts.append("GROUP BY event_type ORDER BY count DESC")

        query_job = bq_client.query(" ".join(query_parts), job_config=bigquery.QueryJobConfig(query_parameters=query_params))
        
        summary = []
        for row in query_job:
            summary.append(dict(row))
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
