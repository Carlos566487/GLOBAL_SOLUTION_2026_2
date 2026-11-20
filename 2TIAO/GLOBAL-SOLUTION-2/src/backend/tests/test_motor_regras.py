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



# --- Escopo categoria_fabricante (contrato v2) -----------------------------

def alerta_categoria(**extra):
    alerta = {
        "alerta_id": "sanibras",
        "produto": "Suplementos alimentares do fabricante",
        "marca": "Sanibras",
        "fabricante": "Sanibras Medicamentos e Nutrição Ltda.",
        "cnpj": "82.268.269/0001-18",
        "escopo": "categoria_fabricante",
        "categoria": "suplemento",
        "status_extracao": "ok",
        "campos_pendentes": [],
        "regra_lote": {"tipo": "data_corte", "lotes": [], "sufixo": None, "fabricado_ate": "2026-06-12"},
    }
    alerta.update(extra)
    return alerta


def recebimento_suplemento(**dados):
    recebimento = {
        "loja_id": "LOJA-A",
        "produto": "Whey Protein 900 g",
        "marca": "Sanibras",
        "fabricante": "Sanibras Medicamentos e Nutrição Ltda.",
        "cnpj": "82.268.269/0001-18",
        "categoria": "suplemento",
        "lote": "X1",
        "data_fabricacao": "2026-06-10",
    }
    recebimento.update(dados)
    return recebimento


def test_categoria_fabricante_ignora_nome_comercial():
    r = avaliar_recebimento(alerta_categoria(), recebimento_suplemento())
    assert r["resultado"] == "match"


def test_categoria_fabricante_preserva_data_de_corte():
    r = avaliar_recebimento(alerta_categoria(), recebimento_suplemento(data_fabricacao="2026-06-13"))
    assert r["resultado"] == "sem_match"
    r = avaliar_recebimento(alerta_categoria(), recebimento_suplemento(data_fabricacao=None))
    assert r["resultado"] == "verificacao_pendente"


def test_categoria_fabricante_cnpj_diferente_nao_casa():
    r = avaliar_recebimento(alerta_categoria(), recebimento_suplemento(cnpj="11.111.111/0001-11"))
    assert r["resultado"] == "sem_match"


def test_categoria_fabricante_categoria_diferente_nao_casa():
    r = avaliar_recebimento(alerta_categoria(), recebimento_suplemento(categoria="medicamento"))
    assert r["resultado"] == "sem_match"


def test_categoria_fabricante_sem_categoria_fica_pendente():
    r = avaliar_recebimento(alerta_categoria(), recebimento_suplemento(categoria=None))
    assert r["resultado"] == "verificacao_pendente"
    assert r["motivos"] == ["categoria"]


def test_categoria_fabricante_sem_cnpj_usa_razao_social():
    r = avaliar_recebimento(alerta_categoria(), recebimento_suplemento(cnpj=None))
    assert r["resultado"] == "match"
    r = avaliar_recebimento(alerta_categoria(), recebimento_suplemento(cnpj=None, fabricante=None))
    assert r["resultado"] == "verificacao_pendente"
    assert r["motivos"] == ["fabricante"]
