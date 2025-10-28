import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# --- AI Configuration ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("ERROR: GOOGLE_API_KEY not found in the backend/.env file")

GENAI_MODEL = os.getenv("GENAI_MODEL", "gemini-2.5-flash")
GENAI_VISION_MODEL = os.getenv("GENAI_VISION_MODEL", "gemini-2.5-pro") # Default to a vision-capable model
genai.configure(api_key=api_key)

# --- Vertex AI Configuration ---
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1"
BIGQUERY_DATASET = "knowledge_base"
BIGQUERY_TABLE = "documents"
AUDIT_TABLE = "audit_log"

# --- GCS Configuration ---
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

# --- Jira Configuration ---
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# --- Azure DevOps Configuration ---
AZURE_DEVOPS_URL = os.getenv("AZURE_DEVOPS_URL")
AZURE_DEVOPS_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT")
AZURE_DEVOPS_PAT = os.getenv("AZURE_DEVOPS_PAT")

# --- Polarion Configuration ---
POLARION_URL = os.getenv("POLARION_URL")
POLARION_USERNAME = os.getenv("POLARION_USERNAME")
POLARION_PASSWORD = os.getenv("POLARION_PASSWORD")
POLARION_PROJECT_ID = os.getenv("POLARION_PROJECT_ID")

# --- GDPR Configuration ---
GDPR_COMPLIANT = os.getenv("GDPR_COMPLIANT", "False").lower() == "true"
GDPR_SECRET_KEY = os.getenv("GDPR_SECRET_KEY")
if GDPR_COMPLIANT and not GDPR_SECRET_KEY:
    raise ValueError("ERROR: GDPR_SECRET_KEY must be set in .env if GDPR_COMPLIANT is true")

# --- Public API Configuration ---
PUBLIC_API_KEY = os.getenv("PUBLIC_API_KEY")
