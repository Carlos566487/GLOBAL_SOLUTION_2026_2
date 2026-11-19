import json
import re
from pathlib import Path

import pytest

from ia.prompt import CAMPOS_FORA_DO_LLM, carregar_prompt, montar_conteudo, schema_resposta
from ia.schemas import AlertaExtraido

DATA = Path(__file__).resolve().parents[3] / "data"
DIVISAO = json.loads((DATA / "divisao_golden_set.json").read_text(encoding="utf-8"))
GOLDEN = json.loads((DATA / "Golden_Set_Recall.json").read_text(encoding="utf-8"))
PROMPT = carregar_prompt()

EXEMPLOS = [i["recolhimento_id"] for i in DIVISAO["exemplos_prompt"]["itens"]]
RESERVADOS = {i["recolhimento_id"] for i in DIVISAO["reservados_avaliacao"]["itens"]}


def test_exemplos_sao_o_grupo_de_exemplos_mais_o_sintetico():
    assert [e.nome for e in PROMPT.exemplos] == EXEMPLOS + ["sintetico-data-corte"]


def test_cobre_os_quatro_tipos_e_um_pendente():
    tipos = {a["regra_lote"]["tipo"] for e in PROMPT.exemplos for a in e.saida["alertas"]}
    assert {"lista", "todos", "data_corte"} <= tipos
    assert any(a["campos_pendentes"] for e in PROMPT.exemplos for a in e.saida["alertas"])


def test_saidas_dos_exemplos_reais_sao_o_gabarito():
    for exemplo in PROMPT.exemplos[:-1]:
        rotulos = next(a for a in GOLDEN["alertas"] if a["recolhimento_id"] == exemplo.nome)["rotulos"]
        assert len(exemplo.saida["alertas"]) == len(rotulos)
        for saida, rotulo in zip(exemplo.saida["alertas"], rotulos):
            for campo in ("produto", "marca", "fabricante", "cnpj", "regra_lote", "campos_pendentes"):
                assert saida[campo] == rotulo[campo]


@pytest.mark.parametrize("exemplo", PROMPT.exemplos, ids=lambda e: e.nome)
def test_saidas_dos_exemplos_validam_no_formato_1(exemplo):
    for i, item in enumerate(exemplo.saida["alertas"]):
        alerta = AlertaExtraido.model_validate(
            {**item, "alerta_id": f"{exemplo.nome}-{i}", "fonte_url": "https://www.gov.br/anvisa/x"}
        )
        assert alerta.campos_pendentes == item["campos_pendentes"]


def test_nenhum_lote_reservado_vaza_para_o_prompt():
    enviado = PROMPT.sistema + "".join(e.entrada + json.dumps(e.saida) for e in PROMPT.exemplos)
    compacto = re.sub(r"\s+", "", enviado).upper()
    for a in GOLDEN["alertas"]:
        if a["recolhimento_id"] not in RESERVADOS:
            continue
        for rotulo in a["rotulos"]:
            for lote in rotulo["regra_lote"]["lotes"]:
                # lotes muito curtos (ex.: "42") aparecem por acaso em qualquer texto
                if len(lote) >= 5:
                    assert re.sub(r"\s+", "", lote).upper() not in compacto, (a["recolhimento_id"], lote)


def test_schema_sem_ref_sem_campos_do_extrator_e_tudo_obrigatorio():
    schema = schema_resposta()
    assert "$ref" not in json.dumps(schema)
    item = schema["properties"]["alertas"]["items"]
    assert not set(CAMPOS_FORA_DO_LLM) & set(item["properties"])
    assert set(item["required"]) == set(item["properties"])
    regra = item["properties"]["regra_lote"]
    assert set(regra["required"]) == {"tipo", "lotes", "sufixo", "fabricado_ate"}


def test_conteudo_alterna_usuario_e_modelo_e_termina_no_texto():
    conteudo = montar_conteudo("Texto novo", PROMPT)
    papeis = [c.role for c in conteudo]
    assert papeis == ["user", "model"] * len(PROMPT.exemplos) + ["user"]
    assert conteudo[-1].parts[0].text.endswith("Texto novo")
