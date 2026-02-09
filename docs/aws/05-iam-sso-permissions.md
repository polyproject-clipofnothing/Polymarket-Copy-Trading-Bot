# IAM / AWS SSO Permissions (PR15)

PR15 introduces a least-privilege IAM policy for the Phase 1 S3 ObjectStore bucket/prefix and documents how to attach it to the AWS SSO Permission Set used by the `polymarket-dev` profile.

## What this enables

Allows the Phase 1 services (simulation/recorder artifacts) to read/write only:

- Bucket: `polymarket-copy-bot-objects-dev-137097287791`
- Prefix: `polymarket-copy-bot/*`

## Terraform outputs

After applying infra, capture:

- `s3_objectstore_policy_arn`
- `s3_objectstore_bucket`
- `s3_objectstore_prefix`

## Apply the policy (Terraform)

```bash
aws sso login --profile polymarket-dev
export AWS_PROFILE=polymarket-dev

cd infra/terraform
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
terraform output
