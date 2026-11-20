"""Regras de decisão do POST /cidadao/verificar SEM depender do OCR.

O leitor da embalagem é substituído por uma leitura fixa (monkeypatch), para
testar só a decisão: em_recall, sem_recall e verificacao_pendente.
Executar a partir de `src/backend`:  python -m pytest tests/test_cidadao_regras.py -v
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytest.importorskip("cv2")
pytest.importorskip("google.genai")
pytest.importorskip("multipart")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import main, repositorio  # noqa: E402
from ia.schemas import LeituraEmbalagem  # noqa: E402

VAIDOSA = {
    "alerta_id": "vaidosa", "fonte_url": "https://www.gov.br/anvisa/x", "fonte_hash": None,
    "produto": "Ricota Fresca", "marca": "Vaidosa",
    "fabricante": "Vaidosa Indústria e Comércio de Alimentos Ltda.", "cnpj": "02.896.434/0001-47",
    "escopo": "produto", "categoria": None,
    "regra_lote": {"tipo": "lista", "lotes": ["148", "153", "166", "167"], "sufixo": None, "fabricado_ate": None},
    "status_extracao": "ok", "campos_pendentes": [],
}
SANIBRAS = {
    "alerta_id": "sanibras", "fonte_url": "https://prefeitura.sp.gov.br/x", "fonte_hash": None,
    "produto": "Suplementos alimentares do fabricante", "marca": "Sanibras",
    "fabricante": "Sanibras Medicamentos e Nutrição Ltda.", "cnpj": "82.268.269/0001-18",
    "escopo": "categoria_fabricante", "categoria": "suplemento",
    "regra_lote": {"tipo": "data_corte", "lotes": [], "sufixo": None, "fabricado_ate": "2026-06-12"},
    "status_extracao": "ok", "campos_pendentes": [],
}


def _leitura(**campos) -> LeituraEmbalagem:
    base = {"ean": "7890000000000", "produto": None, "marca": None, "lote": None,
            "data_fabricacao": None, "validade": None, "confianca_ocr": 0.95}
    base.update(campos)
    return LeituraEmbalagem(**base)


@pytest.fixture()
def consultar(monkeypatch):
    repositorio.limpar_dados()
    repositorio.adicionar_alerta(VAIDOSA)
    repositorio.adicionar_alerta(SANIBRAS)
    cliente = TestClient(main.app)

    def _consultar(leitura: LeituraEmbalagem) -> dict:
        monkeypatch.setattr(main, "ler_embalagem", lambda *_a, **_k: leitura)
        resp = cliente.post("/cidadao/verificar", files={"imagem": ("x.png", b"bytes", "image/png")})
        assert resp.status_code == 200
        return resp.json()

    yield _consultar
    repositorio.limpar_dados()


def test_lote_do_alerta_em_recall(consultar):
    r = consultar(_leitura(produto="Ricota Fresca", marca="Vaidosa", lote="153"))
    assert r["resultado"] == "em_recall"
    assert r["alerta_id"] == "vaidosa"


def test_lote_fora_do_alerta_sem_recall(consultar):
    r = consultar(_leitura(produto="Ricota Fresca", marca="Vaidosa", lote="154"))
    assert r["resultado"] == "sem_recall"


def test_lote_ilegivel_pendente(consultar):
    r = consultar(_leitura(produto="Ricota Fresca", marca="Vaidosa", lote=None))
    assert r["resultado"] == "verificacao_pendente"
    assert "lote" in r["pendencias"]


def test_confianca_baixa_pendente(consultar):
    r = consultar(_leitura(produto="Ricota Fresca", marca="Vaidosa", lote="153", confianca_ocr=0.5))
    assert r["resultado"] == "verificacao_pendente"


def test_produto_nao_identificado_pendente(consultar):
    r = consultar(_leitura(ean=None, lote="153"))
    assert r["resultado"] == "verificacao_pendente"
    assert r["pendencias"] == ["produto"]


def test_recall_por_categoria_do_fabricante_nao_vira_sem_recall(consultar):
    """Antes: 'Whey Protein' da Sanibras recebia sem_recall (nome diferente do
    alerta). A embalagem não traz CNPJ nem categoria: o seguro é pendente."""
    r = consultar(_leitura(produto="Whey Protein 900 g", marca="Sanibras", lote="X1",
                           data_fabricacao=date(2026, 6, 10)))
    assert r["resultado"] == "verificacao_pendente"
    assert set(r["pendencias"]) == {"fabricante", "categoria"}


def test_outra_marca_sem_recall(consultar):
    r = consultar(_leitura(produto="Whey Protein 900 g", marca="Outra Marca", lote="X1"))
    assert r["resultado"] == "sem_recall"
