import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from google.cloud import bigquery, storage
import firebase_admin
from firebase_admin import credentials, firestore
from unittest.mock import MagicMock
from config import PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE

bq_client = None
storage_client = None
db = None

def get_db():
    global db
    if db is None:
        if "PYTEST_CURRENT_TEST" not in os.environ:
            print("Attempting to initialize Firebase Admin SDK with Application Default Credentials...")
            try:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                print("Firebase Admin SDK initialized successfully.")
            except Exception as e:
                print(f"Error initializing Firebase Admin SDK: {e}")
                raise
        else:
            print("PYTEST_CURRENT_TEST is set, using MagicMock for db.")
            db = MagicMock()
    return db

if "PYTEST_CURRENT_TEST" not in os.environ:
    bq_client = bigquery.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)
    db = get_db()
else:
    bq_client = MagicMock()
    storage_client = MagicMock()
    db = get_db()

def create_bigquery_dataset_and_table():
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    dataset_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}"
    try:
        bq_client.get_dataset(dataset_id)
    except Exception:
        dataset = bigquery.Dataset(dataset_id)
        bq_client.create_dataset(dataset, timeout=30)

    table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
    try:
        bq_client.get_table(table_id)
    except Exception:
        schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("filename", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("upload_date", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("embedding", "FLOAT", mode="REPEATED"),
        ]
        table = bigquery.Table(table_id, schema=schema)
        bq_client.create_table(table)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_bigquery_dataset_and_table()
    yield
