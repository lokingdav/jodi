terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.4"
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
  default = "cpex-keypair"
}

variable "us_east_1_count" {
  default = 5
}

variable "us_east_2_count" {
  default = 5
}

variable "us_west_1_count" {
  default = 5
}

variable "us_west_2_count" {
  default = 5
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
  name_prefix = "cpex-sg-use1-"

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
  name_prefix = "cpex-sg-use2-"

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
  name_prefix = "cpex-sg-usw1-"

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
  name_prefix = "cpex-sg-usw2-"

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

resource "aws_instance" "cpex_nodes_use1" {
  provider        = aws.us-east-1
  count           = var.us_east_1_count
  ami             = var.ubuntu_ami_map["us-east-1"]
  instance_type   = var.instance_type
  key_name        = aws_key_pair.use1.key_name
  security_groups = [aws_security_group.sg_use1.name]

  user_data       = file("${path.module}/scripts/setup-instance.sh")

  tags = {
    Name = "cpex-node-use1-${count.index}"
  }
}

resource "aws_instance" "cpex_nodes_use2" {
  provider        = aws.us-east-2
  count           = var.us_east_2_count
  ami             = var.ubuntu_ami_map["us-east-2"]
  instance_type   = var.instance_type
  key_name        = aws_key_pair.use2.key_name
  security_groups = [aws_security_group.sg_use2.name]

  user_data       = file("${path.module}/scripts/setup-instance.sh")

  tags = {
    Name = "cpex-node-use2-${count.index}"
  }
}

resource "aws_instance" "cpex_nodes_usw1" {
  provider        = aws.us-west-1
  count           = var.us_west_1_count
  ami             = var.ubuntu_ami_map["us-west-1"]
  instance_type   = var.instance_type
  key_name        = aws_key_pair.usw1.key_name
  security_groups = [aws_security_group.sg_usw1.name]

  user_data       = file("${path.module}/scripts/setup-instance.sh")

  tags = {
    Name = "cpex-node-usw1-${count.index}"
  }
}

resource "aws_instance" "cpex_nodes_usw2" {
  provider        = aws.us-west-2
  count           = var.us_west_2_count
  ami             = var.ubuntu_ami_map["us-west-2"]
  instance_type   = var.instance_type
  key_name        = aws_key_pair.usw2.key_name
  security_groups = [aws_security_group.sg_usw2.name]

  user_data       = file("${path.module}/scripts/setup-instance.sh")

  tags = {
    Name = "cpex-node-usw2-${count.index}"
  }
}

# Combine all public or private IPs if desired:
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

# ---------------------------------------------------------------------
# 1) Create a random shuffle of all instance IDs to randomize the grouping
# ---------------------------------------------------------------------
resource "random_shuffle" "cpex_node_ids" {
  input = [
    for instance in concat(
      aws_instance.cpex_nodes_use1,
      aws_instance.cpex_nodes_use2,
      aws_instance.cpex_nodes_usw1,
      aws_instance.cpex_nodes_usw2
    ) : instance.id
  ]

  result_count = length(concat(
    aws_instance.cpex_nodes_use1,
    aws_instance.cpex_nodes_use2,
    aws_instance.cpex_nodes_usw1,
    aws_instance.cpex_nodes_usw2
  ))
}

# ---------------------------------------------------------------------
# 2) Build a local map of instance_id => { name, public_ip }
# ---------------------------------------------------------------------
locals {
  all_instances = concat(
    aws_instance.cpex_nodes_use1,
    aws_instance.cpex_nodes_use2,
    aws_instance.cpex_nodes_usw1,
    aws_instance.cpex_nodes_usw2
  )

  # Create a map of ID => object containing name, public IP
  cpex_nodes_map = {
    for inst in local.all_instances :
    inst.id => {
      name = inst.tags.Name
      ip   = inst.public_ip
    }
  }

  node_count = length(local.all_instances)
}

# ---------------------------------------------------------------------
# 3) In the final hosts.yml, half of the instances are “stores”
#    and the other half are “evaluators,” in a random order
# ---------------------------------------------------------------------
resource "local_file" "ansible_hosts" {
  filename = "./hosts.yml"

  content = <<-EOT
all:
  hosts:
${join("\n", [
  for i, node_id in random_shuffle.cpex_node_ids.result : format(
    "    %s:\n      ansible_host: %s\n      ansible_user: ubuntu\n      label: %s",
    local.cpex_nodes_map[node_id].name,
    local.cpex_nodes_map[node_id].ip,
    i < floor(local.node_count / 2) ? "store" : "evaluator"
  )
])}
EOT
}

# You can still output the final line-based hosts if desired:
output "hosts_file" {
  value = local_file.ansible_hosts.content
}
