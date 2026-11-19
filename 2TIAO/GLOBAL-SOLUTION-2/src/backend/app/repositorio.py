from __future__ import annotations

from typing import Any


alertas: list[dict[str, Any]] = []
matches: list[dict[str, Any]] = []


def limpar_dados() -> None:
    alertas.clear()
    matches.clear()


def adicionar_alerta(alerta: dict[str, Any]) -> None:
    alertas.append(alerta)


def adicionar_match(match: dict[str, Any]) -> None:
    matches.append(match)


def buscar_match(match_id: str) -> dict[str, Any] | None:
    for match in matches:
        if match.get("match_id") == match_id:
            return match

    return None