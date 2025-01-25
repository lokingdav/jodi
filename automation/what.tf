terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }
  required_version = ">= 1.2.0"
}

data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

provider "aws" {
  region = "us-east-1"
}

variable "instance_type" {
  default = "t3.nano"
}

variable "key_name" {
  default = "cpex-keypair"
}

variable "us_east_1_count" {
  default = 3
}

variable "us_east_2_count" {
  default = 3
}

variable "us_west_1_count" {
  default = 2
}

variable "us_west_2_count" {
  default = 2
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
  public_key = file("~/.ssh/id_ed25519.pub")
}

resource "aws_security_group" "cpex_sg_use1" {
  provider   = aws.us-east-1
  name_prefix = "cpex-sg-use1-"
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

resource "aws_security_group" "cpex_sg_use2" {
  provider   = aws.us-east-2
  name_prefix = "cpex-sg-use2-"
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

resource "aws_security_group" "cpex_sg_usw1" {
  provider   = aws.us-west-1
  name_prefix = "cpex-sg-usw1-"
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

resource "aws_security_group" "cpex_sg_usw2" {
  provider   = aws.us-west-2
  name_prefix = "cpex-sg-usw2-"
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

resource "aws_instance" "cpex_nodes_use1" {
  provider        = aws.us-east-1
  count           = var.us_east_1_count
  ami             = data.aws_ami.ubuntu.id
  instance_type   = var.instance_type
  key_name        = aws_key_pair.cpex_keypair.key_name
  security_groups = [aws_security_group.cpex_sg_use1.name]
  tags = {
    Name = "cpex-node-use1-${count.index}"
  }
}

resource "aws_instance" "cpex_nodes_use2" {
  provider        = aws.us-east-2
  count           = var.us_east_2_count
  ami             = data.aws_ami.ubuntu.id
  instance_type   = var.instance_type
  key_name        = aws_key_pair.cpex_keypair.key_name
  security_groups = [aws_security_group.cpex_sg_use2.name]
  tags = {
    Name = "cpex-node-use2-${count.index}"
  }
}

resource "aws_instance" "cpex_nodes_usw1" {
  provider        = aws.us-west-1
  count           = var.us_west_1_count
  ami             = data.aws_ami.ubuntu.id
  instance_type   = var.instance_type
  key_name        = aws_key_pair.cpex_keypair.key_name
  security_groups = [aws_security_group.cpex_sg_usw1.name]
  tags = {
    Name = "cpex-node-usw1-${count.index}"
  }
}

resource "aws_instance" "cpex_nodes_usw2" {
  provider        = aws.us-west-2
  count           = var.us_west_2_count
  ami             = data.aws_ami.ubuntu.id
  instance_type   = var.instance_type
  key_name        = aws_key_pair.cpex_keypair.key_name
  security_groups = [aws_security_group.cpex_sg_usw2.name]
  tags = {
    Name = "cpex-node-usw2-${count.index}"
  }
}

output "public_ips" {
  value = concat(
    aws_instance.cpex_nodes_use1[*].public_ip,
    aws_instance.cpex_nodes_use2[*].public_ip,
    aws_instance.cpex_nodes_usw1[*].public_ip,
    aws_instance.cpex_nodes_usw2[*].public_ip
  )
}

output "private_ips" {
  value = concat(
    aws_instance.cpex_nodes_use1[*].private_ip,
    aws_instance.cpex_nodes_use2[*].private_ip,
    aws_instance.cpex_nodes_usw1[*].private_ip,
    aws_instance.cpex_nodes_usw2[*].private_ip
  )
}

output "hosts_file" {
  value = join(
    "\n",
    [
      for instance in concat(
        aws_instance.cpex_nodes_use1,
        aws_instance.cpex_nodes_use2,
        aws_instance.cpex_nodes_usw1,
        aws_instance.cpex_nodes_usw2
      ) : "${instance.public_ip} ansible_user=ec2-user"
    ]
  )
}

resource "local_file" "ansible_hosts" {
  content = <<EOT
all:
  hosts:
${join(
  "\n",
  [
    for instance in concat(
      aws_instance.cpex_nodes_use1,
      aws_instance.cpex_nodes_use2,
      aws_instance.cpex_nodes_usw1,
      aws_instance.cpex_nodes_usw2
    ) : "    ${instance.public_ip}:"
  ]
)}
EOT

  filename = "./hosts.yml"
}
