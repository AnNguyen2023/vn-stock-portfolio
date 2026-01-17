from typing import Any, Optional
from fastapi.responses import JSONResponse
from core.schemas import ResponseEnvelope

def success(data: Any = None, meta: Optional[dict] = None) -> dict:
    """Returns a standardized success response compatible with ResponseEnvelope."""
    return ResponseEnvelope(ok=True, data=data, meta=meta).dict()

def fail(code: str, message: str, details: Optional[dict] = None, status_code: int = 400) -> JSONResponse:
    """Returns a standardized error response compatible with ResponseEnvelope."""
    content = ResponseEnvelope(
        ok=False,
        error={
            "code": code,
            "message": message,
            "details": details
        }
    ).dict()
    return JSONResponse(status_code=status_code, content=content)
