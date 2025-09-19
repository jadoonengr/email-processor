
# Step 1: Enable GCP Services
# =====================================================
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable gmail.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable artifactregistry.googleapis.com


# Step 2: Create Project
# =====================================================
PROJECT_ID="email-management-system-fd34"
gcloud projects create PROJECT_ID
gcloud config set project $PROJECT_ID
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Step 3: Create Big Query Table
# =====================================================

# Set your variables
DATASET_NAME="idp"
TABLE_NAME="gmail_raw_emails"
LOCATION="us-central1"

# Create dataset first (if it doesn't exist)
bq mk \
    --location=$LOCATION \
    --dataset \
    $PROJECT_ID:$DATASET_NAME

# Create table with schema
bq mk \
    --table \
    $PROJECT_ID:$DATASET_NAME.$TABLE_NAME \
    message_id:STRING:REQUIRED,thread_id:STRING,subject:STRING,sender:STRING,recipient:STRING,date_received:STRING,parsed_date:TIMESTAMP,body_text:STRING,label_ids:STRING,snippet:STRING,message_size:INTEGER,attachment_count:INTEGER,attachments_info:RECORD:REPEATED,attachments_info.file_id:STRING,attachments_info.file_name:STRING,attachments_info.file_type:STRING,attachments_info.gcs_url:STRING,processed_at:TIMESTAMP

# Step 4: Create Cloud Storage Buckets
# =====================================================
# Bucket for Raw Emails Storage
gcloud storage buckets create gs://gmail-attachments-bucket-2fba \
    --location=us-central1 \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access

# Bucket for Pub/Sub Notifications Messages
gcloud storage buckets create gs://gmail-pub-sub-notifications \
    --location=us-central1 \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access

# Step 5: Create Pub/Sub Resources
# =====================================================
gcloud pubsub topics create email-notifier-topic

gcloud pubsub subscriptions create email-notifier-topic-sub --topic=email-notifier-topic

# Step 6: Create Service Account
# =====================================================
# Set your project ID
SERVICE_ACCOUNT_NAME="email-notifier-dev-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Create the service account
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="Email Notifier DEV Service Account" \
    --description="Service account for email notification system dev environment"

# Assign BigQuery Data Editor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/bigquery.dataEditor"

# Assign Cloud Build Editor role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudbuild.builds.editor"

# Assign Cloud Functions Developer role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudfunctions.developer"

# Assign Pub/Sub Publisher role to Gmail API
gcloud pubsub topics add-iam-policy-binding email-notifier \
     --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
     --role=roles/pubsub.publisher

# Assign Storage Object User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/storage.objectUser"

# Assign Storage Object User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/pubsub.editor"

# Step 7: Deployment Settings
# =====================================================
# Grant Cloud Build permissions to deploy functions
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/cloudfunctions.admin

# Grant permissions to access secrets
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/secretmanager.secretAccessor

# Grant Service Account User role
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
    --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/iam.serviceAccountUser
    
# Step 8: Deploy Code
# =====================================================
gcloud functions deploy email-processor \
    --gen2 \
    --runtime=python312 \
    --source=. \
    --entry-point=process_email \
    --trigger-topic=email-notifier \
    --memory=512MB \
    --timeout=60s \
    --region=us-central1  


# Step 3: Test Deployment
# =====================================================
gcloud pubsub topics publish email-notifier \
  --message '{"emailAddress": "jadoon.engr@gmail.com", "messageId": "abc123"}'
