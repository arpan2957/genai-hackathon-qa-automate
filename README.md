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

## Manual Deployment

These steps outline how to manually deploy the application to Google Cloud Platform.

### Backend Deployment (Google Cloud Run)

**Prerequisites:**
*   Google Cloud SDK (`gcloud`) installed and configured.
*   A GCP project with the Cloud Run and Artifact Registry APIs enabled.

1.  **Build the Docker Image:**
    From the `backend` directory, build the Docker image:
    ```bash
    docker build -t gcr.io/YOUR_PROJECT_ID/ai-test-case-generator-backend .
    ```

2.  **Push the Image to Artifact Registry:**
    ```bash
    docker push gcr.io/YOUR_PROJECT_ID/ai-test-case-generator-backend
    ```

3.  **Deploy to Cloud Run:**
    ```bash
    gcloud run deploy ai-test-case-generator-backend \
      --image gcr.io/YOUR_PROJECT_ID/ai-test-case-generator-backend \
      --platform managed \
      --region asia-south1 \
      
      --set-env-vars GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY",FRONTEND_ORIGIN="https://your-firebase-project-id.web.app"
    ```
    **Note on Security:** After deployment, your Cloud Run service will be private. To allow your Firebase-hosted frontend to access it, you must grant the Firebase service account (typically `YOUR_PROJECT_ID@appspot.gserviceaccount.com`) the `roles/run.invoker` role on your Cloud Run service. You can do this via the GCP Console (Cloud Run -> Service -> Permissions) or using `gcloud` CLI.
    ```

### Frontend Deployment (Firebase Hosting)

**Prerequisites:**
*   Firebase CLI installed (`npm install -g firebase-tools`).
*   A Firebase project created in the Firebase console.

1.  **Initialize Firebase:**
    From the `frontend` directory, run:
    ```bash
    firebase init
    ```
    *   Select "Hosting: Configure files for Firebase Hosting and (optionally) set up GitHub Action deploys".
    *   Select your existing Firebase project.
    *   Set your public directory to `build`.
    *   Configure as a single-page app (rewrite all urls to /index.html).

2.  **Build the React App for Production:**
    From the `frontend` directory, run the following command, replacing the URL with your deployed Cloud Run service URL:
    ```bash
    REACT_APP_BACKEND_URL=https://your-cloud-run-service-url.run.app npm run build
    ```

3.  **Deploy to Firebase:**
    From the `frontend` directory, run:
    ```bash
    firebase deploy --only hosting
    ```
