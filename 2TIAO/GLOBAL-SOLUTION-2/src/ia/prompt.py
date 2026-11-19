"""Carrega o prompt de extração versionado e monta o schema de resposta e o few-shot."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from google.genai import types

from ia.schemas import AlertaExtraido

PASTA_PROMPTS = Path(__file__).resolve().parent / "prompts"
VERSAO_PADRAO = "extracao_v1"

# Preenchidos pelo extrator (alerta_id, fonte) e pelo validador (status); o LLM não os gera.
CAMPOS_FORA_DO_LLM = ("alerta_id", "fonte_url", "fonte_hash", "status_extracao")

_EXEMPLO = re.compile(
    r"^## Exemplo \d+ — (?P<nome>\S+)\n.*?~~~text\n(?P<entrada>.*?)\n~~~.*?~~~json\n(?P<saida>.*?)\n~~~",
    re.S | re.M,
)


@dataclass(frozen=True)
class Exemplo:
    nome: str
    entrada: str
    saida: dict


@dataclass(frozen=True)
class Prompt:
    versao: str
    sistema: str
    exemplos: tuple[Exemplo, ...]


@lru_cache
def carregar_prompt(versao: str = VERSAO_PADRAO) -> Prompt:
    texto = (PASTA_PROMPTS / f"{versao}.md").read_text(encoding="utf-8")
    sistema = texto.split("\n## Sistema\n", 1)[1].split("\n## Exemplo ", 1)[0].strip()
    exemplos = tuple(
        Exemplo(m["nome"], m["entrada"], json.loads(m["saida"])) for m in _EXEMPLO.finditer(texto)
    )
    return Prompt(versao, sistema, exemplos)


def formatar_entrada(texto: str) -> str:
    return f"Texto oficial do alerta:\n\n{texto.strip()}"


def montar_conteudo(texto: str, prompt: Prompt) -> list[types.Content]:
    """Few-shot como conversa: cada exemplo vira (usuário: texto) → (modelo: JSON)."""
    conteudo = []
    for exemplo in prompt.exemplos:
        conteudo.append(types.Content(role="user", parts=[types.Part(text=formatar_entrada(exemplo.entrada))]))
        conteudo.append(types.Content(
            role="model", parts=[types.Part(text=json.dumps(exemplo.saida, ensure_ascii=False))]
        ))
    conteudo.append(types.Content(role="user", parts=[types.Part(text=formatar_entrada(texto))]))
    return conteudo


def _resolver(no, defs):
    if isinstance(no, dict):
        if "$ref" in no:
            return _resolver(defs[no["$ref"].rsplit("/", 1)[1]], defs)
        return {k: _resolver(v, defs) for k, v in no.items() if k not in ("title", "default")}
    if isinstance(no, list):
        return [_resolver(item, defs) for item in no]
    return no


@lru_cache
def schema_resposta() -> dict:
    """JSON Schema da resposta do LLM, gerado do modelo Pydantic do formato 1.

    Sem $ref, sem os campos preenchidos fora do LLM e com todos os campos obrigatórios:
    o modelo precisa declarar `null` explicitamente em vez de omitir.
    """
    bruto = AlertaExtraido.model_json_schema()
    item = _resolver(bruto, bruto.pop("$defs", {}))
    for campo in CAMPOS_FORA_DO_LLM:
        item["properties"].pop(campo)
    item["required"] = list(item["properties"])
    regra = item["properties"]["regra_lote"]
    regra["required"] = list(regra["properties"])
    return {
        "type": "object",
        "properties": {"alertas": {"type": "array", "items": item}},
        "required": ["alertas"],
        "additionalProperties": False,
    }
