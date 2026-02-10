# Terraform Bootstrap Stack

This stack contains **one-time, account-level IAM resources** that must be
created by an AWS principal with **IAM admin privileges**.

It is intentionally **separate** from the main Terraform stack.

---

## What This Stack Creates

- GitHub Actions **OIDC Provider**
- IAM Role assumed by GitHub Actions via OIDC
- Inline IAM policy granting Terraform CI limited permissions

**This stack does NOT create:**
- Terraform state S3 bucket
- DynamoDB lock table
- Application infrastructure

Those are managed by the main Terraform stack.

---

## Why This Stack Exists

Separating bootstrap IAM resources ensures:

- CI **cannot modify its own permissions**
- IAM changes are explicit and auditable
- Application Terraform remains least-privileged
- Future PRs don’t accidentally cause IAM drift

This is a standard, production-grade Terraform pattern.

---

## Prerequisites

- AWS SSO profile with **IAM admin permissions**
- Terraform installed locally
- AWS region: `us-east-1`

---

## Authenticate (AWS SSO)

```bash
aws sso login --profile polymarket-admin
export AWS_PROFILE=polymarket-admin