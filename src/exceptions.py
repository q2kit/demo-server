from django.core.exceptions import PermissionDenied


class CsrfFailureException(PermissionDenied):
    """Raised when CSRF validation fails."""

    def __init__(self, message="CSRF token missing or incorrect.") -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message
