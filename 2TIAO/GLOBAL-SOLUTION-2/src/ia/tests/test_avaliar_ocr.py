"""Script de teste do OCR rodado numa pasta temporária com imagens sintéticas (nenhuma foto real)."""
import cv2
import numpy as np
import pytest

from ia import embalagem
from ia.avaliacao import avaliar_ocr

CSV = (
    "arquivo;produto;marca;ean;lote;data_fabricacao;validade;legivel_sim_nao;observacao\n"
    "nitida.png;Ricota Fresca;Vaidosa;2000000001531;153;10/06/2026;01/08/2026;sim;\n"
    "lote_errado.png;Ricota Fresca;Vaidosa;2000000001531;153;;2027-09;sim;\n"
    "so_ean.png;Ricota Fresca;Vaidosa;2000000001531;;;;nao;\n"
    "borrada.png;nao_identificado;nao_identificado;;;;;nao;controle negativo\n"
    "falta.png;Ricota Fresca;Vaidosa;;;;;sim;\n"
)
LEITURAS = {  # o que o OCR "lê" em cada foto sintética, pela largura da imagem
    101: [("LOTE: 153", 0.95), ("FAB: 10/06/2026 VAL: 01/08/2026", 0.9)],
    102: [("LOTE: 158", 0.93)],
    103: [("OLEO DE SOJA", 0.99)],
    104: [("L0TE 1S3", 0.31)],
}


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    (tmp_path / "gabarito_fotos.csv").write_text(CSV, encoding="utf-8")
    for nome, largura in (("nitida.png", 101), ("lote_errado.png", 102), ("so_ean.png", 103), ("borrada.png", 104)):
        cv2.imwrite(str(tmp_path / nome), np.full((50, largura), 255, np.uint8))
    monkeypatch.setattr(embalagem, "ler_ean", lambda _cinza: "2000000001531")
    monkeypatch.setattr(embalagem, "preprocessar", lambda cinza: cinza)
    return tmp_path


def leitor(imagem):
    return [([[0, 40 * i], [9, 40 * i], [9, 40 * i + 20], [0, 40 * i + 20]], t, c)
            for i, (t, c) in enumerate(LEITURAS[imagem.shape[1]])]


def test_classifica_e_agrupa(pasta):
    av = avaliar_ocr.avaliar(pasta, leitor=leitor)
    resultado = {l["arquivo"]: (l["resultado"] if not l["ausente"] else "ausente", l["grupos"]) for l in av["linhas"]}
    assert resultado == {
        "nitida.png": (avaliar_ocr.ACERTO, ["lote_legivel"]),
        "lote_errado.png": (avaliar_ocr.ERRO_CONFIANTE, ["lote_legivel", "validade_mes_ano"]),  # leu 158: o pior caso
        "so_ean.png": (avaliar_ocr.PENDENTE_CORRETO, ["so_ean"]),
        "borrada.png": (avaliar_ocr.PENDENTE_CORRETO, ["controle_negativo"]),
        "falta.png": ("ausente", []),
    }


def test_relatorio_tem_as_duas_versoes_e_os_grupos(pasta, tmp_path_factory):
    av = avaliar_ocr.avaliar(pasta, leitor=leitor)
    saida = tmp_path_factory.mktemp("docs")
    avaliar_ocr.escrever_relatorio([("Versão A", "desc A", av), ("Versão B", "desc B", av)], saida / "r.md", saida / "r.csv")
    md = (saida / "r.md").read_text(encoding="utf-8")
    assert md.count("| Lote legível | 2 | 1/2 (50%) |") == 2
    assert "| Controle negativo (lote ilegível) | 1 |" in md
    assert "**1/4 (25%)**" in md  # erro confiante destacado, sobre todas as fotos lidas
    assert "| lote | 1/2 (50%) | 0 | 1 |" in md
    linhas_csv = (saida / "r.csv").read_text(encoding="utf-8-sig").splitlines()
    assert len(linhas_csv) == 1 + 2 * 5


def test_leitor_original_vem_do_commit_anterior_a_regra():
    ler = avaliar_ocr.carregar_leitor_original()
    assert callable(ler) and ler.__module__ == "ia._embalagem_original"


def test_gabarito_aceita_datas_iso_e_brasileiras(tmp_path):
    (tmp_path / "g.csv").write_text("arquivo,lote,data_fabricacao,validade,legivel_sim_nao\n"
                                    "a.jpg,1,2026-06-10,01/08/2026,Sim\n", encoding="utf-8")
    [g] = avaliar_ocr.carregar_gabarito(tmp_path / "g.csv")
    assert str(g["data_fabricacao"]) == "2026-06-10" and str(g["validade"]) == "2026-08-01" and g["legivel"]
