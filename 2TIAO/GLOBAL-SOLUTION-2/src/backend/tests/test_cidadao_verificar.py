"""Fluxo do cidadão de ponta a ponta: POST /cidadao/verificar com as imagens
SIMULADAS da demo (data/demo/) e o alerta oficial real da Vaidosa.

Exige o leitor completo (OpenCV + EasyOCR + pyzbar); sem eles, é pulado.
Na primeira execução o EasyOCR baixa ~100 MB de pesos.

Executar a partir de `src/backend`:  python -m pytest tests/test_cidadao_verificar.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytest.importorskip("cv2")
pytest.importorskip("easyocr")
pytest.importorskip("pyzbar.pyzbar")
pytest.importorskip("google.genai")
pytest.importorskip("multipart")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import main, repositorio  # noqa: E402

DATA = SRC.parent / "data"
GOLDEN = DATA / "Golden_Set_Recall.json"


def _vaidosa() -> dict:
    dados = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return next(r for a in dados["alertas"] for r in a["rotulos"] if r["alerta_id"] == "vaidosa")


@pytest.fixture(scope="module")
def cliente():
    repositorio.limpar_dados()
    c = TestClient(main.app)
    # Carrega o alerta oficial na API (sem recebimentos).
    assert c.post("/motor/processar", json={"alerta": _vaidosa(), "recebimentos": []}).status_code == 200
    yield c
    repositorio.limpar_dados()


def _verificar(cliente, arquivo: str) -> dict:
    caminho = DATA / "demo" / arquivo
    with caminho.open("rb") as f:
        resp = cliente.post("/cidadao/verificar", files={"imagem": (arquivo, f, "image/png")})
    assert resp.status_code == 200
    return resp.json()


def test_lote_153_em_recall(cliente):
    r = _verificar(cliente, "demo_vaidosa_153.png")
    assert r["resultado"] == "em_recall"
    assert r["alerta_id"] == "vaidosa"
    assert r["fonte_url"].startswith("https://www.gov.br/anvisa/")
    assert r["leitura"]["lote"] == "153"


def test_lote_154_sem_recall(cliente):
    r = _verificar(cliente, "demo_vaidosa_154.png")
    assert r["resultado"] == "sem_recall"
    assert r["leitura"]["lote"] == "154"


def test_lote_ilegivel_verificacao_pendente(cliente):
    r = _verificar(cliente, "demo_ilegivel.png")
    assert r["resultado"] == "verificacao_pendente"
    assert "lote" in r["pendencias"]


def test_imagem_vazia_e_recusada(cliente):
    resp = cliente.post("/cidadao/verificar", files={"imagem": ("vazia.png", b"", "image/png")})
    assert resp.status_code == 400
