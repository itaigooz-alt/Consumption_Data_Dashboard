#!/bin/bash
# GCP Cloud Run Deployment Script for Consumption Dashboard
# This script uses Cloud Build (no local Docker required)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Consumption Dashboard - GCP Cloud Run Deployment"
echo "==========================================${NC}"
echo ""

PROJECT_ID="yotam-395120"
SERVICE_NAME="consumption-dashboard"
REGION="us-central1"

# Step 1: Check gcloud
echo "Step 1: Checking gcloud CLI..."
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI not found${NC}"
    echo "Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo -e "${GREEN}✅ gcloud CLI found${NC}"
echo ""

# Step 2: Check authentication
echo "Step 2: Checking authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}⚠️  No active authentication found${NC}"
    echo ""
    echo "Please run these commands to authenticate:"
    echo "  gcloud auth login"
    echo "  gcloud auth application-default login"
    echo "  gcloud config set project ${PROJECT_ID}"
    echo ""
    echo "Then run this script again."
    exit 1
fi
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
echo -e "${GREEN}✅ Authenticated as: ${ACTIVE_ACCOUNT}${NC}"
echo ""

# Step 3: Set project
echo "Step 3: Setting GCP project..."
gcloud config set project ${PROJECT_ID} --quiet
CURRENT_PROJECT=$(gcloud config get-value project)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Error: Could not set project${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Project set to: ${PROJECT_ID}${NC}"
echo ""

# Step 4: Enable APIs
echo "Step 4: Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project=${PROJECT_ID} 2>/dev/null || echo -e "${YELLOW}⚠️  APIs may already be enabled${NC}"
echo -e "${GREEN}✅ APIs enabled${NC}"
echo ""

# Step 5: Verify files exist
echo "Step 5: Verifying deployment files..."
REQUIRED_FILES=("Dockerfile" "cloudbuild.yaml" "consumption_dashboard.py" "requirements.txt")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Error: Required file not found: $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All required files found${NC}"
echo ""

# Step 6: Submit build to Cloud Build
echo "Step 6: Submitting build to Cloud Build..."
echo -e "${YELLOW}This will:${NC}"
echo "  1. Upload code to Cloud Build"
echo "  2. Build Docker image in the cloud"
echo "  3. Push to Container Registry"
echo "  4. Deploy to Cloud Run"
echo ""
echo -e "${YELLOW}This may take 5-10 minutes...${NC}"
echo ""

gcloud builds submit --config cloudbuild.yaml --project=${PROJECT_ID}

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed. Check logs:${NC}"
    echo "https://console.cloud.google.com/cloud-build/builds?project=${PROJECT_ID}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Build and deployment completed!${NC}"
echo ""

# Step 7: Get service URL
echo "Step 7: Getting service URL..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --format 'value(status.url)' 2>/dev/null)

if [ -z "$SERVICE_URL" ]; then
    echo -e "${YELLOW}⚠️  Could not retrieve service URL${NC}"
    echo "Check Cloud Run console: https://console.cloud.google.com/run?project=${PROJECT_ID}"
else
    echo -e "${GREEN}✅ Service deployed!${NC}"
    echo ""
    echo -e "${BLUE}Your dashboard is available at:${NC}"
    echo -e "${GREEN}${SERVICE_URL}${NC}"
    echo ""
fi

# Step 8: Next steps
echo "=========================================="
echo -e "${YELLOW}Next Steps:${NC}"
echo "=========================================="
echo ""
echo "1. Configure secrets in Cloud Run:"
echo "   https://console.cloud.google.com/run?project=${PROJECT_ID}"
echo ""
echo "2. Add environment variables:"
echo "   - GCP_PROJECT_ID = yotam-395120"
echo "   - BQ_DATASET_ID = peerplay"
echo ""
echo "3. Create secrets in Secret Manager and reference them in Cloud Run:"
echo "   - GOOGLE_APPLICATION_CREDENTIALS_JSON"
echo "   - GOOGLE_OAUTH_CLIENT_ID"
echo "   - GOOGLE_OAUTH_CLIENT_SECRET"
echo "   - STREAMLIT_REDIRECT_URI (set to: ${SERVICE_URL})"
echo ""
echo "4. Update OAuth redirect URI in Google Cloud Console:"
echo "   https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}"
echo "   Add: ${SERVICE_URL}"
echo ""
echo "See DEPLOY_NOW.md for detailed instructions."
echo ""

