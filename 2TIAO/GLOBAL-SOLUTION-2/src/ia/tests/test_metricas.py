import pytest

from ia.avaliacao.metricas import (
    chave_lote, comparar_regra, comparar_registro, digitos, falha_de_servico, norm_fabricante,
    norm_texto, parear, trecho_de_suporte, valor_no_texto,
)


def reg(produto, cnpj="11.222.333/0001-81", lotes=("1",), alerta_id="g", marca="M", fabricante="F"):
    return {"alerta_id": alerta_id, "produto": produto, "marca": marca, "fabricante": fabricante, "cnpj": cnpj,
            "regra_lote": {"tipo": "lista", "lotes": list(lotes), "sufixo": None, "fabricado_ate": None}}


@pytest.mark.parametrize("a, b", [
    ("NAN Supreme Pro, 0–6 meses, 400 g", "NAN SUPREME PRO 0-6 Meses 400g"),
    ("Água Mineral sem Gás", "agua mineral SEM GAS"),
])
def test_norm_texto_iguala_formatacao(a, b):
    assert norm_texto(a) == norm_texto(b)


def test_norm_fabricante_remove_parenteses():
    assert norm_fabricante("BL Indústria Ótica Ltda. (Bausch Lomb)") == norm_fabricante("BL INDUSTRIA OTICA LTDA")


def test_cnpj_por_digitos_e_lote_sem_espacos():
    assert digitos("26.726.809/0001-99") == digitos("26726809000199")
    assert chave_lote("183/3 B") == chave_lote("183/3b")
    assert chave_lote("07225288") != chave_lote("7225288")  # zeros à esquerda contam


@pytest.mark.parametrize("g, e, ok", [
    ({"tipo": "lista", "lotes": ["183/3B"]}, {"tipo": "lista", "lotes": ["183/3 B"]}, True),
    ({"tipo": "lista", "lotes": ["1", "2"]}, {"tipo": "lista", "lotes": ["2", "1"]}, True),
    ({"tipo": "lista", "lotes": ["1", "2"]}, {"tipo": "lista", "lotes": ["1"]}, False),
    ({"tipo": "data_corte", "fabricado_ate": "2026-06-12"}, {"tipo": "data_corte", "fabricado_ate": "2026-06-13"}, False),
    ({"tipo": "todos"}, {"tipo": "todos"}, True),
    ({"tipo": None}, {"tipo": "todos"}, False),
    ({"tipo": None}, {"tipo": None}, True),
])
def test_comparar_regra(g, e, ok):
    base = {"lotes": [], "sufixo": None, "fabricado_ate": None}
    assert comparar_regra({**base, **g}, {**base, **e}) is ok


def test_comparar_registro_nulos_iguais_contam_como_acerto():
    g = reg("X", cnpj=None, marca=None)
    assert all(comparar_registro(g, reg("x", cnpj=None, marca=None)).values())


def test_parear_por_produto_e_cnpj_sem_usar_lote():
    gab = [reg("NAN Supreme Pro 400 g", alerta_id="g400"), reg("NAN Supreme Pro 800 g", alerta_id="g800")]
    ext = [reg("NAN SUPREME PRO 800G", lotes=("errado",)), reg("NAN SUPREME PRO 400G")]
    pares, _ = parear(gab, ext)
    assert {gi: ei for gi, (ei, _) in pares.items()} == {0: 1, 1: 0}


def test_parear_no_maximo_um_e_cnpj_incompativel_nao_pareia():
    gab = [reg("Biscoito", alerta_id="a"), reg("Biscoito", alerta_id="b")]
    pares, ambiguos = parear(gab, [reg("Biscoito")])
    assert len(pares) == 1  # o outro registro fica sem par (falso negativo)
    pares, _ = parear([reg("Biscoito")], [reg("Biscoito", cnpj="99.999.999/0001-99")])
    assert pares == {}


def test_parear_registra_ambiguidade():
    gab = [reg("Panetone Gotas", alerta_id="p")]
    _, ambiguos = parear(gab, [reg("Panetone Gotas"), reg("Panetone Gotas")])
    assert ambiguos and ambiguos[0].startswith("p:")


def test_parear_abaixo_do_limiar_fica_sem_par():
    pares, _ = parear([reg("Molho de tomate")], [reg("Suplemento vitamínico")])
    assert pares == {}


def test_trecho_de_suporte_por_lote_por_produto_e_sem_suporte():
    texto = "Título\nRecolhimento do lote 183/3 B do leite condensado.\nOutro parágrafo."
    assert "183/3 B" in trecho_de_suporte({"produto": "x", "regra_lote": {"lotes": ["183/3B"]}}, texto)
    assert trecho_de_suporte({"produto": "Leite Condensado", "regra_lote": {"lotes": []}}, texto)
    assert trecho_de_suporte({"produto": "Queijo minas", "regra_lote": {"lotes": ["999"]}}, texto) is None


@pytest.mark.parametrize("motivo, servico", [
    ("orcamento_esgotado", True), ("modelos_esgotados", True), ("erro_llm:RuntimeError", True),
    ("json_invalido", False), (None, False),
])
def test_falha_de_servico(motivo, servico):
    assert falha_de_servico(motivo) is servico


def test_valor_no_texto_separa_dado_de_outra_fonte():
    texto = "Recolhimento do lote 183/3 B do Leite Condensado, da Multlac Ltda. (CNPJ 02.389.692/0001-37). Validade 12/06/2026."
    g = reg("Leite Condensado", cnpj="02389692000137", lotes=("183/3B",), fabricante="Multlac Ltda. (anotação)")
    assert valor_no_texto("cnpj", g, texto) and valor_no_texto("regra", g, texto)
    assert valor_no_texto("produto", g, texto) and valor_no_texto("fabricante", g, texto)
    assert not valor_no_texto("cnpj", {**g, "cnpj": "60.409.075/0001-52"}, texto)
    assert not valor_no_texto("regra", {**g, "regra_lote": {"tipo": "todos"}}, texto)
    corte = {**g, "regra_lote": {"tipo": "data_corte", "fabricado_ate": "2026-06-12"}}
    assert valor_no_texto("regra", corte, texto)
