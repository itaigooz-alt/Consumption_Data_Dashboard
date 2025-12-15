# Consumption Dashboard Deployment Guide

Based on [PeerPlayGames dashboard_deployment_template](https://github.com/PeerPlayGames/dashboard_deployment_template)

## Quick Deploy

Run the deployment script to verify everything is ready:

```bash
./deployment_script.sh
```

## Deployment Options

### Option 1: Streamlit Cloud (Recommended)

**Best for**: Streamlit dashboards with automatic deployments

#### Steps:

1. **Go to Streamlit Cloud**:
   - Visit: https://share.streamlit.io
   - Sign in with your GitHub account

2. **Create New App**:
   - Click "**New app**"
   - Repository: `itaigooz-alt/Consumption_Data_Dashboard`
   - Branch: `main`
   - Main file path: `consumption_dashboard.py`
   - App URL: `consumption-dashboard` (or your preferred name)

3. **Configure Secrets** (in Streamlit Cloud Settings → Secrets):
   ```toml
   [GOOGLE_APPLICATION_CREDENTIALS_JSON]
   type = "service_account"
   project_id = "yotam-395120"
   private_key_id = "your-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\nYour key\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@yotam-395120.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."

   GOOGLE_OAUTH_CLIENT_ID = "your-oauth-client-id.apps.googleusercontent.com"
   GOOGLE_OAUTH_CLIENT_SECRET = "your-oauth-client-secret"
   STREAMLIT_REDIRECT_URI = "https://consumption-dashboard.streamlit.app/"
   ```

4. **Deploy**:
   - Click "**Deploy!**"
   - Wait 2-3 minutes for build to complete

5. **Update OAuth Redirect URI**:
   - After deployment, note your exact Streamlit Cloud URL
   - Go to Google Cloud Console → Credentials
   - Edit your OAuth 2.0 Client ID
   - Add the Streamlit Cloud URL to "Authorized redirect URIs"
   - Format: `https://your-app-name.streamlit.app/` (with trailing slash)

#### Benefits:
- ✅ Native Streamlit support
- ✅ Automatic deployments from GitHub
- ✅ Free tier available
- ✅ Built-in authentication handling
- ✅ No server management needed

---

### Option 2: Manual GitHub Push

If you need to push changes manually:

```bash
# Check status
git status

# Add all changes
git add .

# Commit
git commit -m "Deploy consumption dashboard"

# Push to GitHub
git push origin main
```

Streamlit Cloud will automatically detect the push and redeploy.

---

## Required Files

The deployment script verifies these files exist:

- ✅ `consumption_dashboard.py` - Main dashboard file
- ✅ `requirements.txt` - Python dependencies
- ✅ `runtime.txt` - Python version (3.11)
- ✅ `.streamlit/config.toml` - Streamlit configuration

## Pre-Deployment Checklist

- [ ] Code is committed to Git
- [ ] Pushed to GitHub repository
- [ ] `requirements.txt` includes all dependencies
- [ ] `runtime.txt` specifies Python version
- [ ] `.streamlit/config.toml` is configured
- [ ] Google OAuth credentials are created
- [ ] Service account JSON key is ready
- [ ] BigQuery table `fact_consumption_daily_dashboard` exists and has data

## Post-Deployment

1. **Verify Dashboard Loads**:
   - Visit your Streamlit Cloud URL
   - Check that authentication works
   - Verify data loads from BigQuery

2. **Test Features**:
   - Test all filters
   - Test dimension selectors
   - Verify all views render correctly
   - Check date range selection

3. **Monitor**:
   - Check Streamlit Cloud logs for errors
   - Monitor BigQuery query costs
   - Verify authentication is working

## Troubleshooting

### Dashboard Not Loading
- Check Streamlit Cloud logs
- Verify `requirements.txt` has all dependencies
- Ensure Python version matches `runtime.txt`

### Authentication Errors
- Verify OAuth redirect URI matches exactly
- Check OAuth consent screen is configured
- Ensure service account has BigQuery permissions

### BigQuery Connection Errors
- Verify service account JSON is correctly formatted
- Check service account has proper BigQuery roles
- Ensure table `fact_consumption_daily_dashboard` exists

### Data Not Showing
- Verify table has data for the selected date range
- Check BigQuery query logs
- Verify table name is correct in code

---

## Support

For deployment issues:
1. Check Streamlit Cloud deployment logs
2. Review Google Cloud Console for authentication errors
3. Verify all secrets are correctly formatted
4. Run `./deployment_script.sh` to verify setup

---

**Last Updated**: January 2025  
**Template**: [PeerPlayGames/dashboard_deployment_template](https://github.com/PeerPlayGames/dashboard_deployment_template)

