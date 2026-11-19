"""Leitor da embalagem: foto (bytes) → LeituraEmbalagem (formato 5).

Tudo roda localmente: OpenCV (pré-processamento) + EasyOCR (texto) + pyzbar (código de barras).
A imagem só existe em memória durante a chamada: não é salva, não é logada e não vai para o LLM.
O texto lido pelo OCR também não é logado (pode conter dado pessoal incidental).
"""
from __future__ import annotations

import logging
import re
from datetime import date
from functools import lru_cache
from typing import Callable, Mapping

import cv2
import numpy as np

from ia.schemas import LeituraEmbalagem

log = logging.getLogger(__name__)

# Saída do OCR: [(caixa, texto, confiança)], como em easyocr.Reader.readtext.
LeitorOCR = Callable[[np.ndarray], list]

_DATA = r"(\d{2})\s*[/.\-]\s*(\d{2})\s*[/.\-]\s*(\d{4}|\d{2})\b"

# Convenção de lote (a mesma do gabarito das fotos; ver docs/interface_ia.md):
# 1. Marcador "L", "L:" ou "L." (também "LOTE"/"LOT" com valor na mesma linha). "L" só é marcador
#    seguido de ":" ou "." ou de um dígito ("L029"); "LJA..." não é marcador.
# 2. O lote é o texto logo após o marcador, na mesma linha, até a primeira hora (HH:MM), data
#    ou fim da linha, sem o marcador. Espaços internos são preservados. Também para no rótulo de
#    outro campo como palavra inteira (VAL, FAB, VENC, EMP); "VAL200127" dentro do código não para.
# 3. Sem marcador com valor, mas com o rótulo "Lote" (ex.: "Validade/Lote:"), o lote é a primeira
#    linha seguinte com dígito que não tem data/hora nem rótulo de outro campo, inteira.
RE_MARCADOR_LOTE = re.compile(r"\bLOTE(?![A-Z])\s*[:.\-]?\s*|\bLOT(?![A-Z])\s*[:.\-]?\s*|\bL\s*[:.]\s*|\bL\s*(?=\d)")
RE_ROTULO_LOTE = re.compile(r"\bLOTE(?![A-Z])")
RE_HORA_OU_DATA = re.compile(
    r"(?:^|(?<=\s))(?:\d{1,2}:\d{2}\b|\d{2}[/.\-]\d{2}(?:[/.\-]\d{2,4})?\b|[A-Z]{3}/\d{2,4}\b|\d{2}/\d{4}\b)")
RE_OUTRO_CAMPO = re.compile(r"\b(?:VAL|VALIDADE|FAB|FABRICA[ÇC][ÃA]O|FABRICADO|VENC|VENCIMENTO|EMP)\b")
RE_FAB = re.compile(r"(?:\bFAB(?:RICA[ÇC][ÃA]O|RICADO(?:\s+EM)?)?\b\.?|\bF\s*[:.])\s*[:.]?\s*" + _DATA)
RE_VAL = re.compile(r"(?:\bVAL(?:IDADE)?\b\.?|\bVENC(?:IMENTO)?\b\.?|\bV\s*[:.])\s*[:.]?\s*" + _DATA)
TIPOS_EAN = {"EAN13", "EAN8", "UPCA"}


@lru_cache(maxsize=1)
def _easyocr():
    import easyocr  # import tardio: só carrega o PyTorch quando o OCR é usado

    return easyocr.Reader(["pt", "en"], gpu=False, verbose=False)


def leitor_padrao(imagem: np.ndarray) -> list:
    return _easyocr().readtext(imagem)


# --- código de barras --------------------------------------------------------

def ean_valido(codigo: str) -> bool:
    """Dígito verificador GS1 (EAN-8, UPC-A, EAN-13, GTIN-14)."""
    if not (codigo.isdigit() and len(codigo) in (8, 12, 13, 14)):
        return False
    corpo, dv = codigo[:-1], int(codigo[-1])
    soma = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(corpo)))
    return (10 - soma % 10) % 10 == dv


def ler_ean(cinza: np.ndarray) -> str | None:
    """Lê o código de barras. Nenhum ou mais de um EAN distinto → None (identificação insegura)."""
    from pyzbar import pyzbar

    lidos = set()
    for variante in (cinza, cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]):
        for simbolo in pyzbar.decode(variante):
            codigo = simbolo.data.decode("ascii", "ignore")
            if simbolo.type in TIPOS_EAN and ean_valido(codigo):
                lidos.add(codigo)
        if lidos:
            break
    return lidos.pop() if len(lidos) == 1 else None


# --- OCR ---------------------------------------------------------------------

