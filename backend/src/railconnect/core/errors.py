from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from railconnect.core.error_schemas import ErrorResponse

HTTP_ERRORS = {
    400: ("BAD_REQUEST", "The request could not be understood."),
    401: ("UNAUTHENTICATED", "Authentication is required."),
    403: ("FORBIDDEN", "You do not have permission for this action."),
    404: ("NOT_FOUND", "The requested resource was not found."),
    405: ("METHOD_NOT_ALLOWED", "This request method is not allowed."),
    409: ("CONFLICT", "The request conflicts with the current state."),
    415: ("UNSUPPORTED_MEDIA_TYPE", "This request requires a supported content type."),
    422: ("VALIDATION_ERROR", "Some request values are invalid or missing."),
    429: ("RATE_LIMITED", "Too many requests. Please try again later."),
    500: ("INTERNAL_ERROR", "An unexpected error occurred."),
    503: ("SERVICE_UNAVAILABLE", "The service is temporarily unavailable."),
}


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id: str = request.state.request_id
    payload = ErrorResponse(
        code=code,
        message=message,
        request_id=request_id,
    )
    response = JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        headers=headers,
    )
    response.headers["X-Request-ID"] = request_id
    return response


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_error(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        code, message = HTTP_ERRORS.get(
            exc.status_code,
            ("HTTP_ERROR", "The request could not be completed."),
        )
        return error_response(
            request,
            exc.status_code,
            code,
            message,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            request,
            422,
            "VALIDATION_ERROR",
            "Some request values are invalid or missing.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return error_response(
            request,
            500,
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
        )
