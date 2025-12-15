# Consumption Dashboard Deployment Guide

Based on [PeerPlayGames dashboard_deployment_template](https://github.com/PeerPlayGames/dashboard_deployment_template)

## Quick Deploy to GCP Cloud Run

Run the deployment script:

```bash
./deploy.sh
```

This script will:
1. Build the Docker image
2. Push to Google Container Registry
3. Deploy to Cloud Run
4. Provide you with the dashboard URL

---

## Prerequisites

1. **Google Cloud SDK (gcloud CLI)**:
   ```bash
   # Install: https://cloud.google.com/sdk/docs/install
   gcloud --version
   ```

2. **Docker**:
   ```bash
   # Install: https://docs.docker.com/get-docker/
   docker --version
   ```

3. **Authentication**:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project yotam-395120
   ```

4. **Required APIs Enabled**:
   - Cloud Build API
   - Cloud Run API
   - Container Registry API

   The `deploy.sh` script will enable these automatically.

---

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

Use the provided deployment script:

```bash
cd /Users/itaigooz/Consumption
./deploy.sh
```

The script will:
- ✅ Verify prerequisites (gcloud, Docker)
- ✅ Set GCP project
- ✅ Enable required APIs
- ✅ Build Docker image
- ✅ Push to Container Registry
- ✅ Deploy to Cloud Run
- ✅ Provide the service URL

### Option 2: Manual Deployment

#### Step 1: Build Docker Image

```bash
docker build -t gcr.io/yotam-395120/consumption-dashboard:latest .
```

#### Step 2: Push to Container Registry

```bash
gcloud auth configure-docker
docker push gcr.io/yotam-395120/consumption-dashboard:latest
```

#### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy consumption-dashboard \
    --image gcr.io/yotam-395120/consumption-dashboard:latest \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --set-env-vars GCP_PROJECT_ID=yotam-395120,BQ_DATASET_ID=peerplay \
    --project yotam-395120
```

### Option 3: Cloud Build (CI/CD)

For automated deployments from GitHub:

1. **Connect Repository to Cloud Build**:
   - Go to: https://console.cloud.google.com/cloud-build/triggers
   - Click "Create Trigger"
   - Connect your GitHub repository
   - Select branch: `main`
   - Build configuration: `cloudbuild.yaml`

2. **Deploy on Push**:
   - Every push to `main` will trigger a build
   - Cloud Build will use `cloudbuild.yaml` to build and deploy

---

## Configure Secrets in Cloud Run

After initial deployment, configure secrets:

1. **Go to Cloud Run Console**:
   - Visit: https://console.cloud.google.com/run
   - Select service: `consumption-dashboard`
   - Click "Edit & Deploy New Revision"

2. **Add Environment Variables/Secrets**:
   - Go to "Variables & Secrets" tab
   - Add the following:

   **Environment Variables**:
   - `GCP_PROJECT_ID` = `yotam-395120`
   - `BQ_DATASET_ID` = `peerplay`

   **Secrets** (create secrets first in Secret Manager):
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON` - Service account JSON
   - `GOOGLE_OAUTH_CLIENT_ID` - OAuth client ID
   - `GOOGLE_OAUTH_CLIENT_SECRET` - OAuth client secret
   - `STREAMLIT_REDIRECT_URI` - Your Cloud Run service URL

3. **Create Secrets in Secret Manager**:
   ```bash
   # Service account JSON
   echo '{"type":"service_account",...}' | gcloud secrets create google-application-credentials-json \
       --data-file=- \
       --project=yotam-395120

   # OAuth Client ID
   echo 'your-client-id.apps.googleusercontent.com' | gcloud secrets create google-oauth-client-id \
       --data-file=- \
       --project=yotam-395120

   # OAuth Client Secret
   echo 'your-client-secret' | gcloud secrets create google-oauth-client-secret \
       --data-file=- \
       --project=yotam-395120

   # Redirect URI (update after deployment)
   echo 'https://consumption-dashboard-xxxxx-uc.a.run.app/' | gcloud secrets create streamlit-redirect-uri \
       --data-file=- \
       --project=yotam-395120
   ```

4. **Grant Cloud Run Access to Secrets**:
   ```bash
   gcloud secrets add-iam-policy-binding google-application-credentials-json \
       --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor" \
       --project=yotam-395120
   ```

5. **Reference Secrets in Cloud Run**:
   - In Cloud Run service settings, add secrets as environment variables
   - Format: `SECRET_NAME=projects/PROJECT_ID/secrets/SECRET_NAME/versions/latest`

---

## Update OAuth Redirect URI

After deployment, update Google OAuth settings:

1. **Get Your Cloud Run URL**:
   ```bash
   gcloud run services describe consumption-dashboard \
       --region us-central1 \
       --format 'value(status.url)'
   ```

2. **Update OAuth Credentials**:
   - Go to: https://console.cloud.google.com/apis/credentials
   - Edit your OAuth 2.0 Client ID
   - Add to "Authorized redirect URIs":
     - `https://your-cloud-run-url.run.app/` (with trailing slash)

---

## Required Files

The deployment uses these files:

- ✅ `Dockerfile` - Container image definition
- ✅ `cloudbuild.yaml` - Cloud Build configuration
- ✅ `.gcloudignore` - Files to exclude from deployment
- ✅ `consumption_dashboard.py` - Main dashboard file
- ✅ `requirements.txt` - Python dependencies
- ✅ `.streamlit/config.toml` - Streamlit configuration
- ✅ `deploy.sh` - Deployment automation script

---

## Pre-Deployment Checklist

- [ ] gcloud CLI installed and authenticated
- [ ] Docker installed and running
- [ ] Code is committed to Git
- [ ] Pushed to GitHub repository
- [ ] `requirements.txt` includes all dependencies
- [ ] Service account created with BigQuery permissions
- [ ] OAuth credentials created
- [ ] BigQuery table `fact_consumption_daily_dashboard` exists and has data

---

## Post-Deployment

1. **Verify Dashboard Loads**:
   - Visit your Cloud Run URL
   - Check that authentication works
   - Verify data loads from BigQuery

2. **Test Features**:
   - Test all filters
   - Test dimension selectors
   - Verify all views render correctly
   - Check date range selection

3. **Monitor**:
   - Check Cloud Run logs: `gcloud run services logs read consumption-dashboard --region us-central1`
   - Monitor BigQuery query costs
   - Verify authentication is working
   - Check Cloud Run metrics in console

---

## Troubleshooting

### Build Fails
- Check Dockerfile syntax
- Verify all files exist (requirements.txt, etc.)
- Check Cloud Build logs

### Deployment Fails
- Verify gcloud authentication
- Check Cloud Run API is enabled
- Ensure Container Registry API is enabled
- Check service account permissions

### Dashboard Not Loading
- Check Cloud Run logs
- Verify environment variables are set
- Ensure secrets are correctly configured
- Verify BigQuery table exists

### Authentication Errors
- Verify OAuth redirect URI matches Cloud Run URL exactly
- Check OAuth consent screen is configured
- Ensure service account has BigQuery permissions
- Verify secrets are correctly formatted

### BigQuery Connection Errors
- Verify service account JSON is correctly formatted
- Check service account has proper BigQuery roles:
  - `BigQuery Data Viewer`
  - `BigQuery Job User`
- Ensure table `fact_consumption_daily_dashboard` exists

### Data Not Showing
- Verify table has data for the selected date range
- Check BigQuery query logs
- Verify table name is correct in code
- Check date filters are working

---

## Scaling Configuration

Default Cloud Run settings:
- **Memory**: 2Gi
- **CPU**: 2
- **Min Instances**: 0 (scales to zero)
- **Max Instances**: 10
- **Timeout**: 300 seconds

To update:
```bash
gcloud run services update consumption-dashboard \
    --memory 4Gi \
    --cpu 4 \
    --max-instances 20 \
    --region us-central1
```

---

## Cost Optimization

- **Min instances = 0**: Service scales to zero when not in use
- **Max instances**: Limit to control costs
- **Memory/CPU**: Adjust based on usage
- **BigQuery**: Use query caching, limit date ranges

---

## Support

For deployment issues:
1. Check Cloud Run logs: `gcloud run services logs read consumption-dashboard --region us-central1`
2. Review Cloud Build logs in console
3. Verify all secrets are correctly formatted
4. Run `./deploy.sh` to verify setup
5. Check Google Cloud Console for errors

---

**Last Updated**: January 2025  
**Template**: [PeerPlayGames/dashboard_deployment_template](https://github.com/PeerPlayGames/dashboard_deployment_template)
