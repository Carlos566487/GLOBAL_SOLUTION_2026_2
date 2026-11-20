"""Carrega os dados da demonstração na API (que guarda tudo em memória).

Uso, com a API no ar (uvicorn backend.app.main:app), a partir desta pasta (src/):
    python carregar_demo.py

Alertas: registros REAIS do golden set (Vaidosa e Sanibras).
Recebimentos das lojas: SIMULADOS (simulado: true).
Rode de novo sempre que a API for reiniciada. Não rode duas vezes seguidas sem
reiniciar a API, senão os matches aparecem duplicados no painel.
"""
import json
from pathlib import Path

import requests

API = "http://127.0.0.1:8000"
GOLDEN = Path(__file__).resolve().parent.parent / "data" / "Golden_Set_Recall.json"

dados = json.loads(GOLDEN.read_text(encoding="utf-8"))
alertas = {r["alerta_id"]: r for a in dados["alertas"] for r in a["rotulos"]}

# Cenários 1 e 3 — Ricota Vaidosa, regra "lista" (lotes 148, 153, 166, 167)
vaidosa = alertas["vaidosa"]
ricota = dict(produto="Ricota Fresca", marca="Vaidosa", cnpj=vaidosa["cnpj"], simulado=True)
r1 = requests.post(f"{API}/motor/processar", json={"alerta": vaidosa, "recebimentos": [
    dict(ricota, loja_id="SP-ZL-03", lote="153"),   # no alerta -> match
    dict(ricota, loja_id="SP-ZN-07", lote="154"),   # fora do alerta -> sem match
    dict(ricota, loja_id="SP-ZS-11", lote="166"),   # no alerta -> match
    dict(ricota, loja_id="SP-CE-01", lote=None),    # lote ilegível -> pendente
]}, timeout=30)
r1.raise_for_status()

# Cenário 2 — Sanibras, escopo categoria_fabricante + data de corte 2026-06-12
# (escopo/categoria iguais à saída real do extrator; o golden set ainda não tem esses campos)
sanibras = {**alertas["sanibras"], "escopo": "categoria_fabricante", "categoria": "suplemento"}
suplemento = dict(marca="Sanibras", cnpj=sanibras["cnpj"], fabricante=sanibras["fabricante"],
                  categoria="suplemento", simulado=True)
r2 = requests.post(f"{API}/motor/processar", json={"alerta": sanibras, "recebimentos": [
    dict(suplemento, loja_id="SP-ZL-03", produto="Whey Protein 900 g", data_fabricacao="2026-06-12"),
    dict(suplemento, loja_id="SP-ZO-05", produto="Whey Protein 900 g", data_fabricacao="2026-06-13"),
]}, timeout=30)
r2.raise_for_status()

total = requests.get(f"{API}/matches", timeout=30).json()["total"]
print(f"{total} matches carregados (esperado: 3). Atualize o painel em http://localhost:5173")
