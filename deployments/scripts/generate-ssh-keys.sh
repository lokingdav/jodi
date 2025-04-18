#!/bin/bash

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
