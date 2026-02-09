# NOTE:
# This file must be applied by an AWS principal with IAM admin privileges.
# The polymarket-dev SSO role does NOT have permission to create:
# - aws_iam_openid_connect_provider
# - aws_iam_role / policies
# PR16 ships the IaC + CI workflow; an admin must apply infra once.


#############################################
# GitHub Actions OIDC → AssumeRole (Terraform)
#############################################

data "aws_partition" "current" {}
data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  # Update these to match your repo exactly:
  github_owner = "polyproject-clipofnothing"
  github_repo  = "Polymarket-Copy-Trading-Bot"

  # Role name (keep stable; used in docs/workflow)
  gha_role_name = "polymarket-copy-bot-terraform-ci"

  # Terraform remote state resources (from your earlier work)
  tfstate_bucket = "polymarket-copy-bot-tfstate-dev-137097287791"
  tfstate_key    = "polymarket-copy-bot/dev/terraform.tfstate"
  tf_lock_table  = "polymarket-copy-bot-tf-lock-dev"

  # Artifacts bucket (current stack manages this)
  artifacts_bucket = "polymarket-copy-bot-objects-dev-137097287791"
}

#############################################
# 1) OIDC Provider for GitHub Actions
#############################################

resource "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]

  # GitHub uses standard CA chains; AWS still requires thumbprints.
  # This value is commonly used for GitHub's OIDC provider.
  # If your org requires a different thumbprint, update here.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
  ]
}

#############################################
# 2) IAM Role assumed by GitHub Actions (OIDC)
#############################################

data "aws_iam_policy_document" "github_actions_trust" {
  statement {
    sid     = "GitHubActionsAssumeRoleWithOIDC"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    # Restrict to your repo
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Allow PRs/branches to plan:
    # sub format: repo:<owner>/<repo>:ref:refs/heads/<branch>
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${local.github_owner}/${local.github_repo}:ref:refs/heads/*",
      ]
    }

    # Optional hardening (later): restrict to a workflow file using job_workflow_ref
    # condition {
    #   test     = "StringLike"
    #   variable = "token.actions.githubusercontent.com:job_workflow_ref"
    #   values   = ["${local.github_owner}/${local.github_repo}/.github/workflows/terraform.yml@*"]
    # }
  }
}

resource "aws_iam_role" "github_actions_terraform" {
  name               = local.gha_role_name
  assume_role_policy = data.aws_iam_policy_document.github_actions_trust.json
  description        = "GitHub Actions OIDC role for Terraform CI (fmt/validate/plan)"
}

#############################################
# 3) Least-privilege permissions for CI role
#############################################

data "aws_iam_policy_document" "github_actions_terraform_permissions" {
  # --- Terraform state bucket access (scoped to key) ---
  statement {
    sid    = "TfStateListBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${local.tfstate_bucket}",
    ]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = [local.tfstate_key]
    }
  }

  statement {
    sid    = "TfStateObjectRW"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${local.tfstate_bucket}/${local.tfstate_key}",
    ]
  }

  # --- DynamoDB state lock table ---
  statement {
    sid    = "TfLockTableRW"
    effect = "Allow"
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
      "dynamodb:UpdateItem",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:dynamodb:*:${local.account_id}:table/${local.tf_lock_table}",
    ]
  }

  # --- Stack resources Terraform manages (start: S3 artifacts bucket) ---
  statement {
    sid    = "ArtifactsBucketRead"
    effect = "Allow"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${local.artifacts_bucket}",
    ]
  }

  statement {
    sid    = "ArtifactsBucketWriteObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${local.artifacts_bucket}/*",
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_terraform_inline" {
  name   = "terraform-ci-inline"
  role   = aws_iam_role.github_actions_terraform.id
  policy = data.aws_iam_policy_document.github_actions_terraform_permissions.json
}
