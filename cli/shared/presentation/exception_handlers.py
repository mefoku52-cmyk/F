from fastapi import Request
from fastapi.responses import JSONResponse


class ExceptionHandler:
    @staticmethod
    async def handle(request: Request, exc: Exception) -> JSONResponse:
        status_map = {
            "NotFoundError": 404,
            "ConflictError": 409,
            "ValidationError": 400,
            "UnauthorizedError": 401,
            "ForbiddenError": 403,
        }
        error_type = type(exc).__name__
        status = status_map.get(error_type, 500)
        return JSONResponse(status_code=status, content={"detail": str(exc)})
