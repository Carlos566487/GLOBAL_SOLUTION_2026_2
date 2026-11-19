"""Regras de comparação da avaliação do extrator (funções puras, sem LLM)."""
from __future__ import annotations

import re
import unicodedata

CAMPOS_IDENTIDADE = ("produto", "marca", "fabricante", "cnpj")
CAMPOS_AVALIADOS = ("regra", *CAMPOS_IDENTIDADE)  # escopo e categoria fora até a PO atualizar o gabarito

LIMIAR_PAREAMENTO = 0.3  # similaridade mínima de produto para parear
MARGEM_AMBIGUIDADE = 0.05  # candidatos com similaridade a menos disso do melhor = ambíguo

MOTIVOS_SERVICO = ("orcamento_esgotado", "modelos_esgotados")


def falha_de_servico(motivo: str | None) -> bool:
    """O modelo não respondeu: não é erro de extração."""
    return bool(motivo) and (motivo in MOTIVOS_SERVICO or motivo.startswith("erro_llm:"))


# --- normalização ------------------------------------------------------------

def norm_texto(valor: str | None) -> str | None:
    """Minúsculas, sem acento, sem pontuação, espaço padronizado (inclui separar número de unidade: 800g → 800 g)."""
    if valor is None:
        return None
    # Tira só os acentos; qualquer outro símbolo (inclusive "–") vira espaço, sem colar palavras.
    valor = "".join(c for c in unicodedata.normalize("NFKD", valor) if not unicodedata.combining(c)).lower()
    valor = re.sub(r"[^a-z0-9]+", " ", valor)
    valor = re.sub(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)", " ", valor)
    return " ".join(valor.split()) or None


def norm_fabricante(valor: str | None) -> str | None:
    """Como norm_texto, removendo antes as anotações entre parênteses (ex.: "(Bausch Lomb)")."""
    if valor is None:
        return None
    return norm_texto(re.sub(r"\([^)]*\)", " ", valor))


def digitos(valor: str | None) -> str | None:
    if valor is None:
        return None
    return "".join(c for c in valor if c.isdigit()) or None


def chave_lote(lote: str) -> str:
    """Chave de comparação de lote na avaliação: sem nenhum espaço + upper ("183/3 B" = "183/3B")."""
    return re.sub(r"\s+", "", lote).upper()


# --- comparação --------------------------------------------------------------

def comparar_regra(gabarito: dict, extraido: dict) -> bool:
    tipo = gabarito.get("tipo")
    if tipo != extraido.get("tipo"):
        return False
    if tipo == "lista":
        return {chave_lote(l) for l in gabarito["lotes"]} == {chave_lote(l) for l in extraido["lotes"]}
    if tipo == "sufixo":
        return chave_lote(gabarito["sufixo"] or "") == chave_lote(extraido["sufixo"] or "")
    if tipo == "data_corte":
        return gabarito["fabricado_ate"] == extraido["fabricado_ate"]
    return True  # todos / null: o tipo basta


def comparar_registro(gabarito: dict, extraido: dict) -> dict[str, bool]:
    return {
        "regra": comparar_regra(gabarito["regra_lote"], extraido["regra_lote"]),
        "produto": norm_texto(gabarito["produto"]) == norm_texto(extraido["produto"]),
        "marca": norm_texto(gabarito["marca"]) == norm_texto(extraido["marca"]),
        "fabricante": norm_fabricante(gabarito["fabricante"]) == norm_fabricante(extraido["fabricante"]),
        "cnpj": digitos(gabarito["cnpj"]) == digitos(extraido["cnpj"]),
    }


