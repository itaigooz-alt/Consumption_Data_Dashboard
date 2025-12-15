# Deploy Consumption Dashboard to GCP Cloud Run

## Step 1: Authenticate with Google Cloud

Run these commands to authenticate:

```bash
# Login to Google Cloud
gcloud auth login

# Set up application default credentials
gcloud auth application-default login

# Verify project is set
gcloud config set project yotam-395120
```

## Step 2: Deploy Using Cloud Build (No Docker Required)

Since Docker is not installed locally, we'll use Cloud Build which builds in the cloud:

```bash
cd /Users/itaigooz/Consumption

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com --project=yotam-395120

# Submit build to Cloud Build (this will build and deploy)
gcloud builds submit --config cloudbuild.yaml --project=yotam-395120
```

This will:
1. Upload your code to Cloud Build
2. Build the Docker image in the cloud
3. Push to Container Registry
4. Deploy to Cloud Run
5. Provide you with the service URL

## Step 3: Get Your Service URL

After deployment completes, get your service URL:

```bash
gcloud run services describe consumption-dashboard \
    --region us-central1 \
    --project yotam-395120 \
    --format 'value(status.url)'
```

## Step 4: Configure Secrets

After deployment, you need to configure secrets in Cloud Run:

1. **Go to Cloud Run Console**:
   - Visit: https://console.cloud.google.com/run?project=yotam-395120
   - Click on service: `consumption-dashboard`

2. **Edit Service**:
   - Click "Edit & Deploy New Revision"
   - Go to "Variables & Secrets" tab

3. **Add Environment Variables**:
   - `GCP_PROJECT_ID` = `yotam-395120`
   - `BQ_DATASET_ID` = `peerplay`

4. **Create and Add Secrets** (in Secret Manager first):

   ```bash
   # Create secrets in Secret Manager
   # Replace with your actual values
   
   # Service Account JSON
   gcloud secrets create google-application-credentials-json \
       --data-file=/path/to/service-account.json \
       --project=yotam-395120
   
   # OAuth Client ID
   echo -n 'your-oauth-client-id.apps.googleusercontent.com' | \
       gcloud secrets create google-oauth-client-id \
       --data-file=- \
       --project=yotam-395120
   
   # OAuth Client Secret
   echo -n 'your-oauth-client-secret' | \
       gcloud secrets create google-oauth-client-secret \
       --data-file=- \
       --project=yotam-395120
   
   # Redirect URI (update with your actual Cloud Run URL)
   echo -n 'https://consumption-dashboard-xxxxx-uc.a.run.app/' | \
       gcloud secrets create streamlit-redirect-uri \
       --data-file=- \
       --project=yotam-395120
   ```

5. **Grant Cloud Run Access to Secrets**:
   ```bash
   # Get the Cloud Run service account
   PROJECT_NUMBER=$(gcloud projects describe yotam-395120 --format='value(projectNumber)')
   
   # Grant access to each secret
   gcloud secrets add-iam-policy-binding google-application-credentials-json \
       --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor" \
       --project=yotam-395120
   
   gcloud secrets add-iam-policy-binding google-oauth-client-id \
       --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor" \
       --project=yotam-395120
   
   gcloud secrets add-iam-policy-binding google-oauth-client-secret \
       --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor" \
       --project=yotam-395120
   
   gcloud secrets add-iam-policy-binding streamlit-redirect-uri \
       --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor" \
       --project=yotam-395120
   ```

6. **Reference Secrets in Cloud Run**:
   - In Cloud Run service settings → Variables & Secrets
   - Add environment variables that reference secrets:
     - `GOOGLE_APPLICATION_CREDENTIALS_JSON` = `projects/yotam-395120/secrets/google-application-credentials-json/versions/latest`
     - `GOOGLE_OAUTH_CLIENT_ID` = `projects/yotam-395120/secrets/google-oauth-client-id/versions/latest`
     - `GOOGLE_OAUTH_CLIENT_SECRET` = `projects/yotam-395120/secrets/google-oauth-client-secret/versions/latest`
     - `STREAMLIT_REDIRECT_URI` = `projects/yotam-395120/secrets/streamlit-redirect-uri/versions/latest`

## Step 5: Update OAuth Redirect URI

After you have your Cloud Run URL, update Google OAuth settings:

1. Go to: https://console.cloud.google.com/apis/credentials?project=yotam-395120
2. Edit your OAuth 2.0 Client ID
3. Add to "Authorized redirect URIs":
   - `https://your-cloud-run-url.run.app/` (with trailing slash)

## Troubleshooting

### Build Fails
- Check Cloud Build logs: https://console.cloud.google.com/cloud-build/builds?project=yotam-395120
- Verify all files are in the repository
- Check cloudbuild.yaml syntax

### Service Not Accessible
- Verify service is deployed: `gcloud run services list --project=yotam-395120`
- Check service logs: `gcloud run services logs read consumption-dashboard --region us-central1`

### Authentication Errors
- Verify secrets are correctly configured
- Check service account has BigQuery permissions
- Verify OAuth redirect URI matches exactly

