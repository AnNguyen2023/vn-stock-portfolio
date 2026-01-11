from typing import Any, Optional
from fastapi import HTTPException, status

class AppBaseException(Exception):
    """Base category for all application-specific errors."""
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)

class EntityNotFoundException(AppBaseException):
    """Raised when a requested resource (Ticker, Trade, User) is not found."""
    def __init__(self, entity: str, identifier: Any):
        super().__init__(
            message=f"{entity} with ID/Code '{identifier}' not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )

class ValidationError(AppBaseException):
    """Raised for business logic validation failures."""
    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class ExternalServiceError(AppBaseException):
    """Raised when a third-party API (VNStock, Supabase) fails or times out."""
    def __init__(self, service_name: str, message: str = "External service unavailable"):
        super().__init__(
            message=f"[{service_name}] Error: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY
        )

class UnauthorizedError(AppBaseException):
    """Raised for authentication or permission issues."""
    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
