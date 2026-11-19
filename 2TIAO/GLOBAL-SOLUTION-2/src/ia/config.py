"""Configuração do LLM lida do .env na raiz do repositório."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

# Decisão de 17/11/2026: Flash-Lite como principal (100% de resposta nos testes do dia; os Flash
# 3.8 e 3.7 deram 503/504 em todas as chamadas). É o mesmo modelo avaliado e demonstrado.
MODELO_PADRAO = "gemini-3.5-flash-lite"
FALLBACK_PADRAO = "gemini-3.7-flash,gemini-3.8-flash"


def _lista(valor: str | None) -> list[str]:
    return [item.strip() for item in (valor or "").split(",") if item.strip()]


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or None
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or MODELO_PADRAO
# Usados em ordem quando o principal esgota as retentativas (429/500/503) ou dá 504/timeout.
GEMINI_FALLBACK_MODELS = _lista(os.getenv("GEMINI_FALLBACK_MODELS") or FALLBACK_PADRAO)

# Avaliação: um modelo fixo, sem fallback. Vazio = GEMINI_MODEL.
EVAL_MODEL = os.getenv("EVAL_MODEL") or GEMINI_MODEL

TEMPERATURA = 0.0
# Por modelo: 1 chamada + 1 retentativa após cada espera (segundos), só para estes códigos.
ESPERAS_RETENTATIVA = (2, 4, 8)
CODIGOS_RETENTAVEIS = frozenset({429, 500, 503})
# Estes passam direto ao próximo modelo, sem nova tentativa no mesmo: cada um já custou até
# TIMEOUT_MS e tende a se repetir ("timeout" = a chamada passou de TIMEOUT_MS sem resposta).
CODIGOS_TROCA_MODELO = frozenset({504, "timeout"})
TIMEOUT_MS = 30_000
# Teto de uma extração inteira, somando tentativas, esperas e fallbacks.
ORCAMENTO_EXTRACAO_S = 90
