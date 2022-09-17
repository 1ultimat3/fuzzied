variable "aws_profile" {}

variable "fuzzing_data_bucket" {
  default = "fuzzing-data"
}

variable "fuzzing_job_queue_name" {
  default = "fuzzing-job-queue.fifo"
}
