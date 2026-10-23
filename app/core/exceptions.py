from typing import Any, Optional

class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "BAD_REQUEST", data: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.data = data
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", data: Optional[Any] = None):
        super().__init__(message=message, status_code=404, error_code="NOT_FOUND", data=data)


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request", data: Optional[Any] = None):
        super().__init__(message=message, status_code=400, error_code="BAD_REQUEST", data=data)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized", data: Optional[Any] = None):
        super().__init__(message=message, status_code=401, error_code="UNAUTHORIZED", data=data)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden: insufficient permissions", data: Optional[Any] = None):
        super().__init__(message=message, status_code=403, error_code="FORBIDDEN", data=data)


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict detected", data: Optional[Any] = None):
        super().__init__(message=message, status_code=409, error_code="CONFLICT", data=data)


class InsufficientStockError(AppException):
    def __init__(self, message: str = "Insufficient inventory stock", data: Optional[Any] = None):
        super().__init__(message=message, status_code=400, error_code="INSUFFICIENT_STOCK", data=data)


class PaymentError(AppException):
    def __init__(self, message: str = "Payment processing failed", data: Optional[Any] = None):
        super().__init__(message=message, status_code=402, error_code="PAYMENT_FAILED", data=data)
