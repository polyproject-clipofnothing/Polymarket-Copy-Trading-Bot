class CloudError(RuntimeError):
    """Base error for cloud boundary failures."""


class SecretNotFound(CloudError):
    """Raised when a secret key is missing."""


class ObjectNotFound(CloudError):
    """Raised when an object/path is missing."""

class CloudError(RuntimeError):
    """Base error for cloud boundary failures."""


class SecretNotFound(CloudError):
    """Raised when a secret key is missing."""


class ObjectNotFound(CloudError):
    """Raised when an object/path is missing."""
