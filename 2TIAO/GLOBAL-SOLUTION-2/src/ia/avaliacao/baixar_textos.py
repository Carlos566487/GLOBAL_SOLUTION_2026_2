"""Baixa o texto oficial de cada recolhimento para a avaliação do extrator.

Não é o coletor: sem agendamento e sem fonte_hash oficial. Fonte de cada recolhimento
= coluna "Fonte oficial" da aba "Alertas" de data/Dataset_Recall_Anvisa.xlsx.
Saída: data/textos_avaliacao/<recolhimento_id>.txt + manifesto.json.

Uso (na pasta src/):  python -m ia.avaliacao.baixar_textos [--so id1,id2] [--forcar]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import pdfplumber
import requests
from bs4 import BeautifulSoup

from ia.schemas import fonte_oficial

RAIZ = Path(__file__).resolve().parents[3]
PLANILHA = RAIZ / "data" / "Dataset_Recall_Anvisa.xlsx"
SAIDA = RAIZ / "data" / "textos_avaliacao"
MANIFESTO = SAIDA / "manifesto.json"

# Containers do corpo da notícia (gov.br/Plone, prefeitura.sp/Liferay), do mais ao menos específico.
SELETORES = ["section.psp-agencies-content", "#parent-fieldname-text", "#content-core", "#content",
             ".journal-content-article", "article", "main"]
HEADERS = {"User-Agent": "Mozilla/5.0 (POC academica FIAP - avaliacao de extracao)"}


def ler_fontes() -> dict[str, str]:
    aba = openpyxl.load_workbook(PLANILHA, read_only=True)["Alertas"]
    linhas = aba.iter_rows(values_only=True)
    cabecalho = next(linhas)
    i_id, i_fonte = cabecalho.index("alerta_id"), cabecalho.index("Fonte oficial")
    return {linha[i_id]: linha[i_fonte] for linha in linhas if linha[i_id]}


def texto_de_pdf(conteudo: bytes) -> str:
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        return "\n\n".join(pagina.extract_text() or "" for pagina in pdf.pages)


def _texto_bloco(bloco: dict) -> str:
    tipo = bloco.get("@type")
    if tipo == "html":
        return _texto_corrido(BeautifulSoup(bloco.get("html", ""), "html.parser"))
    if tipo == "slate":
        return bloco.get("plaintext", "")
    if tipo == "text":  # draft-js
        return "\n".join(b.get("text", "") for b in (bloco.get("text") or {}).get("blocks", []))
    if tipo == "slateTable":
        linhas = (bloco.get("table") or {}).get("rows", [])
        return "\n".join(
            " | ".join(" ".join(_textos_slate(c.get("value"))) for c in linha.get("cells", []))
            for linha in linhas
        )
    return ""


def _texto_corrido(sopa: BeautifulSoup) -> str:
    """Quebra linha só em elementos de bloco; tags inline (<strong>, <a>) não partem a frase."""
    for tag in sopa.find_all(["p", "br", "li", "tr", "div", "h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.insert_after("\n")
    for celula in sopa.find_all(["td", "th"]):
        celula.insert_after(" | ")
    linhas = (re.sub(r"[ \t\xa0]+", " ", linha).strip() for linha in sopa.get_text().splitlines())
    return "\n".join(linha for linha in linhas if linha)


def _textos_slate(no) -> list[str]:
    if isinstance(no, dict):
        return [no["text"]] if "text" in no else _textos_slate(no.get("children"))
    if isinstance(no, list):
        return [t for filho in no for t in _textos_slate(filho)]
    return []


def texto_de_volto(sopa: BeautifulSoup) -> str | None:
    """Portal gov.br novo (Plone Volto): o corpo vem em JSON no `window.__data`."""
    script = next((s.string for s in sopa.find_all("script") if s.string and "window.__data=" in s.string), None)
    if not script:
        return None
    # É um literal JS, não JSON puro: `undefined` aparece como valor.
    bruto = re.sub(r"(?<=[:,\[])undefined(?=[,}\]])", "null", script.split("window.__data=", 1)[1])
    dados, _ = json.JSONDecoder().raw_decode(bruto.strip())
    conteudo = (dados.get("content") or {}).get("data") or {}
    blocos, ordem = conteudo.get("blocks") or {}, (conteudo.get("blocks_layout") or {}).get("items", [])
    partes = [conteudo.get("title", ""), conteudo.get("description", "")]
    partes += [_texto_bloco(blocos[i]) for i in ordem if i in blocos]
    texto = "\n".join(p for p in partes if p and p.strip())
    return texto or None


def texto_de_html(conteudo: bytes, charset: str | None = None) -> str:
    # O charset do cabeçalho HTTP vale mais que o <meta> (datalegis declara utf-8 no meta e envia latin-1).
    sopa = BeautifulSoup(conteudo, "html.parser", from_encoding=charset)
    volto = texto_de_volto(sopa)
    if volto:
        return volto
    for tag in sopa(["script", "style", "nav", "header", "footer", "noscript", "form"]):
        tag.decompose()
    titulo = sopa.find("h1")
    corpo = next((sopa.select_one(s) for s in SELETORES if sopa.select_one(s)), sopa.body or sopa)
    texto = _texto_corrido(corpo)
    if titulo and titulo.get_text(strip=True) not in texto:
        texto = titulo.get_text(strip=True) + "\n" + texto
    return texto


def baixar(url: str) -> tuple[str, str]:
    resposta = requests.get(url, headers=HEADERS, timeout=60)
    resposta.raise_for_status()
    tipo = resposta.headers.get("Content-Type", "")
    if "pdf" in tipo or resposta.content[:4] == b"%PDF":
        return texto_de_pdf(resposta.content), "pdf"
    charset = resposta.encoding if "charset=" in tipo.lower() else None
    if charset and charset.lower() in ("iso-8859-1", "latin-1"):
        charset = "cp1252"  # superconjunto usado na prática
    return texto_de_html(resposta.content, charset), "html"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--so", help="ids separados por vírgula")
    parser.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se o arquivo existir")
    args = parser.parse_args()

    SAIDA.mkdir(parents=True, exist_ok=True)
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8")) if MANIFESTO.exists() else {}
    fontes = ler_fontes()
    alvo = args.so.split(",") if args.so else list(fontes)

    for rid in alvo:
        url = fontes[rid]
        arquivo = SAIDA / f"{rid}.txt"
        if arquivo.exists() and not args.forcar:
            print(f"{rid}: já existe, pulando")
            continue
        if arquivo.exists() and "TRANSCRIÇÃO MANUAL" in arquivo.read_text(encoding="utf-8"):
            print(f"{rid}: contém transcrição manual, não sobrescrito (apague o arquivo para baixar de novo)")
            continue
        if not fonte_oficial(url):
            print(f"{rid}: FONTE NÃO OFICIAL, ignorada: {url}")
            continue
        try:
            texto, formato = baixar(url)
        except Exception as erro:  # noqa: BLE001 — script manual, só reporta
            print(f"{rid}: ERRO {erro}")
            continue
        texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
        arquivo.write_text(texto + "\n", encoding="utf-8")
        manifesto[rid] = {
            "fonte_url": url,
            "formato": formato,
            "obtido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "obtencao": "script",
            "caracteres": len(texto),
            # Hash local só para reprodutibilidade da avaliação; não é o fonte_hash do coletor.
            "sha256_local": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
        }
        print(f"{rid}: ok ({formato}, {len(texto)} caracteres)")

    MANIFESTO.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
