"""Extrator de alertas: texto oficial → lista de AlertaExtraido (formato 1).

O LLM só extrai. Qualquer falha (serviço, orçamento, JSON inválido, item fora do schema)
vira alerta em `verificacao_pendente` com o motivo em `campos_pendentes`; nada sobe
como exceção para quem chama.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field

from pydantic import ValidationError

from ia import gemini
from ia.prompt import VERSAO_PADRAO, carregar_prompt, montar_conteudo, schema_resposta
from ia.schemas import HASH_RE, AlertaExtraido, fonte_oficial

log = logging.getLogger(__name__)

# Dados pessoais mascarados antes do envio ao LLM. Só padrões com pontuação, para não
# confundir com lotes e CNPJs (ex.: o lote 13099022444 tem 11 dígitos, como um CPF).
_DADOS_PESSOAIS = [
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "[CPF]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"\(\d{2}\)\s?9?\d{4}-?\d{4}\b"), "[TELEFONE]"),
]


@dataclass
class ResultadoExtracao:
    alertas: list[AlertaExtraido]
    modelo: str | None = None  # modelo que efetivamente respondeu
    versao_modelo: str | None = None
    prompt: str = VERSAO_PADRAO
    motivo_falha: str | None = None  # None = o LLM respondeu e o JSON foi lido
    fonte_recusada: str | None = None  # URL recusada quando motivo_falha == "fonte_nao_oficial"
    tentativas: list[dict] = field(default_factory=list)
    duracao_s: float = 0.0


def mascarar_dados_pessoais(texto: str) -> str:
    for padrao, marcador in _DADOS_PESSOAIS:
        texto = padrao.sub(marcador, texto)
    return texto


def _slug(texto: str | None, limite: int = 40) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")[:limite].strip("-") or "sem-nome"


def _alerta_pendente(motivo: str, fonte_url: str, fonte_hash: str | None, dados: dict | None = None) -> AlertaExtraido:
    """Alerta mínimo para revisão humana quando a extração não pôde ser concluída."""
    dados = dados or {}

    def texto(campo):
        valor = dados.get(campo)
        return valor if isinstance(valor, str) else None

    return AlertaExtraido(
        alerta_id="pendente",
        fonte_url=fonte_url,
        fonte_hash=fonte_hash,
        produto=texto("produto"),
        marca=texto("marca"),
        fabricante=texto("fabricante"),
        cnpj=texto("cnpj"),
        regra_lote={"tipo": None},
        campos_pendentes=[f"extracao:{motivo}"],
    )


def _atribuir_ids(alertas: list[AlertaExtraido], fonte_url: str) -> list[AlertaExtraido]:
    """alerta_id determinístico: marca (ou fabricante) + produto + 6 hex da URL; único na chamada."""
    sufixo = hashlib.sha256(fonte_url.encode()).hexdigest()[:6]
    vistos: dict[str, int] = {}
    for alerta in alertas:
        base = f"{_slug(alerta.marca or alerta.fabricante, 20)}-{_slug(alerta.produto)}-{sufixo}"
        vistos[base] = vistos.get(base, 0) + 1
        alerta.alerta_id = base if vistos[base] == 1 else f"{base}-{vistos[base]}"
    return alertas


def _ler_resposta(texto_json: str, fonte_url: str, fonte_hash: str | None) -> tuple[list[AlertaExtraido], str | None]:
    try:
        itens = json.loads(texto_json)["alertas"]
        if not isinstance(itens, list):
            raise TypeError("'alertas' não é lista")
    except (json.JSONDecodeError, KeyError, TypeError) as erro:
        log.warning("resposta do LLM ilegível: %s", erro)
        return [_alerta_pendente("json_invalido", fonte_url, fonte_hash)], "json_invalido"

    if not itens:
        # Texto vindo de fonte de recolhimento sem nenhum produto: na dúvida, revisão humana.
        return [_alerta_pendente("nenhum_alerta_extraido", fonte_url, fonte_hash)], None

    alertas = []
    for item in itens:
        try:
            dados = {**item, "alerta_id": "provisorio", "fonte_url": fonte_url, "fonte_hash": fonte_hash}
            alertas.append(AlertaExtraido.model_validate(dados))
        except (ValidationError, TypeError) as erro:
            log.warning("item do LLM fora do schema: %s", erro)
            alertas.append(_alerta_pendente("item_invalido", fonte_url, fonte_hash, item if isinstance(item, dict) else None))
    return alertas, None


def extrair_alertas_detalhado(
    texto: str,
    fonte_url: str,
    fonte_hash: str | None = None,
    *,
    modelos: list[str] | None = None,
    versao_prompt: str = VERSAO_PADRAO,
    gerador=gemini.gerar_json,
) -> ResultadoExtracao:
    """Como `extrair_alertas`, devolvendo também modelo, tentativas e motivo de falha."""
    inicio = time.monotonic()
    resultado = ResultadoExtracao(alertas=[], prompt=versao_prompt)
    try:
        if not isinstance(fonte_url, str) or not fonte_oficial(fonte_url):
            # Fonte não oficial não gera alerta nenhum, nem pendente (governança da fonte).
            resultado.motivo_falha = "fonte_nao_oficial"
            resultado.fonte_recusada = str(fonte_url)
            return resultado
        if fonte_hash is not None and not (isinstance(fonte_hash, str) and HASH_RE.match(fonte_hash)):
            resultado.alertas = [_alerta_pendente("fonte_hash_invalido", fonte_url, None)]
            resultado.motivo_falha = "fonte_hash_invalido"
            return resultado
        if not isinstance(texto, str) or not texto.strip():
            resultado.alertas = [_alerta_pendente("texto_vazio", fonte_url, fonte_hash)]
            resultado.motivo_falha = "texto_vazio"
            return resultado

        prompt = carregar_prompt(versao_prompt)
        try:
            resposta = gerador(
                prompt.sistema,
                montar_conteudo(mascarar_dados_pessoais(texto), prompt),
                schema_resposta(),
                modelos=modelos,
            )
        except gemini.LLMIndisponivel as erro:
            resultado.tentativas, resultado.motivo_falha = erro.tentativas, erro.motivo
        except Exception as erro:  # noqa: BLE001 — contrato: nunca levantar para quem chama
            log.warning("falha ao chamar o LLM: %s", type(erro).__name__)
            resultado.motivo_falha = f"erro_llm:{type(erro).__name__}"
        else:
            resultado.modelo, resultado.versao_modelo = resposta.modelo, resposta.versao_modelo
            resultado.tentativas = resposta.tentativas
            resultado.alertas, resultado.motivo_falha = _ler_resposta(resposta.texto, fonte_url, fonte_hash)

        if resultado.motivo_falha and not resultado.alertas:
            resultado.alertas = [_alerta_pendente(resultado.motivo_falha, fonte_url, fonte_hash)]
        resultado.alertas = _atribuir_ids(resultado.alertas, fonte_url)
        return resultado
    except Exception as erro:  # noqa: BLE001 — última barreira
        log.exception("falha inesperada no extrator")
        resultado.motivo_falha = f"erro_interno:{type(erro).__name__}"
        try:
            resultado.alertas = _atribuir_ids([_alerta_pendente("erro_interno", fonte_url, None)], fonte_url)
        except Exception:  # noqa: BLE001 — ex.: fonte_url inválida; não há alerta possível
            resultado.alertas = []
        return resultado
    finally:
        resultado.duracao_s = round(time.monotonic() - inicio, 2)


def main(argv: list[str] | None = None) -> None:
    """Uso (na pasta src/): python -m ia.extrator ARQUIVO.txt --url URL_OFICIAL [--hash sha256:...]"""
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Extrai os alertas de um texto oficial (formato 1).")
    parser.add_argument("arquivo", type=Path)
    parser.add_argument("--url", required=True, help="fonte oficial (*.gov.br ou *.datalegis.net)")
    parser.add_argument("--hash", default=None, help="sha256:<64 hex> do texto bruto, se houver")
    args = parser.parse_args(argv)
    r = extrair_alertas_detalhado(args.arquivo.read_text(encoding="utf-8"), args.url, args.hash)
    print(json.dumps({
        "modelo": r.modelo, "versao_modelo": r.versao_modelo, "motivo_falha": r.motivo_falha,
        "fonte_recusada": r.fonte_recusada, "duracao_s": r.duracao_s,
        "alertas": [a.model_dump(mode="json") for a in r.alertas],
    }, ensure_ascii=False, indent=2))


def extrair_alertas(texto: str, fonte_url: str, fonte_hash: str | None = None) -> list[AlertaExtraido]:
    """Interface para o pipeline: texto oficial → alertas do formato 1. Nunca levanta exceção.

    Fonte fora de *.gov.br / *.datalegis.net → lista vazia. Falha de extração → um alerta
    em `verificacao_pendente` com `extracao:<motivo>` em `campos_pendentes`.
    """
    return extrair_alertas_detalhado(texto, fonte_url, fonte_hash).alertas


if __name__ == "__main__":
    main()