def valor_no_texto(campo: str, gabarito: dict, texto: str) -> bool:
    """Diagnóstico: o valor do gabarito para `campo` pode ser lido no texto de entrada?

    Não muda a acurácia; separa erro do extrator de dado que a PO trouxe de outra fonte (ex.: RE).
    """
    if campo == "status":
        return True
    if campo == "regra":
        regra = gabarito["regra_lote"]
        compacto = chave_lote(texto)
        if regra["tipo"] == "lista":
            return all(chave_lote(l) in compacto for l in regra["lotes"])
        if regra["tipo"] == "todos":
            return "todos" in (norm_texto(texto) or "").split()
        if regra["tipo"] == "data_corte":
            ano, mes, dia = regra["fabricado_ate"].split("-")
            return f"{dia}/{mes}/{ano}" in texto
        return True
    valor = gabarito[campo]
    if valor is None:
        return True
    if campo == "cnpj":
        return digitos(valor) in (digitos(texto) or "")
    normal = norm_fabricante if campo == "fabricante" else norm_texto
    return f" {normal(valor)} " in f" {norm_texto(texto)} "


# --- pareamento --------------------------------------------------------------

def similaridade(a: str | None, b: str | None) -> float:
    """Jaccard dos tokens normalizados do produto."""
    ta, tb = set((norm_texto(a) or "").split()), set((norm_texto(b) or "").split())
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def _cnpj_compativel(a: str | None, b: str | None) -> bool:
    da, db = digitos(a), digitos(b)
    return da is None or db is None or da == db


def parear(gabarito: list[dict], extraidos: list[dict]) -> tuple[dict[int, tuple[int, float]], list[str]]:
    """Pareia cada registro do gabarito com no máximo um alerta extraído do mesmo texto.

    Critério: produto normalizado (similaridade de tokens ≥ LIMIAR_PAREAMENTO) + CNPJ
    compatível (mesmos dígitos, ou um dos lados nulo). Atribuição gulosa pela maior
    similaridade. Lotes NÃO entram no pareamento, para não favorecer a métrica da regra.
    Devolve {índice_gabarito: (índice_extraído, similaridade)} e as notas de ambiguidade.
    """
    candidatos = sorted(
        (
            (similaridade(g["produto"], e["produto"]), gi, ei)
            for gi, g in enumerate(gabarito)
            for ei, e in enumerate(extraidos)
            if _cnpj_compativel(g["cnpj"], e["cnpj"])
        ),
        key=lambda c: (-c[0], c[1], c[2]),
    )
    candidatos = [c for c in candidatos if c[0] >= LIMIAR_PAREAMENTO]

    pares: dict[int, tuple[int, float]] = {}
    usados: set[int] = set()
    for score, gi, ei in candidatos:
        if gi not in pares and ei not in usados:
            pares[gi] = (ei, score)
            usados.add(ei)

    ambiguos = []
    for gi, (ei, score) in pares.items():
        rivais = [e for s, g, e in candidatos if g == gi and e != ei and score - s < MARGEM_AMBIGUIDADE]
        if rivais:
            ambiguos.append(
                f"{gabarito[gi]['alerta_id']}: pareado com o extraído #{ei} (sim. {score:.2f}); "
                f"rival(is) #{', #'.join(map(str, rivais))} a menos de {MARGEM_AMBIGUIDADE}"
            )
    return pares, ambiguos


# --- suporte no texto (revisão manual) ---------------------------------------

def trecho_de_suporte(alerta: dict, texto: str, limite: int = 300) -> str | None:
    """Linha do texto que sustenta o alerta: contém um dos lotes, ou ≥ 60% das palavras do produto."""
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    lotes = [chave_lote(l) for l in (alerta.get("regra_lote") or {}).get("lotes") or []]
    for linha in linhas:
        if any(lote in chave_lote(linha) for lote in lotes):
            return linha[:limite]
    tokens = set((norm_texto(alerta.get("produto")) or "").split())
    if tokens:
        melhor = max(linhas, key=lambda l: len(tokens & set((norm_texto(l) or "").split())), default="")
        if len(tokens & set((norm_texto(melhor) or "").split())) / len(tokens) >= 0.6:
            return melhor[:limite]
    return None
