terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }
  required_version = ">= 1.2.0"
}

variable "ubuntu_ami_map" {
  type = map(string)
  default = {
    "us-east-1" = "ami-04b4f1a9cf54c11d0"
    "us-east-2" = "ami-0cb91c7de36eed2cb"
    "us-west-1" = "ami-07d2649d67dbe8900"
    "us-west-2" = "ami-00c257e12d6828491"
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "instance_type" {
  default = "t3.small"
}

variable "key_name" {
  default = "livenet-keypair"
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

variable "sg_start_port" {
  default = 10430
}

variable "sg_end_port" {
  default = 10434
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

resource "aws_key_pair" "use1" {
  provider    = aws.us-east-1
  key_name    = var.key_name
  public_key  = file("~/.ssh/id_ed25519.pub")
}

resource "aws_key_pair" "use2" {
  provider    = aws.us-east-2
  key_name    = var.key_name
  public_key  = file("~/.ssh/id_ed25519.pub")
}

resource "aws_key_pair" "usw1" {
  provider    = aws.us-west-1
  key_name    = var.key_name
  public_key  = file("~/.ssh/id_ed25519.pub")
}

resource "aws_key_pair" "usw2" {
  provider    = aws.us-west-2
  key_name    = var.key_name
  public_key  = file("~/.ssh/id_ed25519.pub")
}

resource "aws_security_group" "sg_use1" {
  provider    = aws.us-east-1
  name_prefix = "livenet-sg-use1-"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = var.sg_start_port
    to_port     = var.sg_end_port
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

resource "aws_security_group" "sg_use2" {
  provider    = aws.us-east-2
  name_prefix = "livenet-sg-use2-"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = var.sg_start_port
    to_port     = var.sg_end_port
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

resource "aws_security_group" "sg_usw1" {
  provider    = aws.us-west-1
  name_prefix = "livenet-sg-usw1-"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = var.sg_start_port
    to_port     = var.sg_end_port
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

resource "aws_security_group" "sg_usw2" {
  provider    = aws.us-west-2
  name_prefix = "livenet-sg-usw2-"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = var.sg_start_port
    to_port     = var.sg_end_port
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

resource "aws_instance" "livenet_nodes_use1" {
  provider        = aws.us-east-1
  count           = var.us_east_1_count
  ami             = var.ubuntu_ami_map["us-east-1"]
  instance_type   = var.instance_type
  key_name        = aws_key_pair.use1.key_name
  security_groups = [aws_security_group.sg_use1.name]

  user_data       = file("../${path.module}/scripts/setup-instance.sh")

  tags = {
    Name = "livenet-node-use1-${count.index}"
  }
}

resource "aws_instance" "livenet_nodes_use2" {
  provider        = aws.us-east-2
  count           = var.us_east_2_count
  ami             = var.ubuntu_ami_map["us-east-2"]
  instance_type   = var.instance_type
  key_name        = aws_key_pair.use2.key_name
  security_groups = [aws_security_group.sg_use2.name]

  user_data       = file("../${path.module}/scripts/setup-instance.sh")

  tags = {
    Name = "livenet-node-use2-${count.index}"
  }
}

resource "aws_instance" "livenet_nodes_usw1" {
  provider        = aws.us-west-1
  count           = var.us_west_1_count
  ami             = var.ubuntu_ami_map["us-west-1"]
  instance_type   = var.instance_type
  key_name        = aws_key_pair.usw1.key_name
  security_groups = [aws_security_group.sg_usw1.name]

  user_data       = file("../${path.module}/scripts/setup-instance.sh")

  tags = {
    Name = "livenet-node-usw1-${count.index}"
  }
}

resource "aws_instance" "livenet_nodes_usw2" {
  provider        = aws.us-west-2
  count           = var.us_west_2_count
  ami             = var.ubuntu_ami_map["us-west-2"]
  instance_type   = var.instance_type
  key_name        = aws_key_pair.usw2.key_name
  security_groups = [aws_security_group.sg_usw2.name]

  user_data       = file("../${path.module}/scripts/setup-instance.sh")

  tags = {
    Name = "livenet-node-usw2-${count.index}"
  }
}

output "public_ips" {
  value = concat(
    aws_instance.livenet_nodes_use1[*].public_ip,
    aws_instance.livenet_nodes_use2[*].public_ip,
    aws_instance.livenet_nodes_usw1[*].public_ip,
    aws_instance.livenet_nodes_usw2[*].public_ip
  )
}

output "private_ips" {
  value = concat(
    aws_instance.livenet_nodes_use1[*].private_ip,
    aws_instance.livenet_nodes_use2[*].private_ip,
    aws_instance.livenet_nodes_usw1[*].private_ip,
    aws_instance.livenet_nodes_usw2[*].private_ip
  )
}

output "hosts_file" {
  value = join(
    "\n",
    [
      for instance in concat(
        aws_instance.livenet_nodes_use1,
        aws_instance.livenet_nodes_use2,
        aws_instance.livenet_nodes_usw1,
        aws_instance.livenet_nodes_usw2
      ) : "${instance.tags.Name} ansible_host=${instance.public_ip} ansible_user=ubuntu"
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
      aws_instance.livenet_nodes_use1,
      aws_instance.livenet_nodes_use2,
      aws_instance.livenet_nodes_usw1,
      aws_instance.livenet_nodes_usw2
    ) : "    ${instance.tags.Name}:\n      ansible_host: ${instance.public_ip}\n      ansible_user: ubuntu"
  ]
)}
EOT

  filename = "./hosts.yml"
}
