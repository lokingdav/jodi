#!/bin/bash

if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
else
    echo ".env file not found."
    exit 1
fi

# Configure AWS CLI
aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID"
aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY"
aws configure set default.region "$AWS_DEFAULT_REGION"
aws configure set default.output "$AWS_OUTPUT_FORMAT"

# Verify the configuration
echo "AWS CLI configuration complete. Testing credentials..."
aws sts get-caller-identity --output json

if [ $? -eq 0 ]; then
    echo "AWS CLI is successfully configured."
else
    echo "There was an error configuring the AWS CLI. Please check your credentials."
fi
