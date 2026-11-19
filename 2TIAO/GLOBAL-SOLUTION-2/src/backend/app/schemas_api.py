from typing import Any, Literal

from pydantic import BaseModel


class DecisaoMatch(BaseModel):
    decisao: Literal["confirmado", "rejeitado"]
    responsavel: str
    motivo: str | None = None


class ProcessamentoMotor(BaseModel):
    alerta: dict[str, Any]
    recebimentos: list[dict[str, Any]]


class ColetaAlerta(BaseModel):
    texto: str
    fonte_url: str
    fonte_hash: str | None = None