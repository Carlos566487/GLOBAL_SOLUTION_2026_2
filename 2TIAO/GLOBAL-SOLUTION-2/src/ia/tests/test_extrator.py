import json

import pytest

from ia import config, gemini
from ia.extrator import extrair_alertas, extrair_alertas_detalhado, mascarar_dados_pessoais

URL = "https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2026/teste"
HASH = "sha256:" + "ab" * 32
TEXTO = "A Anvisa determinou o recolhimento do lote 004512 do Biscoito Doce Vale."

ITEM = {
    "produto": "Biscoito Recheado Morango, 120 g",
    "marca": "Doce Vale",
    "fabricante": "Doce Vale Alimentos Ltda.",
    "cnpj": "98.765.432/0001-10",
    "escopo": "produto",
    "categoria": None,
    "regra_lote": {"tipo": "lista", "lotes": ["004512", "B 77/2"], "sufixo": None, "fabricado_ate": None},
    "campos_pendentes": [],
}


def gerador_que_responde(texto_json, recebido=None):
    def gerar(sistema, conteudo, schema, modelos=None):
        if recebido is not None:
            recebido.update(conteudo=conteudo, modelos=modelos)
        return gemini.RespostaLLM(texto_json, "modelo-x", "modelo-x-001", [{"modelo": "modelo-x", "codigo": 200}])
    return gerar


def gerador_que_falha(erro):
    def gerar(*args, **kwargs):
        raise erro
    return gerar


def extrair(gerador, texto=TEXTO, url=URL, hash_=HASH, **kw):
    return extrair_alertas_detalhado(texto, url, hash_, gerador=gerador, **kw)


# --- caminho feliz ----------------------------------------------------------

def test_extrai_e_valida_preenchendo_fonte_e_modelo():
    r = extrair(gerador_que_responde(json.dumps({"alertas": [ITEM]})))
    assert r.motivo_falha is None
    assert (r.modelo, r.versao_modelo) == ("modelo-x", "modelo-x-001")
    [a] = r.alertas
    assert (a.fonte_url, a.fonte_hash, a.status_extracao) == (URL, HASH, "ok")
    assert a.regra_lote.lotes == ["004512", "B 77/2"]


def test_varios_alertas_com_ids_unicos_e_deterministicos():
    resposta = json.dumps({"alertas": [ITEM, ITEM, {**ITEM, "produto": "Outro"}]})
    ids1 = [a.alerta_id for a in extrair(gerador_que_responde(resposta)).alertas]
    ids2 = [a.alerta_id for a in extrair(gerador_que_responde(resposta)).alertas]
    assert ids1 == ids2
    assert len(set(ids1)) == 3
    assert ids1[0].startswith("doce-vale-biscoito-recheado-morango-120-g-")


def test_validador_corrige_status_otimista_do_llm():
    item = {**ITEM, "cnpj": None, "campos_pendentes": []}
    [a] = extrair(gerador_que_responde(json.dumps({"alertas": [item]}))).alertas
    assert a.status_extracao == "verificacao_pendente" and a.campos_pendentes == ["cnpj"]


def test_fonte_hash_none_e_aceito():
    [a] = extrair(gerador_que_responde(json.dumps({"alertas": [ITEM]})), hash_=None).alertas
    assert a.fonte_hash is None and a.status_extracao == "ok"


def test_modelos_repassados_ao_gerador():
    recebido = {}
    extrair(gerador_que_responde(json.dumps({"alertas": [ITEM]}), recebido), modelos=["fixo"])
    assert recebido["modelos"] == ["fixo"]


# --- falhas viram pendente, nunca exceção ------------------------------------

def pendente_unico(r, motivo):
    [a] = r.alertas
    assert a.status_extracao == "verificacao_pendente"
    assert f"extracao:{motivo}" in a.campos_pendentes
    assert a.fonte_url == URL
    return a


@pytest.mark.parametrize("resposta", ["não é json", "{}", '{"alertas": "x"}'])
def test_json_invalido(resposta):
    r = extrair(gerador_que_responde(resposta))
    assert r.motivo_falha == "json_invalido"
    pendente_unico(r, "json_invalido")


def test_lista_vazia_vira_pendente_para_revisao():
    r = extrair(gerador_que_responde('{"alertas": []}'))
    pendente_unico(r, "nenhum_alerta_extraido")


def test_item_fora_do_schema_vira_pendente_e_os_outros_seguem():
    ruim = {**ITEM, "regra_lote": {"tipo": "lista", "lotes": [4512]}}
    r = extrair(gerador_que_responde(json.dumps({"alertas": [ITEM, ruim]})))
    ok, pendente = r.alertas
    assert ok.status_extracao == "ok"
    assert "extracao:item_invalido" in pendente.campos_pendentes
    assert pendente.produto == ITEM["produto"]  # o que era legível é preservado


