# S3 ObjectStore (PR13)

PR13 adds an S3-backed implementation of the cloud `ObjectStore` boundary.

## Bucket
- `polymarket-copy-bot-objects-dev-137097287791`
- Prefix: `polymarket-copy-bot/`

## Enable (AWS SSO)
```bash
aws sso login --profile polymarket-dev
export AWS_PROFILE=polymarket-dev

export CLOUD_BACKEND=local
export OBJECT_STORE_BACKEND=s3
export AWS_REGION=us-east-1
export S3_OBJECT_BUCKET=polymarket-copy-bot-objects-dev-137097287791
export S3_OBJECT_PREFIX=polymarket-copy-bot
