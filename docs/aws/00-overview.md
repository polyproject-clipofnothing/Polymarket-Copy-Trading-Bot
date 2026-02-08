# AWS Overview (Planned)

## Phase 1 (current)
- Uses `src/cloud` boundary with **local** implementations:
  - events -> JSONL (logs/cloud_events)
  - objects -> filesystem (simulation_results/objects)
  - secrets -> env vars

## Phase 2 (future)
Swap implementations behind the same interfaces:
- EventPublisher -> SQS (or Kinesis)
- ObjectStore -> S3
- SecretProvider -> AWS Secrets Manager

## IaC approach
Terraform is the source of truth for AWS resources.
PR11 only adds skeleton structure (no provisioning).
