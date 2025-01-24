FROM cpex

ENV DEBIAN_FRONTEND=noninteractive
ENV ANSIBLE_VERSION=2.10

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    software-properties-common \
    curl \
    unzip \
    groff \
    ansible && \
    apt-get clean

# Install Terraform
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
    tee /etc/apt/sources.list.d/hashicorp.list
RUN apt update && apt install -y terraform

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Install Ansible via pip
RUN pip install --upgrade pip; \
    pip install "ansible==${ANSIBLE_VERSION}"; \
    pip install ansible

# Verify tools
RUN terraform --version && \
    ansible --version && \
    aws --version

ENTRYPOINT ["/bin/bash"]
