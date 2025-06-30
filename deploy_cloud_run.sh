#!/bin/bash

# ------------------------------
# Cloud Run Deploy Script for PDF Automation App
# ------------------------------

# Set your GCP project
PROJECT_ID="turing-gpt"
REGION="us-central1"
REPO_NAME="pdf-app-repo"
IMAGE_NAME="pdf-automations-app"
FULL_IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME"
SERVICE_NAME="pdf-automations-app"

echo "🔧 Setting GCP project: $PROJECT_ID"
gcloud config set project $PROJECT_ID

echo "📦 Creating Artifact Registry repo (if not exists): $REPO_NAME"
gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION || echo "ℹ️ Repo may already exist – continuing..."

echo "🚀 Submitting Cloud Build to build & push Docker image to Artifact Registry..."
gcloud builds submit --tag $FULL_IMAGE

echo "🌐 Deploying to Cloud Run: $SERVICE_NAME"
gcloud run deploy $SERVICE_NAME \
  --image $FULL_IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated

echo "✅ Deployment finished! 🎉"
echo "👉 Visit your app: check the 'Service URL' output above"
