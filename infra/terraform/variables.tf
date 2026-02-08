variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "env" {
  type        = string
  description = "Environment name (dev/stage/prod)"
  default     = "dev"
}
