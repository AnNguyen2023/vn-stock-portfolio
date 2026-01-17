from typing import Any, Optional
from core.schemas import ResponseEnvelope

def success(data: Any = None, meta: dict = None) -> ResponseEnvelope:
    return ResponseEnvelope(
        ok=True,
        data=data,
        meta=meta
    )

def fail(code: str, message: str, details: Any = None, status_code: int = 400) -> ResponseEnvelope:
    from fastapi.responses import JSONResponse
    from fastapi.encoders import jsonable_encoder
    
    content = ResponseEnvelope(
        ok=False,
        error={
            "code": code,
            "message": message,
            "details": details
        }
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content)
    )
