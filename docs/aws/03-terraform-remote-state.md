# Terraform Remote State (PR12)

This document describes how Terraform remote state is configured for this repository.

Remote state is required so:
- Terraform state is not stored locally
- Multiple contributors can safely run Terraform
- State locking prevents concurrent writes

This setup is introduced in **PR12**.

---

## Overview

Terraform remote state is backed by:
- **S3** for state storage
- **DynamoDB** for state locking
- **AWS SSO** for authentication (no static credentials)

The remote backend is configured once and reused by all Terraform stacks in this repo.

---

## AWS Account & Region

- **AWS Account ID:** `137097287791`
- **Region:** `us-east-1`
- **AWS Auth:** IAM Identity Center (AWS SSO)

---

## Remote State Resources

### S3 State Bucket

- **Name:**  
  `polymarket-copy-bot-tfstate-dev-137097287791`

- **Purpose:**  
  Stores Terraform state files (`terraform.tfstate`)

- **Configuration:**
  - Versioning enabled
  - Server-side encryption enabled (AES256)
  - Public access fully blocked

---

### DynamoDB Lock Table

- **Name:**  
  `polymarket-copy-bot-tf-lock-dev`

- **Purpose:**  
  Prevents concurrent Terraform runs from corrupting state

- **Key Schema:**
  - Partition key: `LockID` (string)

- **Billing Mode:**  
  `PAY_PER_REQUEST`

---

## Directory Structure

