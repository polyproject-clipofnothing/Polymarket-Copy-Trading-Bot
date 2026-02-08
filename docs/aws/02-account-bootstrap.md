# AWS Account Bootstrap (Planned for PR12)

This will be implemented in PR12 with a careful checklist.

## Bootstrap resources
- S3 bucket for Terraform remote state
- DynamoDB table for Terraform state locking

## Notes
- No app resources yet (no ECS/SQS/S3 app buckets/IAM roles for runtime)
- No secrets stored yet
