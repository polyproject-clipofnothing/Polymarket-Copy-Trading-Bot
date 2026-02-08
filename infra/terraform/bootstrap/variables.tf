variable "aws_region" {
  type        = string
  description = "AWS region for bootstrap resources"
  default     = "us-east-1"
}

variable "project" {
  type        = string
  description = "Project name used for tagging/naming"
  default     = "polymarket-copy-bot"
}

variable "env" {
  type        = string
  description = "Environment name"
  default     = "dev"
}

variable "tf_state_bucket_name" {
  type        = string
  description = "Globally-unique S3 bucket name for Terraform remote state"
}

variable "tf_lock_table_name" {
  type        = string
  description = "DynamoDB table name for Terraform state locking"
}
