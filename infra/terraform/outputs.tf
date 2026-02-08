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
output "github_actions_oidc_provider_arn" {
  value       = aws_iam_openid_connect_provider.github_actions.arn
  description = "OIDC provider ARN for GitHub Actions"
}

output "github_actions_terraform_role_arn" {
  value       = aws_iam_role.github_actions_terraform.arn
  description = "AssumeRole ARN for GitHub Actions Terraform CI"
}
