"""Gera as 3 imagens SIMULADAS de rótulo usadas na demonstração (data/demo/).

Uso (na pasta src/):  python -m ia.avaliacao.gerar_demo

Não são fotos: são rótulos desenhados com PIL, com a faixa "IMAGEM SIMULADA — DEMONSTRAÇÃO" e o
nome do arquivo visíveis. Ficam fora das métricas das fotos reais.
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parents[3]
PASTA_DEMO = RAIZ / "data" / "demo"


def ean13(corpo12: str) -> str:
    """Completa 12 dígitos com o dígito verificador GS1."""
    soma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(corpo12))
    return corpo12 + str((10 - soma % 10) % 10)


# Prefixo GS1 200–299 = numeração de uso interno/restrito: nunca é EAN de produto real.
EAN_DEMO = ean13("200000000153")
CATALOGO_DEMO = {EAN_DEMO: ("Ricota Fresca", "Vaidosa")}

DEMOS = [
    {"arquivo": "demo_vaidosa_153.png", "lote": "153", "borrar_lote": False,
     "esperado": "leitura completa, sem pendência → em_recall no motor (lote 153 está no alerta da Vaidosa)"},
    {"arquivo": "demo_vaidosa_154.png", "lote": "154", "borrar_lote": False,
     "esperado": "leitura completa, sem pendência → sem_recall no motor (lote 154 não está no alerta)"},
    {"arquivo": "demo_ilegivel.png", "lote": "153", "borrar_lote": True,
     "esperado": "lote ilegível → pendência → verificacao_pendente"},
]


def _codigo_de_barras(ean: str) -> Image.Image:
    from barcode import EAN13
    from barcode.writer import ImageWriter

    return EAN13(ean[:12], writer=ImageWriter()).render({"module_height": 18, "font_size": 12}).convert("RGB")


def _fonte(caminhos: tuple[str, ...], tamanho: int) -> ImageFont.FreeTypeFont:
    for caminho in caminhos:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(size=tamanho)


def _fonte_mono(tamanho: int) -> ImageFont.FreeTypeFont:
    return _fonte(("C:/Windows/Fonts/consola.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                   "/System/Library/Fonts/Menlo.ttc"), tamanho)


def _fonte_texto(tamanho: int) -> ImageFont.FreeTypeFont:
    """Fonte com acentos e travessão (a embutida do PIL não tem Ç, Ã, —)."""
    return _fonte(("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/System/Library/Fonts/Helvetica.ttc"), tamanho)


# Layout das linhas de lote e datas: (y da 1ª linha, distância entre linhas, corpo da fonte).
# Escolhido entre alguns candidatos pela maior confiança mínima do EasyOCR nas duas imagens legíveis;
# o CLAHE do leitor trabalha por blocos, então a vizinhança de cada linha muda a confiança. Quem foi
# ajustado foi o desenho do rótulo simulado; o leitor e o limite de 0,8 não mudaram.
LAYOUT_PADRAO = (300, 100, 64)


def desenhar(arquivo: str, lote: str, borrar_lote: bool, layout: tuple[int, int, int] = LAYOUT_PADRAO) -> Image.Image:
    largura, altura = 1100, 1000
    y0, passo, corpo = layout
    img = Image.new("RGB", (largura, altura), "white")
    d = ImageDraw.Draw(img)
    fonte = ImageFont.load_default(size=56)
    grande = _fonte_mono(corpo)  # monoespaçada, como a impressão de lote
    pequena = _fonte_texto(26)

    d.rectangle([0, 0, largura, 70], fill=(200, 30, 30))
    d.text((24, 16), "IMAGEM SIMULADA — DEMONSTRAÇÃO", font=pequena, fill="white")
    d.text((largura - 24, 16), arquivo, font=pequena, fill="white", anchor="ra")

    d.text((60, 110), "RICOTA FRESCA", font=fonte, fill="black")
    d.text((60, 180), "VAIDOSA", font=fonte, fill="black")
    caixa_lote = (50, y0 - 10, 700, y0 + passo - 10)
    d.text((60, y0), f"L:{lote}", font=grande, fill="black")
    d.text((60, y0 + passo), "FAB: 10/06/2026", font=grande, fill="black")
    d.text((60, y0 + 2 * passo), "VAL: 01/08/2026", font=grande, fill="black")

    if borrar_lote:
        regiao = img.crop(caixa_lote).filter(ImageFilter.GaussianBlur(9))
        ruido = np.random.default_rng(0).normal(0, 20, (regiao.height, regiao.width, 3))
        regiao = Image.fromarray(np.clip(np.asarray(regiao) + ruido, 0, 255).astype(np.uint8))
        img.paste(regiao, caixa_lote[:2])

    codigo = _codigo_de_barras(EAN_DEMO)
    img.paste(codigo, (60, altura - codigo.height - 40))
    d.rectangle([0, altura - 30, largura, altura], fill=(200, 30, 30))
    d.text((24, altura - 28), "IMAGEM SIMULADA — DEMONSTRAÇÃO · EAN fictício (prefixo 200, uso interno)",
           font=_fonte_texto(20), fill="white")
    return img


def gerar() -> list[Path]:
    PASTA_DEMO.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for demo in DEMOS:
        caminho = PASTA_DEMO / demo["arquivo"]
        desenhar(demo["arquivo"], demo["lote"], demo["borrar_lote"]).save(caminho)
        caminhos.append(caminho)
    return caminhos


def png_em_memoria(demo: dict) -> bytes:
    buffer = io.BytesIO()
    desenhar(demo["arquivo"], demo["lote"], demo["borrar_lote"]).save(buffer, format="PNG")
    return buffer.getvalue()


if __name__ == "__main__":
    for caminho in gerar():
        print(caminho)
