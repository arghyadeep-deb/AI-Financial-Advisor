"""Structured error contract (architecture.md > API conventions).

Every error body keeps the legacy ``detail`` key (existing clients read it)
and adds ``{code, message, request_id, retryable, field_errors}``.
Request validation errors never echo submitted values (no secrets/PII).
"""
import logging
import uuid
from typing import Any, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("advisor.api")

_CODES = {400: "bad_request", 401: "unauthenticated", 403: "forbidden", 404: "not_found",
          409: "conflict", 422: "validation_error", 429: "rate_limited"}


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "") or ""


def _body(request: Request, status_code: int, detail: Any) -> dict:
    code = _CODES.get(status_code, "server_error" if status_code >= 500 else "error")
    message = detail if isinstance(detail, str) else (detail or {}).get("message", "Request failed.")
    if isinstance(detail, dict) and detail.get("code"):
        code = detail["code"]
    body = {
        "detail": detail,
        "code": code,
        "message": message,
        "request_id": request_id_of(request),
        "retryable": status_code in (429, 502, 503, 504),
        "field_errors": [],
    }
    if isinstance(detail, dict):
        body.update({k: v for k, v in detail.items() if k not in body})
    return body


def install(app: FastAPI) -> None:

    @app.middleware("http")
    async def _request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id", "")[:64]
        request.state.request_id = rid if rid.replace("-", "").isalnum() and rid else uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return JSONResponse(_body(request, exc.status_code, exc.detail), status_code=exc.status_code,
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        fields: List[dict] = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            fields.append({"field": ".".join(loc), "message": str(err.get("msg", "Invalid value")),
                           "type": err.get("type", "")})
        body = _body(request, 422, "Some fields are invalid.")
        body["field_errors"] = fields
        body["detail"] = "Some fields are invalid."
        return JSONResponse(body, status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # Log type only: exception text may contain request content.
        log.error("unhandled %s request_id=%s", type(exc).__name__, request_id_of(request))
        return JSONResponse(_body(request, 500, "Something went wrong. Please try again."), status_code=500)
