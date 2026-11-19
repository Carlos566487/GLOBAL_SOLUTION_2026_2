"""Modelos Pydantic dos formatos 1 (alerta extraído) e 5 (leitura da embalagem), contrato v2.

Os formatos 2, 3, 4, 6 e 7 pertencem a outros papéis e não ficam aqui.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

DOMINIOS_OFICIAIS = ("gov.br", "datalegis.net")
LIMITE_CONFIANCA_OCR = 0.8
CNPJ_RE = re.compile(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# Campos de identidade cujo nulo bloqueia o match (critério do golden set: JMS sem marca,
# Granoro/Militão/D'Viez sem CNPJ). `fabricante` nulo só é registrado.
CAMPOS_DECISIVOS = ("produto", "marca", "cnpj")


def normalizar_lote(lote: str | None) -> str | None:
    """Normalização do contrato: strip + upper. Vazio vira None. Nada além disso."""
    if lote is None:
        return None
    lote = lote.strip().upper()
    return lote or None


def fonte_oficial(url: str) -> bool:
    """Aceita só *.gov.br e *.datalegis.net (http/https)."""
    partes = urlparse(url)
    host = (partes.hostname or "").lower()
    return partes.scheme in ("http", "https") and any(
        host == d or host.endswith("." + d) for d in DOMINIOS_OFICIAIS
    )


def _vazio_para_none(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


# ---------------------------------------------------------------------------
# Formato 1 — Alerta extraído
# ---------------------------------------------------------------------------

class RegraLote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["lista", "sufixo", "data_corte", "todos"] | None
    lotes: list[StrictStr] = Field(default_factory=list)
    sufixo: StrictStr | None = None
    fabricado_ate: date | None = None

    @field_validator("lotes")
    @classmethod
    def _limpar_lotes(cls, lotes: list[str]) -> list[str]:
        # Só remove espaços das pontas e descarta vazios; o texto do lote é preservado.
        return [lote.strip() for lote in lotes if lote.strip()]

    @field_validator("sufixo", mode="before")
    @classmethod
    def _sufixo_vazio(cls, v):
        return _vazio_para_none(v)


class AlertaExtraido(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alerta_id: StrictStr = Field(min_length=1)
    fonte_url: StrictStr
    fonte_hash: StrictStr | None = None
    produto: StrictStr | None
    marca: StrictStr | None
    fabricante: StrictStr | None
    cnpj: StrictStr | None
    escopo: Literal["produto", "categoria_fabricante"] = "produto"
    categoria: StrictStr | None = None
    regra_lote: RegraLote
    status_extracao: Literal["ok", "verificacao_pendente"] = "ok"
    campos_pendentes: list[StrictStr] = Field(default_factory=list)

    @field_validator("produto", "marca", "fabricante", "cnpj", "categoria", mode="before")
    @classmethod
    def _texto_vazio(cls, v):
        return _vazio_para_none(v)

    @field_validator("fonte_url")
    @classmethod
    def _fonte_oficial(cls, url: str) -> str:
        if not fonte_oficial(url):
            raise ValueError("fonte não oficial: só *.gov.br e *.datalegis.net são aceitos")
        return url

    @field_validator("fonte_hash")
    @classmethod
    def _formato_hash(cls, v: str | None) -> str | None:
        if v is not None and not HASH_RE.match(v):
            raise ValueError("fonte_hash deve ser 'sha256:' + 64 hex minúsculos")
        return v

    @model_validator(mode="after")
    def _calcular_pendencias(self) -> "AlertaExtraido":
        """Recalcula campos_pendentes e status de forma determinística.

        Mantém as pendências já informadas (ex.: ambiguidade apontada pelo extrator) e
        acrescenta as que o próprio contrato exige. O status nunca contradiz a lista.
        """
        pendentes = list(dict.fromkeys(self.campos_pendentes))

        def marcar(campo: str) -> None:
            if campo not in pendentes:
                pendentes.append(campo)

        for campo in CAMPOS_DECISIVOS:
            if getattr(self, campo) is None:
                marcar(campo)
        if self.cnpj is not None and not CNPJ_RE.match(self.cnpj):
            marcar("cnpj")
        if self.escopo == "categoria_fabricante" and self.categoria is None:
            marcar("categoria")

        regra = self.regra_lote
        if regra.tipo is None:
            marcar("regra_lote.tipo")
        elif regra.tipo == "lista" and not regra.lotes:
            marcar("regra_lote.lotes")
        elif regra.tipo == "sufixo" and regra.sufixo is None:
            marcar("regra_lote.sufixo")
        elif regra.tipo == "data_corte" and regra.fabricado_ate is None:
            marcar("regra_lote.fabricado_ate")

        # Extrator marcou pendente sem dizer o motivo: na dúvida, continua pendente.
        if self.status_extracao == "verificacao_pendente" and not pendentes:
            marcar("revisao_manual")

        self.campos_pendentes = pendentes
        self.status_extracao = "verificacao_pendente" if pendentes else "ok"
        return self


# ---------------------------------------------------------------------------
# Formato 5 — Leitura da embalagem
# ---------------------------------------------------------------------------

class LeituraEmbalagem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ean: StrictStr | None
    produto: StrictStr | None
    marca: StrictStr | None
    lote: StrictStr | None
    data_fabricacao: date | None
    validade: date | None
    confianca_ocr: float = Field(ge=0.0, le=1.0)

    @field_validator("ean", "produto", "marca", "lote", mode="before")
    @classmethod
    def _texto_vazio(cls, v):
        return _vazio_para_none(v)

    @field_validator("ean")
    @classmethod
    def _ean_numerico(cls, v: str | None) -> str | None:
        if v is not None and not (v.isdigit() and len(v) in (8, 12, 13, 14)):
            raise ValueError("ean deve ter 8, 12, 13 ou 14 dígitos")
        return v

    @property
    def produto_identificado(self) -> bool:
        """EAN lido, ou produto e marca lidos juntos."""
        return self.ean is not None or (self.produto is not None and self.marca is not None)

    def pendencias(self, tipo_regra: str | None = None) -> list[str]:
        """Motivos que levam a `verificacao_pendente`. Lista vazia = dados suficientes.

        `tipo_regra` é o tipo do alerta candidato: `data_corte` exige a data de fabricação
        (a validade não substitui), `lista`/`sufixo` exigem o lote.
        """
        motivos = []
        if self.confianca_ocr < LIMITE_CONFIANCA_OCR:
            motivos.append("confianca_ocr")
        if not self.produto_identificado:
            motivos.append("produto")
        if tipo_regra in ("lista", "sufixo") and self.lote is None:
            motivos.append("lote")
        if tipo_regra == "data_corte" and self.data_fabricacao is None:
            motivos.append("data_fabricacao")
        return motivos
