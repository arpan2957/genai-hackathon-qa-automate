# Environment Variables Configuration Guide

This document outlines all environment variables used by the AI Test Case Generator and how they're handled in the CI/CD pipeline.

## 🔧 **Backend Environment Variables**

### **Core API Configuration**
```bash
GOOGLE_API_KEY                 # Google Gemini API Key (REQUIRED)
GOOGLE_CLOUD_PROJECT          # GCP Project ID (Auto-configured)
GCS_BUCKET_NAME              # GCS Bucket for knowledge base (Auto-configured)
GENAI_MODEL                  # Gemini model name (Default: gemini-2.5-flash)
GENAI_VISION_MODEL           # Gemini vision model (Default: gemini-2.5-pro)
```

### **Integration APIs (Optional)**
```bash
# Jira Integration
JIRA_URL                     # Jira instance URL
JIRA_USERNAME               # Jira username
JIRA_API_TOKEN              # Jira API token

# Azure DevOps Integration  
AZURE_DEVOPS_URL            # Azure DevOps URL
AZURE_DEVOPS_PROJECT        # Azure DevOps project name
AZURE_DEVOPS_PAT            # Azure DevOps Personal Access Token

# Polarion Integration
POLARION_URL                # Polarion instance URL
POLARION_USERNAME           # Polarion username
POLARION_PASSWORD           # Polarion password
POLARION_PROJECT_ID         # Polarion project ID
```

### **Security & Features**
```bash
GDPR_COMPLIANT              # Enable GDPR compliance (true/false)
GDPR_SECRET_KEY             # GDPR encryption key
PUBLIC_API_KEY              # Public API access key
AGENT_API_KEY               # Agent API access key
```

## 🌐 **Frontend Environment Variables**

### **Backend Connection**
```bash
REACT_APP_BACKEND_URL       # Backend API URL (Auto-configured from Cloud Run)
```

### **Firebase Configuration**
```bash
REACT_APP_FIREBASE_API_KEY              # Firebase API key
REACT_APP_FIREBASE_AUTH_DOMAIN          # Firebase auth domain
REACT_APP_FIREBASE_PROJECT_ID           # Firebase project ID (Auto-configured)
REACT_APP_FIREBASE_STORAGE_BUCKET       # Firebase storage bucket
REACT_APP_FIREBASE_MESSAGING_SENDER_ID  # Firebase messaging sender ID
REACT_APP_FIREBASE_APP_ID               # Firebase app ID
```

## 🔐 **Secret Manager Configuration**

All sensitive variables are stored in Google Secret Manager:

### **Required Secrets (Must Configure)**
```bash
google-api-key              # Your Google Gemini API key
firebase-api-key            # Your Firebase API key
firebase-auth-domain        # Your Firebase auth domain
firebase-storage-bucket     # Your Firebase storage bucket
firebase-messaging-sender-id # Your Firebase messaging sender ID
firebase-app-id             # Your Firebase app ID
```

### **Optional Secrets (For Integrations)**
```bash
jira-url                    # Jira instance URL
jira-username               # Jira username
jira-api-token              # Jira API token
azure-devops-url            # Azure DevOps URL
azure-devops-project        # Azure DevOps project
azure-devops-pat            # Azure DevOps PAT
polarion-url                # Polarion URL
polarion-username           # Polarion username
polarion-password           # Polarion password
polarion-project-id         # Polarion project ID
gdpr-secret-key             # GDPR encryption key
public-api-key              # Public API key
agent-api-key               # Agent API key
```

## 📝 **How to Configure Secrets**

### **1. Run Setup Script**
The setup script creates placeholder secrets:
```bash
./scripts/setup-gcp-cicd.sh PROJECT_ID GITHUB_REPO
```

### **2. Update Required Secrets**
```bash
# Google API Key (REQUIRED)
echo "your-actual-google-api-key" | gcloud secrets versions add google-api-key --data-file=-

# Firebase Configuration (REQUIRED for frontend)
echo "your-firebase-api-key" | gcloud secrets versions add firebase-api-key --data-file=-
echo "your-project.firebaseapp.com" | gcloud secrets versions add firebase-auth-domain --data-file=-
echo "your-project.appspot.com" | gcloud secrets versions add firebase-storage-bucket --data-file=-
echo "your-messaging-sender-id" | gcloud secrets versions add firebase-messaging-sender-id --data-file=-
echo "your-firebase-app-id" | gcloud secrets versions add firebase-app-id --data-file=-
```

