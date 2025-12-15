#!/bin/bash
# GCP Cloud Run Deployment Script for Consumption Dashboard
# Based on PeerPlayGames dashboard_deployment_template

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "Consumption Dashboard - GCP Cloud Run Deployment"
echo "==========================================${NC}"
echo ""

# Configuration
PROJECT_ID="yotam-395120"
SERVICE_NAME="consumption-dashboard"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI not found${NC}"
    echo "Please install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${GREEN}✅ gcloud CLI found${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Error: Docker not found${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✅ Docker found${NC}"
echo ""

# Step 1: Set the project
echo "Step 1: Setting GCP project..."
gcloud config set project ${PROJECT_ID}
echo -e "${GREEN}✅ Project set to ${PROJECT_ID}${NC}"
echo ""

# Step 2: Enable required APIs
echo "Step 2: Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    --project=${PROJECT_ID} 2>/dev/null || echo -e "${YELLOW}⚠️  APIs may already be enabled${NC}"
echo -e "${GREEN}✅ APIs enabled${NC}"
echo ""

# Step 3: Build the Docker image
echo "Step 3: Building Docker image..."
echo "This may take a few minutes..."
docker build -t ${IMAGE_NAME}:latest .
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker image built successfully${NC}"
echo ""

# Step 4: Push the image to Container Registry
echo "Step 4: Pushing image to Container Registry..."
gcloud auth configure-docker --quiet
docker push ${IMAGE_NAME}:latest
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker push failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Image pushed to Container Registry${NC}"
echo ""

# Step 5: Deploy to Cloud Run
echo "Step 5: Deploying to Cloud Run..."
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
    echo -e "${RED}❌ Cloud Run deployment failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Deployment completed successfully!"
echo "==========================================${NC}"
echo ""

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --format 'value(status.url)')

echo -e "${BLUE}Your dashboard is available at:${NC}"
echo -e "${GREEN}${SERVICE_URL}${NC}"
echo ""

echo -e "${YELLOW}⚠️  Important: Configure secrets in Cloud Run${NC}"
echo "1. Go to Cloud Run console: https://console.cloud.google.com/run"
echo "2. Select service: ${SERVICE_NAME}"
echo "3. Click 'Edit & Deploy New Revision'"
echo "4. Go to 'Variables & Secrets' tab"
echo "5. Add the following secrets:"
echo "   - GOOGLE_APPLICATION_CREDENTIALS_JSON (service account JSON)"
echo "   - GOOGLE_OAUTH_CLIENT_ID"
echo "   - GOOGLE_OAUTH_CLIENT_SECRET"
echo "   - STREAMLIT_REDIRECT_URI (set to: ${SERVICE_URL})"
echo ""

