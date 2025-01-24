terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region = "us-east-1"
}

variable "instance_count" {
  default = 10
}

variable "instance_type" {
  default = "t3.nano"
}

variable "ami" {
  default = "ami-0cb91c7de36eed2cb"
}

variable "key_name" {
  default = "cpex-keypair"
}

variable "regions" {
  default = ["us-east-1", "us-east-2", "us-west-1", "us-west-2"]
}

provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"
}

provider "aws" {
  alias  = "us-east-2"
  region = "us-east-2"
}

provider "aws" {
  alias  = "us-west-1"
  region = "us-west-1"
}

provider "aws" {
  alias  = "us-west-2"
  region = "us-west-2"
}

resource "aws_key_pair" "cpex_keypair" {
  key_name   = var.key_name
  public_key = file("~/.ssh/id_rsa.pub")
}

resource "aws_security_group" "cpex_sg" {
  name_prefix = "cpex-sg-"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 10432
    to_port     = 10432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 11432
    to_port     = 11432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "cpex_nodes" {
  count         = var.instance_count
  ami           = var.ami
  instance_type = var.instance_type
  key_name      = aws_key_pair.cpex_keypair.key_name
  security_groups = [aws_security_group.cpex_sg.name]

  provider = aws["${element(var.regions, count.index % length(var.regions))}"]

  tags = {
    Name = "cpex-node-${count.index}"
  }
}

output "public_ips" {
  value = aws_instance.cpex_nodes[*].public_ip
}

output "private_ips" {
  value = aws_instance.cpex_nodes[*].private_ip
}

output "hosts_file" {
  value = join("\n", [for instance in aws_instance.cpex_nodes : "${instance.public_ip} ansible_user=ec2-user"])
}

resource "local_file" "ansible_hosts" {
  content = <<EOT
all:
  hosts:
${join("\n", [for instance in aws_instance.cpex_nodes : "    ${instance.public_ip}:"])}
EOT

  filename = "./hosts.yml"
}
