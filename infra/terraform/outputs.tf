output "env" {
  description = "Selected environment"
  value       = var.env
}

output "aws_region" {
  description = "Selected AWS region"
  value       = var.aws_region
}


output "s3_objectstore_bucket" {
  value       = "polymarket-copy-bot-objects-dev-137097287791"
  description = "S3 bucket for Phase 1 ObjectStore artifacts."
}

output "s3_objectstore_prefix" {
  value       = "polymarket-copy-bot"
  description = "S3 prefix for Phase 1 ObjectStore artifacts."
}
