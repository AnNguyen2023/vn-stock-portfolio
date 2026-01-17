from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class ResponseEnvelope(BaseModel, Generic[T]):
    ok: bool
    data: Optional[T] = None
    error: Optional[Any] = None
    meta: Optional[dict] = None