def preprocessar(cinza: np.ndarray) -> np.ndarray:
    """Redimensiona para o lado maior entre 1000 e 2000 px e realça o contraste (CLAHE)."""
    lado = max(cinza.shape[:2])
    if lado < 1000 or lado > 2000:
        escala = (1000 if lado < 1000 else 2000) / lado
        cinza = cv2.resize(cinza, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(cinza)


def agrupar_linhas(resultado: list) -> list[tuple[str, float]]:
    """Junta as caixas do OCR em linhas (por altura), da esquerda para a direita.

    Cada linha leva a menor confiança entre suas caixas.
    """
    caixas = []
    for caixa, texto, conf in resultado:
        ys = [p[1] for p in caixa]
        xs = [p[0] for p in caixa]
        caixas.append(((min(ys) + max(ys)) / 2, max(ys) - min(ys), min(xs), texto, float(conf)))
    caixas.sort(key=lambda c: (c[0], c[2]))
    linhas: list[list] = []
    for caixa in caixas:
        if linhas and abs(caixa[0] - linhas[-1][0][0]) < 0.5 * max(caixa[1], linhas[-1][0][1]):
            linhas[-1].append(caixa)
        else:
            linhas.append([caixa])
    return [
        (" ".join(c[3] for c in sorted(linha, key=lambda c: c[2])), min(c[4] for c in linha))
        for linha in linhas
    ]


def _data(m: re.Match | None) -> date | None:
    if not m:
        return None
    dia, mes, ano = (int(g) for g in m.groups())
    try:
        return date(2000 + ano if ano < 100 else ano, mes, dia)
    except ValueError:
        return None


def _cortar_lote(resto: str) -> str | None:
    """Corta o texto após o marcador na primeira hora/data ou rótulo de outro campo."""
    fim = len(resto)
    for regex in (RE_HORA_OU_DATA, RE_OUTRO_CAMPO):
        if m := regex.search(resto):
            fim = min(fim, m.start())
    return resto[:fim].strip(" :.-") or None


def ler_lote(linhas: list[tuple[str, float]]) -> tuple[str | None, float | None]:
    """Aplica a convenção de lote às linhas (já em maiúsculas). Devolve (lote, confiança da linha)."""
    for texto, conf in linhas:
        for m in RE_MARCADOR_LOTE.finditer(texto):
            if lote := _cortar_lote(texto[m.end():]):
                return lote, conf
    for i, (texto, _) in enumerate(linhas):
        if RE_ROTULO_LOTE.search(texto):
            for seguinte, conf in linhas[i + 1:]:
                if (any(c.isdigit() for c in seguinte) and not RE_HORA_OU_DATA.search(seguinte)
                        and not RE_OUTRO_CAMPO.search(seguinte)):
                    return seguinte.strip(), conf
    return None, None


def extrair_campos(linhas: list[tuple[str, float]]) -> dict:
    """Lote e datas a partir das linhas do OCR. O lote é texto, sem correção de caracteres."""
    campos = {"lote": None, "data_fabricacao": None, "validade": None}
    confiancas = []
    linhas = [(texto.upper(), conf) for texto, conf in linhas]
    campos["lote"], conf_lote = ler_lote(linhas)
    if conf_lote is not None:
        confiancas.append(conf_lote)
    for texto, conf in linhas:
        for campo, regex in (("data_fabricacao", RE_FAB), ("validade", RE_VAL)):
            if campos[campo] is None and (valor := _data(regex.search(texto))):
                campos[campo] = valor
                confiancas.append(conf)
    # Confiança = a pior linha usada nos campos lidos; nada lido = 0 (leva a pendente).
    campos["confianca_ocr"] = round(min(confiancas), 3) if confiancas else 0.0
    return campos


# --- função pública ----------------------------------------------------------

def _leitura_vazia() -> LeituraEmbalagem:
    return LeituraEmbalagem(ean=None, produto=None, marca=None, lote=None,
                            data_fabricacao=None, validade=None, confianca_ocr=0.0)


def ler_embalagem(
    imagem: bytes,
    *,
    catalogo: Mapping[str, tuple[str, str]] | None = None,
    leitor: LeitorOCR | None = None,
) -> LeituraEmbalagem:
    """Foto da embalagem → formato 5. Nunca levanta exceção; falha = leitura vazia (pendente).

    `catalogo`: EAN → (produto, marca), para identificar o produto pelo código de barras.
    Sem catálogo, produto e marca ficam nulos e a identificação depende do EAN.
    """
    try:
        matriz = cv2.imdecode(np.frombuffer(imagem, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if matriz is None:
            return _leitura_vazia()
        ean = ler_ean(matriz)
        campos = extrair_campos(agrupar_linhas((leitor or leitor_padrao)(preprocessar(matriz))))
        del matriz  # a imagem não sobrevive à chamada
        produto, marca = (catalogo or {}).get(ean, (None, None)) if ean else (None, None)
        return LeituraEmbalagem(ean=ean, produto=produto, marca=marca, **campos)
    except Exception as erro:  # noqa: BLE001 — contrato: nunca levantar para quem chama
        log.warning("falha ao ler a embalagem: %s", type(erro).__name__)  # sem imagem nem texto no log
        return _leitura_vazia()
