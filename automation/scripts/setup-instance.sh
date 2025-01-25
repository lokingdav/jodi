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
  git

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

# 6. (Optional) Add 'ubuntu' user to 'docker' group
sudo groupadd docker
sudo usermod -aG docker ubuntu
newgrp docker

# 7. Clone a specific Git repository as the 'ubuntu' user
#    (replace the URL and target directory as needed)
REPO_URL="https://github.com/lokingdav/cpex.git"
CLONE_DIR="/home/ubuntu/cpex"

# Run git clone as 'ubuntu' user
sudo -u ubuntu git clone "$REPO_URL" "$CLONE_DIR"
