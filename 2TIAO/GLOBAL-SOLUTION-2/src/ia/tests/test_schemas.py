import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ia.schemas import AlertaExtraido, LeituraEmbalagem, RegraLote, normalizar_lote

DATA = Path(__file__).resolve().parents[3] / "data"
GOLDEN = json.loads((DATA / "Golden_Set_Recall.json").read_text(encoding="utf-8"))
REGISTROS = [r for a in GOLDEN["alertas"] for r in a["rotulos"]]

VAIDOSA = next(r for r in REGISTROS if r["alerta_id"] == "vaidosa")


def alerta(**mudancas):
    dados = copy.deepcopy(VAIDOSA)
    dados.update(mudancas)
    return dados


# --- Golden set -------------------------------------------------------------

def test_golden_set_tem_36_registros():
    assert len(GOLDEN["alertas"]) == 20
    assert len(REGISTROS) == 36


@pytest.mark.parametrize("registro", REGISTROS, ids=lambda r: r["alerta_id"])
def test_golden_set_valida_e_pendencias_batem(registro):
    a = AlertaExtraido.model_validate(registro)
    assert a.status_extracao == registro["status_extracao"]
    assert a.campos_pendentes == registro["campos_pendentes"]
    # lotes saem exatamente como entraram (texto, zeros à esquerda, barras, espaços)
    assert a.model_dump(mode="json")["regra_lote"]["lotes"] == registro["regra_lote"]["lotes"]


def test_regra_do_teste_sintetico_de_sufixo_valida():
    regra = RegraLote.model_validate(GOLDEN["teste_sintetico_sufixo"]["regra_lote"])
    assert regra.tipo == "sufixo" and regra.sufixo == "07"


# --- Lote é texto -----------------------------------------------------------

def test_lote_numerico_e_rejeitado():
    dados = alerta()
    dados["regra_lote"]["lotes"] = [148, 153]
    with pytest.raises(ValidationError):
        AlertaExtraido.model_validate(dados)


def test_zeros_a_esquerda_preservados():
    cecco = next(r for r in REGISTROS if r["alerta_id"] == "cecco")
    assert AlertaExtraido.model_validate(cecco).regra_lote.lotes == ["07225288"]


def test_lotes_vazios_sao_descartados_e_lista_vazia_fica_pendente():
    dados = alerta()
    dados["regra_lote"]["lotes"] = ["", "   "]
    a = AlertaExtraido.model_validate(dados)
    assert a.regra_lote.lotes == []
    assert a.status_extracao == "verificacao_pendente"
    assert a.campos_pendentes == ["regra_lote.lotes"]


@pytest.mark.parametrize(
    "entrada, esperado",
    [(" l2305a ", "L2305A"), ("LZ1 VAL200127 3 P 200126", "LZ1 VAL200127 3 P 200126"),
     ("07225288", "07225288"), ("183/3B", "183/3B"), ("", None), ("   ", None), (None, None)],
)
def test_normalizar_lote(entrada, esperado):
    assert normalizar_lote(entrada) == esperado


# --- Pendências -------------------------------------------------------------

def test_status_ok_com_campo_decisivo_nulo_vira_pendente():
    a = AlertaExtraido.model_validate(alerta(cnpj=None, status_extracao="ok", campos_pendentes=[]))
    assert a.status_extracao == "verificacao_pendente"
    assert a.campos_pendentes == ["cnpj"]


def test_texto_vazio_em_campo_decisivo_vira_pendente():
    a = AlertaExtraido.model_validate(alerta(marca="  "))
    assert a.marca is None and a.campos_pendentes == ["marca"]


def test_fabricante_nulo_nao_bloqueia():
    a = AlertaExtraido.model_validate(alerta(fabricante=None))
    assert a.status_extracao == "ok"


def test_cnpj_mal_formatado_vira_pendente():
    a = AlertaExtraido.model_validate(alerta(cnpj="02896434000147"))
    assert a.campos_pendentes == ["cnpj"]


def test_pendente_sem_motivo_continua_pendente():
    a = AlertaExtraido.model_validate(alerta(status_extracao="verificacao_pendente"))
    assert a.status_extracao == "verificacao_pendente"
    assert a.campos_pendentes == ["revisao_manual"]


def test_pendencia_informada_pelo_extrator_e_mantida():
    a = AlertaExtraido.model_validate(alerta(campos_pendentes=["regra_lote.lotes"]))
    assert a.status_extracao == "verificacao_pendente"


