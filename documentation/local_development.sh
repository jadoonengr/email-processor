#!/bin/bash
# local_development.sh - Set up local development environment

set -e

echo "Setting up local development environment..."

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Create necessary directories
mkdir -p logs
mkdir -p tests
mkdir -p schema

# Set up environment variables
cat > .env << EOF
# Local development environment variables
PROJECT_ID=alpine-comfort-470817-s8
DATASET_NAME=gmail_data
TABLE_NAME=email_messages
BUCKET_NAME=gmail-attachments-bucket-2fba
PUBSUB_TOPIC=gmail-notifications
PUBSUB_SUBSCRIPTION=gmail-notifications-sub
REGION=us-central1
ENVIRONMENT=development

# Service account (for local testing - use a test service account)
GOOGLE_APPLICATION_CREDENTIALS=./test-service-account.json
EOF

echo "Local development environment set up!"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Download test service account key to test-service-account.json"
echo "3. Update .env file with your specific values"
echo "4. Run tests: pytest"
echo "5. Start local development: functions-framework --target=gmail_reader_http"