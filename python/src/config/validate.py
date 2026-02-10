from __future__ import annotations

import os


class ConfigError(RuntimeError):
    """
    Raised when runtime configuration is missing or invalid.
    Use this to fail fast with a clear, actionable message.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


def _getenv(name: str) -> str | None:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip()
    return v if v else None


def require_env(name: str) -> str:
    """
    Require that an env var exists and is non-empty.
    Raises ConfigError with a clear message if missing.
    """
    v = _getenv(name)
    if v is None:
        raise ConfigError(f"Missing required env var: {name}")
    return v


def optional_env(name: str, default: str) -> str:
    v = _getenv(name)
    return v if v is not None else default


def _normalize_prefix(prefix: str) -> str:
    # Clean to "polymarket-copy-bot" (no leading/trailing slashes)
    return prefix.strip().strip("/")


def validate_object_store_config() -> None:
    """
    Validates OBJECT_STORE_BACKEND-related config.

    Rules:
    - OBJECT_STORE_BACKEND=local  -> no AWS vars required
    - OBJECT_STORE_BACKEND=s3     -> require AWS_REGION, S3_OBJECT_BUCKET, S3_OBJECT_PREFIX
    """
    backend = optional_env("OBJECT_STORE_BACKEND", "local").lower()

    if backend == "local":
        return

    if backend != "s3":
        raise ConfigError(
            f"Invalid OBJECT_STORE_BACKEND={backend!r}. Allowed values: 'local', 's3'."
        )

    missing: list[str] = []
    aws_region = _getenv("AWS_REGION")
    bucket = _getenv("S3_OBJECT_BUCKET")
    prefix = _getenv("S3_OBJECT_PREFIX")

    if aws_region is None:
        missing.append("AWS_REGION")
    if bucket is None:
        missing.append("S3_OBJECT_BUCKET")
    if prefix is None:
        missing.append("S3_OBJECT_PREFIX")

    if missing:
        raise ConfigError(
            "S3 ObjectStore misconfigured. Missing: "
            + ", ".join(missing)
            + ". Example:\n"
            + "  export OBJECT_STORE_BACKEND=s3\n"
            + "  export AWS_REGION=us-east-1\n"
            + "  export S3_OBJECT_BUCKET=polymarket-copy-bot-objects-dev-137097287791\n"
            + "  export S3_OBJECT_PREFIX=polymarket-copy-bot"
        )

    norm = _normalize_prefix(prefix)
    if not norm:
        raise ConfigError("S3_OBJECT_PREFIX cannot be empty (or only slashes).")

    # Write back normalized prefix so downstream callers always get a clean value
    os.environ["S3_OBJECT_PREFIX"] = norm


def validate_cloud_backend_config() -> None:
    """
    Validates CLOUD_BACKEND for phase safety.

    Phase 1/2 expectation:
      - CLOUD_BACKEND must remain 'local'
      - OBJECT_STORE_BACKEND may be local or s3 (objectstore only)
    """
    backend = optional_env("CLOUD_BACKEND", "local").lower()

    if backend not in ("local", "aws"):
        raise ConfigError(f"Invalid CLOUD_BACKEND={backend!r}. Allowed: 'local', 'aws'.")

    # Phase-safe default: disallow aws cloud backend until Phase 2+ explicitly enables it
    if backend == "aws":
        raise ConfigError(
            "CLOUD_BACKEND='aws' is not supported yet. Use CLOUD_BACKEND=local."
        )


def validate_runtime_config() -> None:
    """
    Baseline validation for ALL services.

    Must NOT require trading secrets.
    Must be phase-safe.
    """
    validate_cloud_backend_config()
    validate_object_store_config()


def validate_strategy_config() -> None:
    """
    Strategy-specific validation (Phase 2 signal-only).
    Add requirements as you introduce them.
    """
    return


def validate_trading_config() -> None:
    """
    Execution/Trader-specific validation (Phase 3+).

    IMPORTANT:
    - Only call this from execution/trader entrypoints.
    - Do NOT call from Phase 1/2 services.
    """
    enabled = optional_env("ENABLE_TRADING", "false").lower() == "true"
    if not enabled:
        raise ConfigError(
            "Trading is disabled. Set ENABLE_TRADING=true to run execution/trader services."
        )

    missing: list[str] = []
    for name in [
        # Examples — adjust later as your trading integration evolves
        "POLYMARKET_PRIVATE_KEY",
        "POLYMARKET_API_KEY",
    ]:
        if _getenv(name) is None:
            missing.append(name)

    if missing:
        raise ConfigError("Trading enabled but required secrets are missing: " + ", ".join(missing))