@pytest.mark.parametrize(
    "regra, campo",
    [({"tipo": None}, "regra_lote.tipo"),
     ({"tipo": "sufixo", "sufixo": " "}, "regra_lote.sufixo"),
     ({"tipo": "data_corte"}, "regra_lote.fabricado_ate")],
)
def test_regra_incompleta_vira_pendente(regra, campo):
    a = AlertaExtraido.model_validate(alerta(regra_lote=regra))
    assert a.campos_pendentes == [campo]


def test_todos_sem_lotes_e_valido():
    a = AlertaExtraido.model_validate(alerta(regra_lote={"tipo": "todos"}))
    assert a.status_extracao == "ok"


# --- Escopo (v2) -------------------------------------------------------------

def test_escopo_padrao_e_produto():
    assert AlertaExtraido.model_validate(VAIDOSA).escopo == "produto"


def test_sanibras_v2_categoria_fabricante():
    sanibras = next(r for r in REGISTROS if r["alerta_id"] == "sanibras")
    a = AlertaExtraido.model_validate({**sanibras, "escopo": "categoria_fabricante", "categoria": "suplemento"})
    assert a.status_extracao == "ok"
    assert a.regra_lote.fabricado_ate.isoformat() == "2026-06-12"


def test_categoria_fabricante_sem_categoria_vira_pendente():
    a = AlertaExtraido.model_validate(alerta(escopo="categoria_fabricante", categoria=None))
    assert a.campos_pendentes == ["categoria"]


# --- Fonte e contrato --------------------------------------------------------

@pytest.mark.parametrize(
    "url",
    ["https://portal-nao-oficial.com.br/ricota-vaidosa", "https://gov.br.exemplo.com/x", "ftp://www.gov.br/x"],
)
def test_fonte_nao_oficial_e_rejeitada(url):
    with pytest.raises(ValidationError):
        AlertaExtraido.model_validate(alerta(fonte_url=url))


def test_fonte_hash_valido_e_invalido():
    ok = "sha256:" + "a" * 64
    assert AlertaExtraido.model_validate(alerta(fonte_hash=ok)).fonte_hash == ok
    with pytest.raises(ValidationError):
        AlertaExtraido.model_validate(alerta(fonte_hash="abc"))


def test_campo_fora_do_contrato_e_rejeitado():
    with pytest.raises(ValidationError):
        AlertaExtraido.model_validate(alerta(decisao="recolher"))


# --- Formato 5 ---------------------------------------------------------------

LEITURA = {"ean": "7890000000000", "produto": "Ricota Fresca", "marca": "Vaidosa", "lote": "153",
           "data_fabricacao": None, "validade": "2026-08-01", "confianca_ocr": 0.91}


def test_leitura_do_contrato_valida_sem_pendencias():
    leitura = LeituraEmbalagem.model_validate(LEITURA)
    assert leitura.pendencias("lista") == []
    assert leitura.model_dump(mode="json") == LEITURA


@pytest.mark.parametrize("confianca, pendente", [(0.79, True), (0.8, False)])
def test_limite_de_confianca(confianca, pendente):
    leitura = LeituraEmbalagem.model_validate({**LEITURA, "confianca_ocr": confianca})
    assert ("confianca_ocr" in leitura.pendencias("lista")) is pendente


def test_data_corte_sem_fabricacao_fica_pendente_mesmo_com_validade():
    leitura = LeituraEmbalagem.model_validate(LEITURA)
    assert leitura.pendencias("data_corte") == ["data_fabricacao"]


def test_lote_ilegivel_fica_pendente():
    leitura = LeituraEmbalagem.model_validate({**LEITURA, "lote": " "})
    assert leitura.lote is None
    assert leitura.pendencias("lista") == ["lote"]


def test_produto_nao_identificado_fica_pendente():
    leitura = LeituraEmbalagem.model_validate({**LEITURA, "ean": None, "marca": None})
    assert leitura.pendencias() == ["produto"]


@pytest.mark.parametrize("mudanca", [{"confianca_ocr": 1.2}, {"ean": "78900A"}, {"lote": 153}])
def test_leitura_invalida_e_rejeitada(mudanca):
    with pytest.raises(ValidationError):
        LeituraEmbalagem.model_validate({**LEITURA, **mudanca})
