"""Cliente do Gemini com saída JSON, retentativa, modelos de fallback e orçamento de tempo."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import lru_cache

from google import genai
from google.genai import errors, types

from ia import config

# O SDK usa httpx2 (ou httpx, conforme a versão); aceita o timeout de qualquer um dos dois.
_TIMEOUTS = []
for _nome in ("httpx2", "httpx"):
    try:
        _TIMEOUTS.append(__import__(_nome).TimeoutException)
    except ImportError:
        pass
EXCECOES_TIMEOUT = tuple(_TIMEOUTS) or (TimeoutError,)


class LLMIndisponivel(Exception):
    """Nenhum modelo respondeu: tentativas esgotadas ou orçamento de tempo estourado."""

    def __init__(self, tentativas: list[dict], motivo: str = "modelos_esgotados"):
        super().__init__(f"LLM indisponível ({motivo}) após {len(tentativas)} tentativas")
        self.tentativas = tentativas
        self.motivo = motivo


@dataclass
class RespostaLLM:
    texto: str
    modelo: str  # modelo pedido que respondeu (principal ou fallback)
    versao_modelo: str | None  # versão informada pela API
    tentativas: list[dict] = field(default_factory=list)


def modelos_em_ordem() -> list[str]:
    return list(dict.fromkeys([config.GEMINI_MODEL, *config.GEMINI_FALLBACK_MODELS]))


@lru_cache(maxsize=1)
def _cliente_padrao() -> genai.Client:
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não definida no .env")
    return genai.Client(
        api_key=config.GEMINI_API_KEY,
        # A retentativa é feita aqui, com regras próprias; a do SDK fica desligada.
        http_options=types.HttpOptions(
            timeout=config.TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1)
        ),
    )


def gerar_json(
    sistema: str,
    conteudo: list,
    schema: dict,
    *,
    modelos: list[str] | None = None,
    orcamento_s: float | None = None,
    cliente=None,
    dormir=time.sleep,
    relogio=time.monotonic,
) -> RespostaLLM:
    """Gera JSON validável pelo `schema`, com temperatura 0.

    `modelos`: ordem de tentativa; padrão = principal + fallbacks do .env. Passe um só
    modelo para desligar o fallback (avaliação). Erros fora de CODIGOS_RETENTAVEIS sobem
    para quem chamou. Sem resposta dentro do orçamento, levanta `LLMIndisponivel`.
    """
    cliente = cliente or _cliente_padrao()
    modelos = modelos or modelos_em_ordem()
    orcamento = config.ORCAMENTO_EXTRACAO_S if orcamento_s is None else orcamento_s
    inicio = relogio()

    def restante() -> float:
        return orcamento - (relogio() - inicio)

    tentativas: list[dict] = []
    for modelo in modelos:
        for espera in (*config.ESPERAS_RETENTATIVA, None):
            if restante() <= 0:
                raise LLMIndisponivel(tentativas, "orcamento_esgotado")
            cfg = types.GenerateContentConfig(
                system_instruction=sistema,
                temperature=config.TEMPERATURA,
                response_mime_type="application/json",
                response_json_schema=schema,
                # A chamada nunca passa do que sobra do orçamento.
                http_options=types.HttpOptions(timeout=int(min(config.TIMEOUT_MS, restante() * 1000))),
            )
            try:
                resposta = cliente.models.generate_content(model=modelo, contents=conteudo, config=cfg)
            except errors.APIError as erro:
                codigo = erro.code
                tentativas.append({"modelo": modelo, "codigo": codigo})
                if codigo not in config.CODIGOS_RETENTAVEIS | config.CODIGOS_TROCA_MODELO:
                    raise
            except EXCECOES_TIMEOUT:
                codigo = "timeout"
                tentativas.append({"modelo": modelo, "codigo": codigo})
            else:
                tentativas.append({"modelo": modelo, "codigo": 200})
                return RespostaLLM(resposta.text, modelo, getattr(resposta, "model_version", None), tentativas)

            if codigo in config.CODIGOS_TROCA_MODELO or espera is None:
                break  # 504/timeout ou tentativas esgotadas: passa ao próximo modelo
            if restante() <= espera:
                raise LLMIndisponivel(tentativas, "orcamento_esgotado")
            dormir(espera)
    raise LLMIndisponivel(tentativas, "modelos_esgotados")
