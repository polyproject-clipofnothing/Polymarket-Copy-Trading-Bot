# GitHub Actions OIDC for Terraform (PR16)

## Goal

Run `terraform fmt` / `terraform validate` / `terraform plan` in CI using GitHub Actions OIDC (no long-lived AWS keys).

## Important: Admin apply required

The `polymarket-dev` AWS SSO role does **not** have IAM permissions to create:
- OIDC providers (`iam:CreateOpenIDConnectProvider`)
- IAM roles/policies (`iam:CreateRole`, `iam:PutRolePolicy`, etc.)

Therefore, an AWS admin/security principal must apply the Terraform IAM/OIDC resources once.

PR16 ships:
- Terraform IaC for the OIDC provider + IAM role
- A GitHub Actions workflow that assumes that role via OIDC
- Setup docs

## Terraform resources (admin-only apply)

Terraform file:
- `infra/terraform/iam_github_oidc.tf`

Admin steps:
1. Apply the Terraform configuration from `infra/terraform` using a principal with IAM privileges.
2. Capture the output:
   ```bash
   terraform output github_actions_terraform_role_arn
