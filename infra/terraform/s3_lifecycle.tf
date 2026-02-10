#############################################
# S3 Lifecycle: Artifacts Cost Control (Dev)
#############################################

resource "aws_s3_bucket_lifecycle_configuration" "objects" {
  bucket = aws_s3_bucket.objects.id

  rule {
    id     = "artifacts-expire-dev"
    status = "Enabled"

    # Scope lifecycle to artifact objects only
    filter {
      prefix = "polymarket-copy-bot/"
    }

    # Delete artifacts after 30 days
    expiration {
      days = 30
    }

    # Clean up old versions if versioning is enabled
    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    # Prevent abandoned multipart uploads from accumulating
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}