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
