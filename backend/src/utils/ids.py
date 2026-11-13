"""路径参数里的 UUID 归一化。

`db.get(Model, "not-a-uuid")` 会让 psycopg 抛 `invalid input syntax for type uuid`（HTTP 500）；
但业务语义上「id 不合法」和「id 不存在」都应当是 404。这里统一先解析，解析失败由调用方走 not_found。
"""
from __future__ import annotations

import uuid


def parse_uuid(value) -> uuid.UUID | None:
    """合法 UUID（str/UUID）-> UUID；非法或缺失 -> None。"""
    if isinstance(value, uuid.UUID):
        return value
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None
