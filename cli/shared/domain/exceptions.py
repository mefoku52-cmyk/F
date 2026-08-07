class AppException(Exception):
    """Base exception for application."""

    pass


class NotFoundError(AppException):
    pass


class ConflictError(AppException):
    pass


class ValidationError(AppException):
    pass


class UnauthorizedError(AppException):
    pass


class ForbiddenError(AppException):
    pass
