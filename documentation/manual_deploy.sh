#!/bin/bash
# manual_deploy.sh - Manual deployment script (alternative to Cloud Build)

set -e

PROJECT_ID="alpine-comfort-470817-s8"
REGION="us-central1"
SERVICE_ACCOUNT_EMAIL="email-notifier-dev-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Manual deployment of Gmail Processor..."

# Set project
gcloud config set project $PROJECT_ID

# Run tests locally
echo "Running tests..."
python -m pytest tests/ -v

# Deploy using gcloud builds submit (local build)
echo "Starting Cloud Build..."
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions=_REGION=$REGION,_SERVICE_ACCOUNT_EMAIL=$SERVICE_ACCOUNT_EMAIL \
    .

echo "Deployment completed!"
