"""Gera docs/GS2026-2_Recall_Seguro.pdf a partir de relatorio.html.

Uso (a partir da raiz do repositório):
    pip install playwright && python -m playwright install chromium
    python 2TIAO/GLOBAL-SOLUTION-2/docs/pdf_fonte/gerar_pdf.py

Alternativa sem instalar nada: abrir relatorio.html no Chrome/Edge → Imprimir →
Salvar como PDF (A4, "Gráficos de fundo" ligado).
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
HTML = AQUI / "relatorio.html"
PDF = AQUI.parent / "GS2026-2_Recall_Seguro.pdf"

RODAPE = (
    '<div style="width:100%;font-size:7.5pt;color:#8a8984;padding:0 18mm;'
    'display:flex;justify-content:space-between;font-family:Arial">'
    "<span>Recall Seguro · Global Solution 2026.2 · FIAP</span>"
    '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
)

with sync_playwright() as p:
    navegador = p.chromium.launch()
    pagina = navegador.new_page()
    pagina.goto(HTML.as_uri(), wait_until="networkidle")
    pagina.pdf(
        path=str(PDF),
        format="A4",
        print_background=True,
        display_header_footer=True,
        header_template="<div></div>",
        footer_template=RODAPE,
        margin={"top": "20mm", "bottom": "20mm", "left": "18mm", "right": "18mm"},
    )
    navegador.close()

print(f"PDF gerado: {PDF}")
