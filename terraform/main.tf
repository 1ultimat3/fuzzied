provider "aws" {
  profile                     = "${var.aws_profile}"
  region                      = "us-east-1"
}

resource "aws_s3_bucket" "fuzzing-data" {
    bucket = "${var.fuzzing_data_bucket}"
}

resource "aws_sqs_queue" "fuzzing-job-queue" {
  name                        = "${var.fuzzing_job_queue_name}"
  fifo_queue                  = true
  content_based_deduplication = false
}

resource "aws_default_vpc" "default" {
  tags = {
    Name = "Default VPC"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

resource "aws_instance" "fuzzied_scheduler" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"
  key_name      = "fuzzied"
  vpc_security_group_ids = [aws_security_group.main.id]

  tags = {
    Name = "fuzzied_scheduler"
  }
}

resource "aws_spot_instance_request" "fuzzied_bot" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.large"
  key_name      = "fuzzied"
  spot_price    = 0.03
  spot_type     = "one-time"
  vpc_security_group_ids = [aws_security_group.main.id]

  tags = {
    Name = "fuzzied_scheduler"
  }
}

resource "aws_security_group" "main" {
  egress = [
    {
      cidr_blocks      = [ "0.0.0.0/0", ]
      description      = ""
      from_port        = 0
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      protocol         = "-1"
      security_groups  = []
      self             = false
      to_port          = 0
    }
  ]
 ingress                = [
   {
     cidr_blocks      = [ "109.40.240.72/32", ]
     description      = ""
     from_port        = 22
     ipv6_cidr_blocks = []
     prefix_list_ids  = []
     protocol         = "tcp"
     security_groups  = []
     self             = false
     to_port          = 22
  }
  ]
}
