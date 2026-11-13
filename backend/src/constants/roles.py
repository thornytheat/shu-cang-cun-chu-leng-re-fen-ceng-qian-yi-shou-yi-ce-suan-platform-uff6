"""RBAC 角色常量。

前后端必须一致：users.role / src/constants/roles.py / frontend/src/constants/roles.ts
角色：admin 平台负责人｜analyst 数据开发｜viewer 财务与报表 owner（只读）。
"""
from __future__ import annotations

ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"
ROLE_VIEWER = "viewer"

ALL_ROLES: tuple[str, ...] = (ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER)

# 能力矩阵：action -> 允许的角色
PERMISSIONS: dict[str, tuple[str, ...]] = {
    "tables:read": ALL_ROLES,
    "tables:recompute": (ROLE_ADMIN, ROLE_ANALYST),
    "policies:read": ALL_ROLES,
    "policies:write": (ROLE_ADMIN,),
    "trial:run": (ROLE_ADMIN, ROLE_ANALYST),
    "plans:read": ALL_ROLES,
    "plans:write": (ROLE_ADMIN, ROLE_ANALYST),
    "plans:submit": (ROLE_ADMIN, ROLE_ANALYST),
    "plans:export": (ROLE_ADMIN, ROLE_ANALYST),
    "audit:read": (ROLE_ADMIN,),
}

ROLE_LABELS: dict[str, str] = {
    ROLE_ADMIN: "平台负责人",
    ROLE_ANALYST: "数据开发",
    ROLE_VIEWER: "财务 / 报表 owner（只读）",
}


def role_can(role: str, action: str) -> bool:
    return role in PERMISSIONS.get(action, ())


def role_permissions(role: str) -> list[str]:
    return [action for action, roles in PERMISSIONS.items() if role in roles]
