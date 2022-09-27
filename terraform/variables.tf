variable "aws_profile" {}

variable "admin_ip" {}

variable "fuzzied_scheduler_count" {
  default = "0"
}

variable "fuzzied_bot_count" {
  default = "0"
}

variable "fuzzing_data_bucket" {
  default = "fuzzing-data"
}

variable "fuzzing_job_queue_name" {
  default = "fuzzing-job-queue.fifo"
}

variable "fuzzing_report_queue_name" {
  default = "fuzzing-report-queue.fifo"
}
