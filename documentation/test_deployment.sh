#!/bin/bash
# test_deployment.sh - Test the deployed functions

set -e

PROJECT_ID="alpine-comfort-470817-s8"
REGION="us-central1"
FUNCTION_NAME_HTTP="gmail-reader-http"

echo "Testing deployed Gmail Processor functions..."

# Get HTTP function URL
HTTP_URL=$(gcloud functions describe $FUNCTION_NAME_HTTP \
    --region=$REGION \
    --format="value(serviceConfig.uri)")

echo "HTTP Function URL: $HTTP_URL"

# Test HTTP function with curl
echo "Testing HTTP function..."
curl -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "user_email": "test@example.com",
        "criteria": {
            "mark_as_read": false,
            "max_results": 5
        }
    }' \
    "$HTTP_URL" || echo "HTTP test completed (may fail if no Gmail access)"

# Test Pub/Sub function by publishing a message
echo "Testing Pub/Sub function..."
gcloud pubsub topics publish gmail-notifications \
    --message='{"emailAddress": "test@example.com", "historyId": "123456"}' || echo "Pub/Sub test completed"

# Check function logs
echo "Recent HTTP function logs:"
gcloud functions logs read $FUNCTION_NAME_HTTP --region=$REGION --limit=10

echo "Testing completed!"