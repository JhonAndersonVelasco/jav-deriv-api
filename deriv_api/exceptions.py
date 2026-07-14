"""
Exceptions for the Deriv API client library.
"""


class DerivAPIError(Exception):
    """Base exception for all Deriv API errors."""

    def __init__(self, message: str, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


class DerivConnectionError(DerivAPIError):
    """Raised when the WebSocket connection cannot be established or is lost."""


class DerivAuthError(DerivAPIError):
    """Raised when authentication fails or an auth token is missing for a protected endpoint."""


class DerivRequestError(DerivAPIError):
    """Raised when the API returns an error response to a request."""

    @classmethod
    def from_response(cls, response: dict) -> "DerivRequestError":
        """Build a DerivRequestError from a raw API error dict."""
        error = response.get("error", {})
        code = error.get("code", "UnknownError")
        message = error.get("message", "An unknown error occurred.")
        return cls(message=message, code=code, details=error)


class DerivTimeoutError(DerivAPIError):
    """Raised when a request does not receive a response within the timeout period."""


class DerivValidationError(DerivAPIError):
    """Raised when request parameters fail local validation before being sent."""


class DerivStreamError(DerivAPIError):
    """Raised when an active subscription stream encounters an error."""
