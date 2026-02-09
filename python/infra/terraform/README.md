# Terraform (AWS) — Skeleton Only (PR11)

This folder is **scaffolding only**.
- No AWS account required to review.
- Do NOT run `terraform apply` in PR11.
- No credentials, no state buckets, no resources are created here yet.

## How this evolves
- PR11: skeleton (this PR)
- PR12: bootstrap remote state (S3 + DynamoDB lock) + backend wiring
- PR13+: add minimal resources incrementally (S3, SQS, IAM, ECS, etc.)

## Files
- `backend.tf.example` — example remote state config (not active yet)
- `env/dev/terraform.tfvars.example` — example env vars (real tfvars are ignored)
