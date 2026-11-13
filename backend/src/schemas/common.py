"""通用返回结构。"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageMeta(BaseModel):
    total: int = 0
    returned: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


class AckResponse(BaseModel):
    ok: bool = True
    message: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)
