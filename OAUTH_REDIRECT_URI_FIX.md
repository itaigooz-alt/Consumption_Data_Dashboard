# Fix OAuth Redirect URI Mismatch Error

## Error: `Error 400: redirect_uri_mismatch`

This error occurs when the redirect URI in your Google OAuth client doesn't match the redirect URI your application is using.

## Quick Fix Steps

### Step 1: Find Your Streamlit Cloud URL

1. Go to https://share.streamlit.io
2. Open your Consumption Dashboard app
3. Copy the **exact URL** (e.g., `https://consumption-dashboard.streamlit.app/`)
   - **Important**: Include the trailing slash `/`
   - **Important**: Use the exact URL shown in Streamlit Cloud

### Step 2: Update Google OAuth Client

1. **Go to Google Cloud Console**:
   - Visit: https://console.cloud.google.com/apis/credentials
   - Select your project

2. **Find Your OAuth Client**:
   - Look for "OAuth 2.0 Client IDs"
   - Click on the client ID you created for the Consumption Dashboard

3. **Update Authorized Redirect URIs**:
   - In the "Authorized redirect URIs" section, add or update:
     - `https://your-actual-streamlit-url.streamlit.app/`
     - Replace `your-actual-streamlit-url` with your actual Streamlit Cloud app name
   - **Important**: 
     - Must include trailing slash `/`
     - Must match exactly (case-sensitive)
     - No extra spaces or characters

4. **Save Changes**:
   - Click "**SAVE**" at the bottom

### Step 3: Update Streamlit Cloud Secrets

1. **Go to Streamlit Cloud**:
   - Visit: https://share.streamlit.io
   - Open your app → Settings → Secrets

2. **Update `STREAMLIT_REDIRECT_URI`**:
   - Make sure it matches your actual Streamlit Cloud URL exactly:
   ```toml
   STREAMLIT_REDIRECT_URI = "https://your-actual-streamlit-url.streamlit.app/"
   ```
   - Replace `your-actual-streamlit-url` with your actual app name
   - Include trailing slash `/`

3. **Save Secrets**:
   - Click "**Save**"
   - The app will automatically redeploy

### Step 4: Verify Both Match

**In Google Cloud Console:**
- Authorized redirect URI: `https://consumption-dashboard.streamlit.app/`

**In Streamlit Cloud Secrets:**
- `STREAMLIT_REDIRECT_URI = "https://consumption-dashboard.streamlit.app/"`

**Both must be identical!**

## Common Mistakes

❌ **Wrong**: `https://consumption-dashboard.streamlit.app` (missing trailing slash)
✅ **Correct**: `https://consumption-dashboard.streamlit.app/`

❌ **Wrong**: `https://Consumption-Dashboard.streamlit.app/` (wrong case)
✅ **Correct**: `https://consumption-dashboard.streamlit.app/`

❌ **Wrong**: `https://consumption-dashboard.streamlit.app/ ` (extra space)
✅ **Correct**: `https://consumption-dashboard.streamlit.app/`

## After Fixing

1. **Wait 1-2 minutes** for Google Cloud changes to propagate
2. **Clear browser cache/cookies** for the Streamlit app
3. **Try signing in again**
4. If still not working, try **incognito/private browsing window**

## Still Having Issues?

1. **Check Streamlit Cloud Logs**:
   - In Streamlit Cloud, go to your app
   - Click "Manage app" → "Logs"
   - Look for any error messages

2. **Verify OAuth Client Type**:
   - Make sure you created a **Web application** client (not Desktop or other types)

3. **Check OAuth Consent Screen**:
   - Make sure the consent screen is published (if using External)
   - Or add test users (if using Internal/Testing)

4. **Double-check the URL**:
   - Copy the exact URL from Streamlit Cloud
   - Paste it into both Google Cloud Console and Streamlit Cloud secrets
   - Make sure there are no hidden characters

---

**Last Updated**: January 2025

