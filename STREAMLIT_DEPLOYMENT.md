# Streamlit Cloud Deployment Guide for Consumption Dashboard

## Prerequisites

1. **GitHub Repository**: Ensure your code is pushed to GitHub
   - Repository: `https://github.com/itaigooz-alt/Consumption_Data_Dashboard`

2. **Google Cloud Project**: Access to the Google Cloud project with BigQuery

3. **Google OAuth Credentials**: OAuth 2.0 Client ID and Secret

---

## Step 1: Create Google OAuth Credentials

1. **Go to Google Cloud Console**:
   - Visit: https://console.cloud.google.com/apis/credentials
   - Select your project (or create a new one)

2. **Configure OAuth Consent Screen** (if not already done):
   - Click "OAuth consent screen" in the left menu
   - User Type: **Internal** (for company use) or **External**
   - App name: "Consumption Dashboard"
   - User support email: Your email
   - Developer contact: Your email
   - Click "**SAVE AND CONTINUE**"
   - Scopes: Add `email` and `profile`
   - Click "**SAVE AND CONTINUE**"
   - Test users: Add Peerplay employee emails (if using External)
   - Click "**SAVE AND CONTINUE**"

3. **Create OAuth Client ID**:
   - Go back to "Credentials" page
   - Click "**+ CREATE CREDENTIALS**"
   - Select "**OAuth client ID**"
   - Application type: **Web application**
   - Name: "Consumption Dashboard"
   - **Authorized redirect URIs**: 
     - Add: `https://consumption-dashboard.streamlit.app/`
     - **Important**: Use the exact URL from Streamlit Cloud (check after deployment)
     - Format: `https://your-app-name.streamlit.app/` (with trailing slash `/`)
   - Click "**CREATE**"
   
4. **Copy Credentials**:
   - Copy the **Client ID** (ends with `.apps.googleusercontent.com`)
   - Copy the **Client Secret**
   - Keep these secure!

---

## Step 2: Create Service Account for BigQuery

1. **Go to IAM & Admin → Service Accounts**:
   - Visit: https://console.cloud.google.com/iam-admin/serviceaccounts

2. **Create Service Account**:
   - Click "**+ CREATE SERVICE ACCOUNT**"
   - Service account name: `consumption-dashboard-sa`
   - Click "**CREATE AND CONTINUE**"
   - Grant role: **BigQuery Data Viewer** and **BigQuery Job User**
   - Click "**CONTINUE**" → "**DONE**"

3. **Create JSON Key**:
   - Click on the service account
   - Go to "**KEYS**" tab
   - Click "**ADD KEY**" → "**Create new key**"
   - Select "**JSON**"
   - Click "**CREATE**"
   - Save the JSON file securely

---

## Step 3: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**:
   - Visit: https://share.streamlit.io
   - Sign in with your GitHub account

2. **Create New App**:
   - Click "**New app**"
   - Connect your GitHub account (if not already connected)
   - Select repository: `itaigooz-alt/Consumption_Data_Dashboard`
   - Branch: `main`
   - Main file path: `consumption_dashboard.py`
   - App URL: Choose a name (e.g., `consumption-dashboard`)
   - Click "**Deploy!**"

3. **Wait for Initial Deployment**:
   - The app will deploy (may take a few minutes)
   - Note the exact URL (e.g., `https://consumption-dashboard.streamlit.app/`)

---

## Step 4: Configure Streamlit Cloud Secrets

1. **Open App Settings**:
   - In Streamlit Cloud, click on your app
   - Click "**⚙️ Settings**" (top right)
   - Go to "**Secrets**" tab

2. **Add Secrets** (in TOML format):

```toml
[GOOGLE_APPLICATION_CREDENTIALS_JSON]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYour private key here\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"

GOOGLE_OAUTH_CLIENT_ID = "your-oauth-client-id.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET = "your-oauth-client-secret"
STREAMLIT_REDIRECT_URI = "https://consumption-dashboard.streamlit.app/"
```

**Important Notes**:
- Replace all placeholder values with your actual credentials
- The `private_key` should include `\n` for newlines (as shown)
- The `STREAMLIT_REDIRECT_URI` must match your Streamlit Cloud app URL exactly
- Make sure the redirect URI in Google OAuth credentials matches this URL

3. **Update OAuth Redirect URI** (if needed):
   - Go back to Google Cloud Console → Credentials
   - Edit your OAuth 2.0 Client ID
   - Update "Authorized redirect URIs" to match your Streamlit Cloud URL
   - Save changes

4. **Save Secrets**:
   - Click "**Save**" in Streamlit Cloud
   - The app will automatically redeploy

---

## Step 5: Verify Deployment

1. **Access the Dashboard**:
   - Visit your Streamlit Cloud URL
   - You should see the Google OAuth login page

2. **Test Authentication**:
   - Sign in with a Peerplay email (peerplay.com or peerplay.io)
   - You should be redirected back to the dashboard
   - The dashboard should load with data from BigQuery

3. **Check for Errors**:
   - If you see authentication errors, verify:
     - OAuth credentials are correct
     - Redirect URI matches exactly
     - Service account has proper BigQuery permissions
     - Secrets are formatted correctly in TOML

---

## Troubleshooting

### Authentication Not Working
- Verify OAuth redirect URI matches exactly (including trailing slash)
- Check that OAuth consent screen is configured
- Ensure user email domain is in `ALLOWED_DOMAINS` in the code

### BigQuery Connection Errors
- Verify service account JSON is correctly formatted in secrets
- Check service account has BigQuery permissions
- Ensure project ID is correct

### App Not Deploying
- Check GitHub repository is public or Streamlit Cloud has access
- Verify `requirements.txt` includes all dependencies
- Check Streamlit Cloud logs for error messages

---

## Security Notes

- **Never commit secrets to GitHub**
- Keep OAuth credentials and service account keys secure
- Regularly rotate credentials
- Use environment-specific credentials for different deployments

---

## Support

For issues or questions:
1. Check Streamlit Cloud logs
2. Review Google Cloud Console for authentication errors
3. Verify all secrets are correctly formatted

---

**Last Updated**: January 2025

