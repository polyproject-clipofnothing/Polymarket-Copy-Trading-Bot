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
