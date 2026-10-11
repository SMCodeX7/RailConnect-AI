import logging
from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("railconnect.requests")


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        status_code = 500
        failed = False

        async def send_with_status(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = int(message["status"])

            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        except Exception:
            failed = True
            raise
        finally:
            if failed or status_code >= 500:
                level = logging.ERROR
            elif status_code >= 400:
                level = logging.WARNING
            else:
                level = logging.INFO

            logger.log(
                level,
                "http_request_failed" if failed else "http_request",
                extra={
                    "request_id": scope.get("state", {}).get(
                        "request_id",
                        "unavailable",
                    ),
                    "method": scope["method"],
                    "route": getattr(scope.get("route"), "path", "unmatched"),
                    "status_code": status_code,
                    "duration_ms": round(
                        (perf_counter() - started_at) * 1000,
                        3,
                    ),
                },
            )
