# AI Test Case Generator

This project is a web-based tool designed to accelerate the Quality Assurance (QA) process for healthcare software. It leverages the Google Gemini AI model to analyze natural language software requirements and automatically generate a comprehensive set of structured test cases.

## Architecture

The project follows a modern client-server architecture:

*   **Frontend:** A single-page application built with **React** and styled with **Tailwind CSS**. It provides a clean user interface for inputting requirements and displaying the generated test cases.
*   **Backend:** A RESTful API built with **Python** and the **FastAPI** framework. This server is responsible for handling requests from the frontend, communicating with the Google Gemini API, and returning the structured test case data.

## Local Development

To run this project locally, you will need to run the frontend and backend servers in two separate terminals.

### Backend (FastAPI)

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Install dependencies:**
    ```bash
    pip3 install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the `backend` directory and add your Google API Key and Frontend Origin:
    ```
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    FRONTEND_ORIGIN="http://localhost:3000"
    # Optional: Jira credentials if you are testing Jira integration locally
    # JIRA_URL="https://your-domain.atlassian.net"
    # JIRA_USERNAME="your-email@example.com"
    # JIRA_API_TOKEN="your-api-token"
    ```

4.  **Run the server:**
    ```bash
    uvicorn main:app --reload
    ```
    The backend server will be running at `http://127.0.0.1:8000`.

### Frontend (React)

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Configure Local Environment Variables:**
    For local development, the application will automatically connect to the backend server running at `http://127.0.0.1:8000`. If you need to override this (for example, to point to a staging backend), you can create a `.env` file in the `frontend` directory:
    ```
    REACT_APP_BACKEND_URL="http://your-staging-backend-url.com"
    ```

4.  **Run the application:**
    ```bash
    npm start
    ```
    The frontend development server will start, and you can view the application in your browser at `http://localhost:3000`.

## Deployment

This application supports both automated and manual deployment strategies.

### Automated Deployment (Recommended)

The application uses GitHub Actions for automated CI/CD with path-based triggers, security scanning, and zero-downtime deployments.

#### Quick Setup

1. **Run the setup script:**
   ```bash
   ./scripts/setup-gcp-cicd.sh YOUR_PROJECT_ID your-github-username/repository-name
   ```

2. **Add GitHub Secrets:**
   Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):
   ```
   GCP_PROJECT_ID: your-gcp-project-id
   FIREBASE_PROJECT_ID: your-firebase-project-id
   WIF_PROVIDER: projects/.../workloadIdentityPools/github-actions-pool/providers/github-actions-provider
   WIF_SERVICE_ACCOUNT: github-actions-sa@your-project.iam.gserviceaccount.com
   FIREBASE_TOKEN: your-firebase-ci-token
   ```

3. **Update Secret Manager:**
   ```bash
   echo "your-actual-google-api-key" | gcloud secrets versions add google-api-key --data-file=-
   ```

4. **Push to main branch** to trigger automated deployment.

#### Features

- **Path-based triggers**: Only deploy what changed (backend/ or frontend/)
- **Security scanning**: Automated vulnerability detection and compliance checks
- **Keyless authentication**: Workload Identity Federation (no service account keys)
- **Zero-downtime deployment**: Rolling updates with health checks
- **Comprehensive testing**: Unit tests, linting, and smoke tests
- **Monitoring**: Built-in observability and alerting

For detailed setup instructions, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

#### Pipeline Status

- **Backend**: Deploys to Google Cloud Run (containerized FastAPI)
- **Frontend**: Deploys to Firebase Hosting (static React build)
- **Security**: Daily security scans and compliance checks
- **Monitoring**: Cloud Logging, metrics, and health checks

### Manual Deployment (Fallback)

#### Backend Deployment (Google Cloud Run)

**Prerequisites:**
*   Google Cloud SDK (`gcloud`) installed and configured.
*   A GCP project with the Cloud Run and Artifact Registry APIs enabled.

1.  **Deploy using Cloud Build:**
    ```bash
    cd backend
    gcloud builds submit --config cloudbuild.yaml
    ```

#### Frontend Deployment (Firebase Hosting)

**Prerequisites:**
*   Firebase CLI installed (`npm install -g firebase-tools`).
*   A Firebase project created in the Firebase console.

1.  **Deploy using Cloud Build:**
    ```bash
    cd frontend
    gcloud builds submit --config cloudbuild.yaml
    ```

### Testing Deployment Setup

Validate your deployment configuration:

```bash
./scripts/test-deployment.sh YOUR_PROJECT_ID your-github-username/repository-name
```

This script checks:
- GCP project access and API enablement
- Service accounts and IAM permissions
- Workload Identity Federation setup
- Secret Manager configuration
- Resource creation (Artifact Registry, GCS, BigQuery)
- GitHub Actions workflow validation