### **3. Update Optional Integration Secrets (As Needed)**
```bash
# Jira Integration
echo "https://your-domain.atlassian.net" | gcloud secrets versions add jira-url --data-file=-
echo "your-email@company.com" | gcloud secrets versions add jira-username --data-file=-
echo "your-jira-api-token" | gcloud secrets versions add jira-api-token --data-file=-

# Azure DevOps Integration
echo "https://dev.azure.com/your-org" | gcloud secrets versions add azure-devops-url --data-file=-
echo "your-project-name" | gcloud secrets versions add azure-devops-project --data-file=-
echo "your-azure-pat" | gcloud secrets versions add azure-devops-pat --data-file=-

# Polarion Integration
echo "https://your-polarion-instance.com" | gcloud secrets versions add polarion-url --data-file=-
echo "your-polarion-username" | gcloud secrets versions add polarion-username --data-file=-
echo "your-polarion-password" | gcloud secrets versions add polarion-password --data-file=-
echo "your-project-id" | gcloud secrets versions add polarion-project-id --data-file=-
```

## 🚀 **How Variables Are Injected**

### **Backend Deployment**
- **GitHub Actions**: Retrieves secrets from Secret Manager and passes as environment variables
- **Cloud Run**: Receives variables via `--set-env-vars` and `--update-secrets`
- **Local Development**: Uses `.env` file (not committed to git)

### **Frontend Deployment**
- **Build Time**: Environment variables are baked into the React build
- **GitHub Actions**: Retrieves Firebase config from Secret Manager
- **Cloud Build**: Gets configuration and builds with proper environment variables

## 🔍 **Variable Validation**

### **Check Current Secret Values**
```bash
# List all secrets
gcloud secrets list

# Check specific secret (will show if it exists)
gcloud secrets describe google-api-key

# View secret value (be careful - this exposes the secret)
gcloud secrets versions access latest --secret="google-api-key"
```

### **Test Configuration**
```bash
# Run the deployment test script
./scripts/test-deployment.sh PROJECT_ID GITHUB_REPO
```

## 🛡️ **Security Best Practices**

### **✅ Do:**
- Store all sensitive data in Google Secret Manager
- Use placeholder values during setup, replace with real values
- Rotate secrets regularly
- Use least-privilege access for service accounts
- Monitor secret access in Cloud Logging

### **❌ Don't:**
- Commit `.env` files to git
- Hardcode secrets in code
- Share secrets in plain text
- Use production secrets in development
- Store secrets in GitHub repository secrets (use Secret Manager instead)

## 🔧 **Troubleshooting**

### **Common Issues:**

1. **Missing Firebase Config**
   ```bash
   # Check if Firebase secrets exist
   gcloud secrets list | grep firebase
   ```

2. **Backend Can't Access Secrets**
   ```bash
   # Check service account permissions
   gcloud projects get-iam-policy PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:github-actions-sa@*"
   ```

3. **Frontend Build Fails**
   ```bash
   # Check if backend URL is accessible
   curl -f https://your-backend-url/health
   ```

4. **Integration Errors**
   ```bash
   # Check integration-specific secrets
   gcloud secrets versions access latest --secret="jira-api-token"
   ```

## 📊 **Environment Variable Matrix**

| Variable | Required | Source | Used By | Notes |
|----------|----------|--------|---------|-------|
| `GOOGLE_API_KEY` | ✅ | Secret Manager | Backend | Core functionality |
| `REACT_APP_BACKEND_URL` | ✅ | Auto-generated | Frontend | API communication |
| `REACT_APP_FIREBASE_*` | ✅ | Secret Manager | Frontend | Authentication & data |
| `JIRA_*` | ❌ | Secret Manager | Backend | Jira integration |
| `AZURE_DEVOPS_*` | ❌ | Secret Manager | Backend | Azure DevOps integration |
| `POLARION_*` | ❌ | Secret Manager | Backend | Polarion integration |
| `GDPR_*` | ❌ | Secret Manager | Backend | GDPR compliance |
| `*_API_KEY` | ❌ | Secret Manager | Backend | API access control |

This comprehensive configuration ensures your application has all necessary environment variables properly managed and securely stored! 🎯
