from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComputeRoute:
    queue: str
    priority: int
    label: str


ROUTES = {
    "interactive": ComputeRoute("interactive", 9, "Интерактивная инженерная задача"),
    "heavy": ComputeRoute("heavy", 6, "Тяжёлая инженерная задача"),
    "background": ComputeRoute("background", 1, "Фоновая задача"),
    "default": ComputeRoute("default", 4, "Обычная задача"),
}


def route_for(kind: str) -> ComputeRoute:
    return ROUTES.get(kind, ROUTES["default"])


def can_view_job(owner: str, current_user: str, is_admin: bool) -> bool:
    return bool(is_admin or owner == current_user)
