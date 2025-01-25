#!/bin/bash
set -e

# 1. Update and upgrade system packages
sudo apt-get update -y
sudo apt-get upgrade -y

# 2. Install dependencies for Docker and Git
sudo apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  git \
  python3 \
  python3-six \
  python3-pip \
  python3-dev 

# 3. Add Docker's official GPG key:
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# 4. Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Update package index and install Docker & Compose plugin
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 6. Add 'ubuntu' user to 'docker' group
sudo groupadd docker || true  # Ignore error if group already exists
sudo usermod -aG docker ubuntu

echo "Setup complete." > /home/ubuntu/done.txt