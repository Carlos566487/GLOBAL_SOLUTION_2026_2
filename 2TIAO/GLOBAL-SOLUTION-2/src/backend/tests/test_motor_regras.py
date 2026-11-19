from app.motor_regras import avaliar_recebimento, normalizar_lote


def alerta_base(tipo, **regra):
    return {
        "alerta_id": "teste",
        "produto": "Ricota Fresca",
        "marca": "Vaidosa",
        "fabricante": "Vaidosa Alimentos",
        "cnpj": "02.896.434/0001-47",
        "status_extracao": "ok",
        "campos_pendentes": [],
        "regra_lote": {
            "tipo": tipo,
            "lotes": regra.get("lotes"),
            "sufixo": regra.get("sufixo"),
            "fabricado_ate": regra.get("fabricado_ate"),
        },
    }


def recebimento_base(**dados):
    recebimento = {
        "loja_id": "LOJA-A",
        "produto": "Ricota Fresca",
        "marca": "Vaidosa",
        "cnpj": "02.896.434/0001-47",
        "lote": None,
        "data_fabricacao": None,
    }

    recebimento.update(dados)
    return recebimento


def test_normalizacao_lote_remove_espacos_e_coloca_maiusculo():
    assert normalizar_lote("183/3 b") == "183/3B"


def test_lista_lote_153_deve_gerar_match():
    alerta = alerta_base(
        "lista",
        lotes=["148", "153", "166", "167"],
    )

    resultado = avaliar_recebimento(
        alerta,
        recebimento_base(lote="153"),
    )

    assert resultado["match"] is True
    assert resultado["resultado"] == "match"
    assert resultado["evidencia"]["campo"] == "lote"


def test_lista_lote_154_nao_deve_gerar_match():
    alerta = alerta_base(
        "lista",
        lotes=["148", "153", "166", "167"],
    )

    resultado = avaliar_recebimento(
        alerta,
        recebimento_base(lote="154"),
    )

    assert resultado["match"] is False
    assert resultado["resultado"] == "sem_match"


def test_lista_sem_lote_deve_ficar_pendente():
    alerta = alerta_base(
        "lista",
        lotes=["148", "153"],
    )

    resultado = avaliar_recebimento(
        alerta,
        recebimento_base(lote=None),
    )

    assert resultado["resultado"] == "verificacao_pendente"
    assert "lote" in resultado["motivos"]


def test_sufixo_deve_normalizar_espacos():
    alerta = alerta_base(
        "sufixo",
        sufixo="3B",
    )

    resultado = avaliar_recebimento(
        alerta,
        recebimento_base(lote="183/3 B"),
    )

    assert resultado["match"] is True
    assert resultado["resultado"] == "match"


def test_data_corte_inclui_o_dia_limite():
    alerta = alerta_base(
        "data_corte",
        fabricado_ate="2026-06-12",
    )

    resultado = avaliar_recebimento(
        alerta,
        recebimento_base(
            data_fabricacao="2026-06-12"
        ),
    )

    assert resultado["match"] is True


def test_data_corte_dia_seguinte_nao_entra():
    alerta = alerta_base(
        "data_corte",
        fabricado_ate="2026-06-12",
    )

    resultado = avaliar_recebimento(
        alerta,
        recebimento_base(
            data_fabricacao="2026-06-13"
        ),
    )

    assert resultado["match"] is False
    assert resultado["resultado"] == "sem_match"


def test_data_corte_sem_data_fabricacao_fica_pendente():
    alerta = alerta_base(
        "data_corte",
        fabricado_ate="2026-06-12",
    )

    resultado = avaliar_recebimento(
        alerta,
        recebimento_base(data_fabricacao=None),
    )

    assert resultado["resultado"] == "verificacao_pendente"
    assert "data_fabricacao" in resultado["motivos"]


def test_regra_todos_deve_gerar_match():
    alerta = alerta_base("todos")

    resultado = avaliar_recebimento(
        alerta,
        recebimento_base(lote="QUALQUER-LOTE"),
    )

    assert resultado["match"] is True
    assert resultado["resultado"] == "match"


def test_alerta_pendente_nao_pode_entrar_no_motor():
    alerta = alerta_base(
        "lista",
        lotes=["153"],
    )

    alerta["status_extracao"] = "verificacao_pendente"
    alerta["campos_pendentes"] = ["cnpj"]

    resultado = avaliar_recebimento(
        alerta,
        recebimento_base(lote="153"),
    )

    assert resultado["match"] is False
    assert resultado["resultado"] == "verificacao_pendente"


def test_cnpj_igual_com_marca_divergente_exige_revisao():
    alerta = alerta_base(
        "lista",
        lotes=["153"],
    )

    recebimento = recebimento_base(
        lote="153",
        marca="Marca diferente",
        cnpj="02896434000147",
    )

    resultado = avaliar_recebimento(alerta, recebimento)

    assert resultado["match"] is True
    assert resultado["revisao_manual"] is True
    assert (
        "marca_divergente_cnpj_compativel"
        in resultado["motivos"]
    )


def test_cnpj_diferente_nao_deve_gerar_match():
    alerta = alerta_base(
        "lista",
        lotes=["153"],
    )

    recebimento = recebimento_base(
        lote="153",
        cnpj="11.111.111/0001-11",
    )

    resultado = avaliar_recebimento(alerta, recebimento)

    assert resultado["match"] is False
    assert resultado["resultado"] == "sem_match"
