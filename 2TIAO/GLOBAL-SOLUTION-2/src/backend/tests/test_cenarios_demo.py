"""Teste de ponta a ponta (API) dos 3 cenários de demonstração.

Reproduz `data/Cenarios_Implementacao_e_Testes.md` pela API FastAPI, com os
alertas reais do golden set (Vaidosa e Sanibras) e recebimentos SIMULADOS.
Gera a evidência citada em `docs/evidencias_testes.md` e no PDF.

Executar a partir de `src/backend`:  python -m pytest tests/test_cenarios_demo.py -v
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# main.py importa o leitor da embalagem (OpenCV) e o extrator (Gemini SDK).
pytest.importorskip("cv2")
pytest.importorskip("google.genai")
pytest.importorskip("multipart")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import main, repositorio  # noqa: E402

GOLDEN = SRC.parent / "data" / "Golden_Set_Recall.json"


def _alertas() -> dict[str, dict]:
    dados = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return {r["alerta_id"]: r for a in dados["alertas"] for r in a["rotulos"]}


ALERTAS = _alertas()
VAIDOSA = ALERTAS["vaidosa"]
SANIBRAS = ALERTAS["sanibras"]


def _ricota(**extra):
    base = {
        "produto": "Ricota Fresca",
        "marca": "Vaidosa",
        "fabricante": VAIDOSA["fabricante"],
        "cnpj": VAIDOSA["cnpj"],
        "categoria": "laticinio",
        "ean": "2000000001531",
        "data_fabricacao": "2026-06-10",
        "quantidade": 24,
        "recebido_em": "2026-06-14",
        "simulado": True,
    }
    base.update(extra)
    return base


def _suplemento(**extra):
    base = {
        "produto": SANIBRAS["produto"],
        "marca": "Sanibras",
        "fabricante": SANIBRAS["fabricante"],
        "cnpj": SANIBRAS["cnpj"],
        "categoria": "suplemento",
        "quantidade": 10,
        "simulado": True,
    }
    base.update(extra)
    return base


@pytest.fixture()
def cliente():
    repositorio.limpar_dados()
    yield TestClient(main.app)
    repositorio.limpar_dados()


def _por_loja(resposta: dict) -> dict[str, dict]:
    return {r["loja_id"]: r for r in resposta["resultados"]}


def test_cenario1_vaidosa_lista_confirmacao_humana(cliente):
    resp = cliente.post(
        "/motor/processar",
        json={
            "alerta": VAIDOSA,
            "recebimentos": [
                _ricota(recebimento_id="r-0001", loja_id="LOJA-A", lote="153"),
                _ricota(recebimento_id="r-0002", loja_id="LOJA-B", lote="154"),
            ],
        },
    ).json()

    lojas = _por_loja(resp)
    assert lojas["LOJA-A"]["resultado"] == "match"
    assert lojas["LOJA-A"]["evidencia"]["valor_recebimento"] == "153"
    assert lojas["LOJA-B"]["resultado"] == "sem_match"
    assert len(resp["matches_criados"]) == 1

    match = resp["matches_criados"][0]
    assert match["status"] == "aguardando_aprovacao"

    decidido = cliente.post(
        f"/matches/{match['match_id']}/decisao",
        json={"decisao": "confirmado", "responsavel": "qualidade.loja03"},
    )
    assert decidido.status_code == 200
    assert decidido.json()["status"] == "confirmado"
    assert decidido.json()["decisao"]["responsavel"] == "qualidade.loja03"

    # Uma decisão não pode ser sobrescrita.
    segunda = cliente.post(
        f"/matches/{match['match_id']}/decisao",
        json={"decisao": "rejeitado", "responsavel": "outro"},
    )
    assert segunda.status_code == 409


def test_cenario2_sanibras_data_corte_inclui_dia_limite(cliente):
    resp = cliente.post(
        "/motor/processar",
        json={
            "alerta": SANIBRAS,
            "recebimentos": [
                _suplemento(recebimento_id="r-0101", loja_id="LOJA-A", data_fabricacao="2026-06-12"),
                _suplemento(recebimento_id="r-0102", loja_id="LOJA-B", data_fabricacao="2026-06-13"),
            ],
        },
    ).json()

    lojas = _por_loja(resp)
    assert lojas["LOJA-A"]["resultado"] == "match"
    assert lojas["LOJA-A"]["evidencia"]["campo"] == "data_fabricacao"
    assert lojas["LOJA-B"]["resultado"] == "sem_match"


# Alerta Sanibras como o extrator o entrega (contrato v2): escopo
# "categoria_fabricante" + categoria "suplemento". O registro do golden set
# ainda não traz esses dois campos (pendência da PO), por isso são
# acrescentados aqui, iguais à saída real do extrator em
# docs/resultados_extracao_execucao.json.
SANIBRAS_CATEGORIA = {**SANIBRAS, "escopo": "categoria_fabricante", "categoria": "suplemento"}


def test_cenario2b_sanibras_produto_com_nome_comercial(cliente):
    """Antes um falso negativo (xfail): agora o motor confirma fabricante
    (CNPJ) + categoria e aplica a data de corte, sem depender do nome."""
    resp = cliente.post(
        "/motor/processar",
        json={
            "alerta": SANIBRAS_CATEGORIA,
            "recebimentos": [
                _suplemento(recebimento_id="r-0103", loja_id="LOJA-A",
                            produto="Whey Protein 900 g", data_fabricacao="2026-06-12"),
                _suplemento(recebimento_id="r-0104", loja_id="LOJA-B",
                            produto="Whey Protein 900 g", data_fabricacao="2026-06-13"),
                _suplemento(recebimento_id="r-0105", loja_id="LOJA-C",
                            produto="Creatina 300 g", categoria=None, data_fabricacao="2026-06-01"),
                _suplemento(recebimento_id="r-0106", loja_id="LOJA-D",
                            produto="Whey Protein 900 g", cnpj="11.111.111/0001-11",
                            fabricante="Outra Empresa Ltda.", data_fabricacao="2026-06-01"),
            ],
        },
    ).json()

    lojas = _por_loja(resp)
    # Nome comercial diferente, mesmo fabricante e categoria, dentro da data: match.
    assert lojas["LOJA-A"]["resultado"] == "match"
    assert lojas["LOJA-A"]["evidencia"]["campo"] == "data_fabricacao"
    # Mesma identidade, fabricado depois do corte: fora do recall.
    assert lojas["LOJA-B"]["resultado"] == "sem_match"
    # Categoria não informada: não presume seguro.
    assert lojas["LOJA-C"]["resultado"] == "verificacao_pendente"
    assert lojas["LOJA-C"]["motivos"] == ["categoria"]
    # Outro fabricante: fora do recall.
    assert lojas["LOJA-D"]["resultado"] == "sem_match"
    assert len(resp["matches_criados"]) == 1


def test_cenario3_vaidosa_lote_ilegivel_fica_pendente(cliente):
    resp = cliente.post(
        "/motor/processar",
        json={
            "alerta": VAIDOSA,
            "recebimentos": [
                _ricota(recebimento_id="r-0201", loja_id="LOJA-C", lote="   "),
                _ricota(recebimento_id="r-0202", loja_id="LOJA-D", lote=None),
            ],
        },
    ).json()

    for loja in ("LOJA-C", "LOJA-D"):
        r = _por_loja(resp)[loja]
        assert r["resultado"] == "verificacao_pendente"
        assert r["motivos"] == ["lote"]
    assert resp["matches_criados"] == []


def test_escala_1000_recebimentos_sem_falso_negativo(cliente):
    random.seed(7)
    afetados = {"148", "153", "166", "167"}
    lotes = ["148", "153", "154", "160", "166", "167", "170", None]
    recebimentos = [
        _ricota(recebimento_id=f"r-{i:04d}", loja_id=f"SP-{i % 20:02d}", lote=random.choice(lotes))
        for i in range(1000)
    ]
    resp = cliente.post(
        "/motor/processar", json={"alerta": VAIDOSA, "recebimentos": recebimentos}
    ).json()

    esperados = sum(1 for r in recebimentos if r["lote"] in afetados)
    pendentes = sum(1 for r in recebimentos if r["lote"] is None)
    assert len(resp["matches_criados"]) == esperados
    assert len(resp["pendentes"]) == pendentes
