# Terraform Bootstrap (PR12)

Creates:
- S3 bucket for Terraform state
- DynamoDB table for state locking

Auth uses AWS SSO.

Run (once):
```bash
aws sso login --profile polymarket-dev
export AWS_PROFILE=polymarket-dev

cd infra/terraform/bootstrap
terraform init
terraform apply \
  -var="aws_region=us-east-1" \
  -var="env=dev" \
  -var="project=polymarket-copy-bot" \
  -var="tf_state_bucket_name=polymarket-copy-bot-tfstate-dev-137097287791" \
  -var="tf_lock_table_name=polymarket-copy-bot-tf-lock-dev"
