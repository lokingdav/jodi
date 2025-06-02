#!/bin/bash

echo "Setting up Livenet configuration..."

# Define the default .ssh directory and key file
SSH_DIR="$HOME/.ssh"
KEY_FILE="$SSH_DIR/id_ed25519"

# Check if the .ssh directory exists, create it if not
if [ ! -d "$SSH_DIR" ]; then
  mkdir -p "$SSH_DIR"
  echo "Created directory: $SSH_DIR"
fi

# Generate the SSH key pair without any prompts
if [ ! -f "$KEY_FILE" ]; then
  ssh-keygen -t ed25519 -f "$KEY_FILE" -N "" -C "default-ed25519-key"
  echo "ED25519 SSH key pair generated in: $SSH_DIR"
else
  echo "ED25519 SSH key pair already exists in: $SSH_DIR"
fi

# Ensure proper permissions
chmod 700 "$SSH_DIR"
chmod 600 "$KEY_FILE"
chmod 644 "$KEY_FILE.pub"

echo "SSH key generation completed in $SSH_DIR."

# Configure AWS CLI directly from .env values
aws configure set aws_access_key_id "$(grep -E "^AWS_ACCESS_KEY_ID=" .env | cut -d= -f2- | tr -d '"'"'")"
aws configure set aws_secret_access_key "$(grep -E "^AWS_SECRET_ACCESS_KEY=" .env | cut -d= -f2- | tr -d '"'"'")"
aws configure set default.region us-east-1
aws configure set default.output json

# Verify the configuration
echo "AWS CLI configuration complete. Testing credentials..."
aws sts get-caller-identity --output json

if [ $? -eq 0 ]; then
    echo "AWS CLI is successfully configured."
else
    echo "There was an error configuring the AWS CLI. Please check your credentials."
fi

cd deployments && terraform init