def test_llm_indisponivel_registra_motivo():
    tentativas = [{"modelo": "a", "codigo": 503}]
    r = extrair(gerador_que_falha(gemini.LLMIndisponivel(tentativas, "orcamento_esgotado")))
    assert r.motivo_falha == "orcamento_esgotado" and r.tentativas == tentativas
    pendente_unico(r, "orcamento_esgotado")


def test_erro_inesperado_do_llm_vira_pendente():
    r = extrair(gerador_que_falha(RuntimeError("GEMINI_API_KEY não definida")))
    assert r.motivo_falha == "erro_llm:RuntimeError"
    pendente_unico(r, "erro_llm:RuntimeError")


def test_texto_vazio():
    r = extrair(gerador_que_falha(AssertionError("não deveria chamar")), texto="   ")
    pendente_unico(r, "texto_vazio")


def test_fonte_hash_invalido():
    r = extrair(gerador_que_falha(AssertionError("não deveria chamar")), hash_="md5:123")
    a = pendente_unico(r, "fonte_hash_invalido")
    assert a.fonte_hash is None


@pytest.mark.parametrize("url", ["https://portal-nao-oficial.com.br/x", None, 123])
def test_fonte_nao_oficial_nao_gera_alerta(url):
    r = extrair(gerador_que_falha(AssertionError("não deveria chamar")), url=url)
    assert r.alertas == [] and r.motivo_falha == "fonte_nao_oficial"
    assert r.fonte_recusada == str(url)


def test_interface_simples_devolve_lista_vazia_para_fonte_nao_oficial():
    assert extrair_alertas(TEXTO, "https://portal-nao-oficial.com.br/x", None) == []


def test_interface_simples_nunca_levanta(monkeypatch):
    monkeypatch.setattr(gemini, "_cliente_padrao", lambda: (_ for _ in ()).throw(RuntimeError("sem chave")))
    [a] = extrair_alertas(TEXTO, URL, None)
    assert a.status_extracao == "verificacao_pendente"


# --- privacidade -------------------------------------------------------------

def test_dados_pessoais_mascarados_antes_do_envio():
    recebido = {}
    texto = TEXTO + " Contato: maria@exemplo.com, (11) 98765-4321, CPF 123.456.789-09."
    extrair(gerador_que_responde(json.dumps({"alertas": [ITEM]}), recebido), texto=texto)
    enviado = recebido["conteudo"][-1].parts[0].text
    assert "maria@exemplo.com" not in enviado and "98765-4321" not in enviado and "123.456.789-09" not in enviado
    assert "004512" in enviado


@pytest.mark.parametrize("trecho", ["lote 13099022444", "CNPJ 07.171.099/0001-33", "lote 21/08/2026", "07225288"])
def test_mascara_nao_altera_lotes_nem_cnpj(trecho):
    assert mascarar_dados_pessoais(trecho) == trecho


# --- integração real (pulada sem chave) -------------------------------------

@pytest.mark.skipif(not config.GEMINI_API_KEY, reason="GEMINI_API_KEY não definida")
def test_integracao_gemini_texto_ficticio():
    texto = ("[TEXTO FICTÍCIO] A Anvisa determinou o recolhimento dos lotes 004512 e B 77/2 do Biscoito "
             "Recheado Morango 120 g, marca Doce Vale, da Doce Vale Alimentos Ltda. (CNPJ 98.765.432/0001-10).")
    r = extrair_alertas_detalhado(texto, URL, None)
    if r.motivo_falha in ("orcamento_esgotado", "modelos_esgotados"):
        pytest.skip(f"serviço indisponível: {r.tentativas}")
    assert r.motivo_falha is None, r.motivo_falha
    assert any(set(a.regra_lote.lotes) == {"004512", "B 77/2"} for a in r.alertas)


def test_linha_de_comando_imprime_alertas(tmp_path, monkeypatch, capsys):
    from ia import extrator

    arquivo = tmp_path / "alerta.txt"
    arquivo.write_text(TEXTO, encoding="utf-8")
    original = extrator.extrair_alertas_detalhado
    monkeypatch.setattr(extrator, "extrair_alertas_detalhado", lambda t, u, h: original(
        t, u, h, gerador=gerador_que_responde(json.dumps({"alertas": [ITEM]}))))
    extrator.main([str(arquivo), "--url", URL])
    saida = json.loads(capsys.readouterr().out)
    assert saida["modelo"] == "modelo-x"
    assert saida["alertas"][0]["regra_lote"]["lotes"] == ["004512", "B 77/2"]
