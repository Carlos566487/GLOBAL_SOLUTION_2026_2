"""Testes do leitor da embalagem com imagens sintéticas geradas em memória (nenhuma foto real)."""
import importlib.util
import os
from datetime import date

import cv2
import numpy as np
import pytest

from ia import embalagem
from ia.embalagem import agrupar_linhas, ean_valido, extrair_campos, ler_embalagem

TEM_EASYOCR = importlib.util.find_spec("easyocr") is not None
TEM_BARCODE = importlib.util.find_spec("barcode") is not None
EAN_FICTICIO = "2000000001531"  # prefixo GS1 200 (uso interno): nunca é produto real


# --- imagens sintéticas (só em memória) --------------------------------------

def rotulo(linhas: list[str], ean: str | None = None) -> np.ndarray:
    img = np.full((120 + 80 * len(linhas) + (260 if ean else 0), 1000, 3), 255, np.uint8)
    for i, texto in enumerate(linhas):
        cv2.putText(img, texto, (30, 90 + 80 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    if ean:
        from barcode import EAN13
        from barcode.writer import ImageWriter

        codigo = np.array(EAN13(ean[:12], writer=ImageWriter()).render().convert("RGB"))
        h, w = codigo.shape[:2]
        y = img.shape[0] - h - 20
        img[y:y + h, 30:30 + w] = codigo[:, :, ::-1]
    return img


def png(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def ocr_falso(*linhas_conf):
    """Leitor que devolve as linhas dadas, uma caixa por linha."""
    def ler(_imagem):
        return [([[0, 50 * i], [100, 50 * i], [100, 50 * i + 30], [0, 50 * i + 30]], texto, conf)
                for i, (texto, conf) in enumerate(linhas_conf)]
    return ler


# --- regras de leitura (OCR falso, rápido) -----------------------------------

def test_le_lote_fabricacao_e_validade():
    campos = extrair_campos([("LOTE: 153", 0.99), ("FAB: 10/06/2026 VAL: 01/08/2026", 0.86)])
    assert campos["lote"] == "153"
    assert campos["data_fabricacao"] == date(2026, 6, 10)
    assert campos["validade"] == date(2026, 8, 1)
    assert campos["confianca_ocr"] == 0.86  # a pior linha usada


@pytest.mark.parametrize("texto, lote", [
    ("LOTE 183/3 B FAB: 10/06/2026", "183/3 B"),  # espaço interno preservado
    ("L: A107 VAL 08/12/26", "A107"),
    ("Lote:07225288", "07225288"),  # zero à esquerda preservado
    ("LOTE LZ1 VAL200127 3 P 200126", "LZ1 VAL200127 3 P 200126"),  # "VAL" dentro do código não corta
    # padrões das fotos de teste (convenção de lote)
    ("VAL:JAN/29 L029 SF", "029 SF"),  # "L" colado ao número; vai até o fim da linha
    ("L:23 21:40 M5-2", "23"),  # para na hora
    ("L.H26H0115", "H26H0115"),
    ("VAL: 14/02/27 L: 3260", "3260"),  # marcador depois da data
    ("L: JGU 080926", "JGU 080926"),
    ("L:172U404I", "172U404I"),
])
def test_formas_de_lote(texto, lote):
    assert extrair_campos([(texto, 0.95)])["lote"] == lote


@pytest.mark.parametrize("texto", ["LJA 076 4051 2", "LEITE INTEGRAL 1 L", "VALIDADE/LOTE:", "L: 21:40"])
def test_sem_marcador_valido_nao_ha_lote(texto):
    assert extrair_campos([(texto, 0.95)])["lote"] is None


def test_rotulo_lote_sem_marcador_usa_a_linha_de_codigo_seguinte():
    linhas = [("Validade/Lote:", 0.99), ("29/05/2027 08:37", 0.97), ("LJA 076 4051 2", 0.93),
              ("Predominantemente", 0.99), ("Conilon", 0.99)]
    campos = extrair_campos(linhas)
    assert campos["lote"] == "LJA 076 4051 2"  # a linha inteira, inclusive o "L" inicial
    assert campos["confianca_ocr"] == 0.93


def test_marcador_tem_prioridade_sobre_o_rotulo():
    linhas = [("EMPACOTAMENTO/VALIDADE/LOTE", 0.99), ("EMP: 14/10/26 M04 16:40", 0.9), ("VAL: 14/02/27 L: 3260", 0.88)]
    assert extrair_campos(linhas)["lote"] == "3260"


def test_validade_nao_vira_fabricacao():
    campos = extrair_campos([("VAL: 01/08/2026", 0.95)])
    assert campos["data_fabricacao"] is None and campos["validade"] == date(2026, 8, 1)


def test_data_impossivel_e_ignorada():
    assert extrair_campos([("FAB: 31/02/2026", 0.95)])["data_fabricacao"] is None


def test_nada_lido_tem_confianca_zero():
    assert extrair_campos([("RICOTA FRESCA", 0.99)]) == {
        "lote": None, "data_fabricacao": None, "validade": None, "confianca_ocr": 0.0}


def test_agrupar_linhas_junta_caixas_na_mesma_altura():
    resultado = [([[200, 0], [300, 0], [300, 30], [200, 30]], "153", 0.9),
                 ([[0, 2], [100, 2], [100, 32], [0, 32]], "LOTE:", 0.7),
                 ([[0, 80], [100, 80], [100, 110], [0, 110]], "VAL: 01/08/2026", 0.95)]
    assert agrupar_linhas(resultado) == [("LOTE: 153", 0.7), ("VAL: 01/08/2026", 0.95)]


@pytest.mark.parametrize("codigo, ok", [(EAN_FICTICIO, True), ("2000000001532", False), ("123", False)])
def test_ean_valido(codigo, ok):
    assert ean_valido(codigo) is ok


# --- ler_embalagem com OCR falso ----------------------------------------------

def test_leitura_completa_sem_pendencia(monkeypatch):
    monkeypatch.setattr(embalagem, "ler_ean", lambda _cinza: EAN_FICTICIO)
    leitura = ler_embalagem(png(rotulo(["x"])), leitor=ocr_falso(("LOTE: 153", 0.95)),
                            catalogo={EAN_FICTICIO: ("Ricota Fresca", "Vaidosa")})
    assert (leitura.ean, leitura.produto, leitura.marca, leitura.lote) == (EAN_FICTICIO, "Ricota Fresca", "Vaidosa", "153")
    assert leitura.pendencias("lista") == []


def test_confianca_baixa_fica_pendente(monkeypatch):
    monkeypatch.setattr(embalagem, "ler_ean", lambda _cinza: EAN_FICTICIO)
    leitura = ler_embalagem(png(rotulo(["x"])), leitor=ocr_falso(("LOTE: 153", 0.62)))
    assert "confianca_ocr" in leitura.pendencias("lista")


def test_sem_ean_e_sem_catalogo_produto_nao_identificado(monkeypatch):
    monkeypatch.setattr(embalagem, "ler_ean", lambda _cinza: None)
    leitura = ler_embalagem(png(rotulo(["x"])), leitor=ocr_falso(("LOTE: 153", 0.99)))
    assert "produto" in leitura.pendencias("lista")


def test_data_corte_sem_fabricacao_fica_pendente(monkeypatch):
    monkeypatch.setattr(embalagem, "ler_ean", lambda _cinza: EAN_FICTICIO)
    leitura = ler_embalagem(png(rotulo(["x"])), leitor=ocr_falso(("LOTE: 153 VAL: 01/08/2026", 0.99)))
    assert leitura.pendencias("data_corte") == ["data_fabricacao"]


@pytest.mark.parametrize("dados", [b"", b"nao e imagem", b"\x89PNG\r\n\x1a\n quebrado"])
def test_bytes_invalidos_viram_leitura_vazia(dados):
    leitura = ler_embalagem(dados, leitor=ocr_falso())
    assert leitura.confianca_ocr == 0.0 and leitura.pendencias("lista")


def test_erro_do_ocr_nao_vaza_excecao():
    def quebra(_img):
        raise RuntimeError("falha no modelo")
    leitura = ler_embalagem(png(rotulo(["x"])), leitor=quebra)
    assert leitura.confianca_ocr == 0.0


def test_nada_e_gravado_em_disco(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cv2, "imwrite", lambda *a, **k: pytest.fail("imagem gravada em disco"))
    ler_embalagem(png(rotulo(["LOTE: 153"])), leitor=ocr_falso(("LOTE: 153", 0.99)))
    assert os.listdir(tmp_path) == []


# --- integração com EasyOCR e pyzbar reais (imagens sintéticas) ---------------

@pytest.mark.skipif(not (TEM_EASYOCR and TEM_BARCODE), reason="easyocr/python-barcode não instalados")
def test_integracao_rotulo_nitido_com_codigo_de_barras():
    img = rotulo(["RICOTA FRESCA VAIDOSA", "LOTE: 153", "FAB: 10/06/2026  VAL: 01/08/2026"], ean=EAN_FICTICIO)
    leitura = ler_embalagem(png(img), catalogo={EAN_FICTICIO: ("Ricota Fresca", "Vaidosa")})
    assert leitura.ean == EAN_FICTICIO
    assert leitura.lote == "153"
    assert leitura.data_fabricacao == date(2026, 6, 10)
    assert leitura.pendencias("lista") == []


@pytest.mark.skipif(not TEM_EASYOCR, reason="easyocr não instalado")
def test_integracao_rotulo_ilegivel_fica_pendente():
    img = rotulo(["RICOTA FRESCA VAIDOSA", "LOTE: 153", "VAL: 01/08/2026"])
    img = cv2.GaussianBlur(img, (61, 61), 25)
    ruido = np.random.default_rng(0).normal(0, 60, img.shape)
    img = np.clip(img + ruido, 0, 255).astype(np.uint8)
    leitura = ler_embalagem(png(img))
    # O que importa: nunca um lote "confiante" a partir de uma foto ilegível.
    assert leitura.pendencias("lista")


@pytest.mark.skipif(not (TEM_EASYOCR and TEM_BARCODE), reason="easyocr/python-barcode não instalados")
@pytest.mark.parametrize("indice", [0, 1, 2], ids=["vaidosa_153", "vaidosa_154", "ilegivel"])
def test_imagens_simuladas_da_demo(indice):
    from ia.avaliacao.gerar_demo import CATALOGO_DEMO, DEMOS, EAN_DEMO, ean13, png_em_memoria

    assert ean13(EAN_DEMO[:12]) == EAN_DEMO and ean_valido(EAN_DEMO) and EAN_DEMO.startswith("200")
    demo = DEMOS[indice]
    leitura = ler_embalagem(png_em_memoria(demo), catalogo=CATALOGO_DEMO)
    assert (leitura.ean, leitura.produto, leitura.marca) == (EAN_DEMO, "Ricota Fresca", "Vaidosa")
    if demo["borrar_lote"]:
        assert leitura.lote is None and "lote" in leitura.pendencias("lista")
    else:
        assert leitura.lote == demo["lote"]
        assert leitura.data_fabricacao == date(2026, 6, 10) and leitura.validade == date(2026, 8, 1)
        assert leitura.pendencias("lista") == []
