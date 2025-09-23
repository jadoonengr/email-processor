#!/bin/bash
# setup_cloud_build.sh - Script to set up Cloud Build triggers and permissions

set -e

# Configuration
PROJECT_ID="alpine-comfort-470817-s8"
REGION="us-central1"
REPO_OWNER="jadoonengr"
REPO_NAME="email-processor"
SERVICE_ACCOUNT_EMAIL="email-notifier-dev-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Setting up Cloud Build for Gmail Processor project..."

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Grant Cloud Build service account necessary roles
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

echo "Granting permissions to Cloud Build service account: $CLOUD_BUILD_SA"

# Grant roles to Cloud Build service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/cloudfunctions.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/pubsub.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/iam.serviceAccountUser"

# Allow Cloud Build to impersonate the application service account
gcloud iam service-accounts add-iam-policy-binding \
    $SERVICE_ACCOUNT_EMAIL \
    --member="serviceAccount:$CLOUD_BUILD_SA" \
    --role="roles/iam.serviceAccountTokenCreator"

# Create build triggers
echo "Creating Cloud Build triggers..."

# Production trigger (main branch)
gcloud builds triggers create github \
    --repo-name=$REPO_NAME \
    --repo-owner=$REPO_OWNER \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml \
    --description="Production deployment trigger" \
    --name="gmail-processor-prod" || echo "Production trigger might already exist"

# Development trigger (develop branch)
gcloud builds triggers create github \
    --repo-name=$REPO_NAME \
    --repo-owner=$REPO_OWNER \
    --branch-pattern="^develop$" \
    --build-config=cloudbuild-dev.yaml \
    --description="Development deployment trigger" \
    --name="gmail-processor-dev" || echo "Development trigger might already exist"

# Pull request trigger (testing)
gcloud builds triggers create github \
    --repo-name=$REPO_NAME \
    --repo-owner=$REPO_OWNER \
    --pull-request-pattern="^main$" \
    --build-config=cloudbuild-test.yaml \
    --comment-control=COMMENTS_ENABLED \
    --description="Pull request testing trigger" \
    --name="gmail-processor-pr" || echo "PR trigger might already exist"

echo "Cloud Build setup completed!"
echo ""
echo "Next steps:"
echo "1. Connect your GitHub repository to Cloud Build in the Google Cloud Console"
echo "2. Update REPO_OWNER and REPO_NAME variables in this script"
echo "3. Push your code to trigger the first build"
echo "4. Check build status: gcloud builds list"