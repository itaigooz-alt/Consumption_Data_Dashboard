#!/bin/bash
# Manual Deployment Script - Builds image and deploys separately
# This avoids the Cloud Build permission issue

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Consumption Dashboard - Manual GCP Deployment"
echo "==========================================${NC}"
echo ""

PROJECT_ID="yotam-395120"
SERVICE_NAME="consumption-dashboard"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI not found${NC}"
    exit 1
fi

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Please authenticate first:${NC}"
    echo "  gcloud auth login"
    exit 1
fi

# Set project
gcloud config set project ${PROJECT_ID} --quiet
echo -e "${GREEN}✅ Project: ${PROJECT_ID}${NC}"
echo ""

# Step 1: Build and push using Cloud Build (without deploy step)
echo "Step 1: Building Docker image with Cloud Build..."
echo "This will build and push the image, but not deploy."
echo ""

# Create a temporary cloudbuild file without the deploy step
cat > /tmp/cloudbuild-build-only.yaml << EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '${IMAGE_NAME}:latest'
      - '.'
    id: 'build-image'

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${IMAGE_NAME}:latest'
    id: 'push-image'

images:
  - '${IMAGE_NAME}:latest'

timeout: '1200s'
EOF

gcloud builds submit --config /tmp/cloudbuild-build-only.yaml --project=${PROJECT_ID}

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed${NC}"
    rm /tmp/cloudbuild-build-only.yaml
    exit 1
fi

echo -e "${GREEN}✅ Image built and pushed successfully!${NC}"
echo ""

# Step 2: Deploy manually
echo "Step 2: Deploying to Cloud Run..."
echo ""

gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --set-env-vars GCP_PROJECT_ID=${PROJECT_ID},BQ_DATASET_ID=peerplay \
    --project ${PROJECT_ID}

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Deployment failed${NC}"
    rm /tmp/cloudbuild-build-only.yaml
    exit 1
fi

# Cleanup
rm /tmp/cloudbuild-build-only.yaml

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --format 'value(status.url)' 2>/dev/null)

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Deployment completed successfully!"
echo "==========================================${NC}"
echo ""

if [ -n "$SERVICE_URL" ]; then
    echo -e "${BLUE}Your dashboard is available at:${NC}"
    echo -e "${GREEN}${SERVICE_URL}${NC}"
    echo ""
fi

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure secrets in Cloud Run console"
echo "2. Update OAuth redirect URI to: ${SERVICE_URL}"
echo "See DEPLOY_NOW.md for details."

