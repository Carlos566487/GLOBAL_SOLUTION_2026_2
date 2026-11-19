from types import SimpleNamespace

import pytest
from google.genai import errors

from ia import config, gemini


def erro(codigo):
    return errors.APIError(codigo, {"error": {"code": codigo, "message": "teste", "status": "X"}})


class Relogio:
    """Relógio falso: avança com as esperas e com o custo de cada chamada."""

    def __init__(self):
        self.agora = 0.0

    def __call__(self):
        return self.agora

    def dormir(self, segundos):
        self.agora += segundos


class ClienteFalso:
    """Devolve, em ordem, os itens de `roteiro`: exceção ou texto. Cada chamada custa `custo` s."""

    def __init__(self, roteiro, relogio=None, custo=0.0):
        self.roteiro = list(roteiro)
        self.chamadas, self.timeouts = [], []
        self.relogio, self.custo = relogio, custo
        self.models = self

    def generate_content(self, model, contents, config):
        self.chamadas.append(model)
        self.timeouts.append(config.http_options.timeout)
        if self.relogio:  # uma chamada real nunca passa do próprio timeout
            self.relogio.agora += min(self.custo, config.http_options.timeout / 1000)
        item = self.roteiro.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(text=item, model_version=f"{model}-v")


@pytest.fixture(autouse=True)
def modelos(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_MODEL", "principal")
    monkeypatch.setattr(config, "GEMINI_FALLBACK_MODELS", ["reserva-1", "reserva-2"])


def chamar(cliente, relogio=None, **kwargs):
    relogio = relogio or Relogio()
    resposta = gemini.gerar_json(
        "sis", ["txt"], {"type": "object"}, cliente=cliente, dormir=relogio.dormir, relogio=relogio, **kwargs
    )
    return resposta, relogio


def test_responde_na_primeira():
    r, relogio = chamar(ClienteFalso(['{"a": 1}']))
    assert (r.texto, r.modelo, relogio.agora) == ('{"a": 1}', "principal", 0)


@pytest.mark.parametrize("codigo", [429, 500, 503])
def test_codigos_retentaveis_ficam_no_mesmo_modelo(codigo):
    r, relogio = chamar(ClienteFalso([erro(codigo), "{}"]))
    assert [t["codigo"] for t in r.tentativas] == [codigo, 200]
    assert r.modelo == "principal" and relogio.agora == 2


def test_retenta_com_espera_crescente():
    r, relogio = chamar(ClienteFalso([erro(503), erro(429), erro(500), "{}"]))
    assert r.modelo == "principal"
    assert relogio.agora == 2 + 4 + 8


@pytest.mark.parametrize("falha", [lambda: erro(504), lambda: gemini.EXCECOES_TIMEOUT[0]("lento")],
                         ids=["504", "timeout"])
def test_504_e_timeout_passam_direto_ao_proximo_modelo(falha):
    cliente = ClienteFalso([falha(), "{}"])
    r, relogio = chamar(cliente)
    assert cliente.chamadas == ["principal", "reserva-1"]
    assert r.modelo == "reserva-1"
    assert relogio.agora == 0  # sem espera ao trocar de modelo


def test_mistura_retentativa_e_troca_de_modelo():
    cliente = ClienteFalso([erro(503), erro(504), erro(429), "{}"])
    r, relogio = chamar(cliente)
    assert cliente.chamadas == ["principal", "principal", "reserva-1", "reserva-1"]
    assert r.modelo == "reserva-1" and relogio.agora == 2 + 2


def test_timeout_por_chamada_limitado_a_30s_e_ao_orcamento_restante():
    relogio = Relogio()
    cliente = ClienteFalso([erro(503), erro(503), "{}"], relogio=relogio, custo=30)
    chamar(cliente, relogio)
    # 1ª: 30 s (sobram 90); 2ª: após 30 + 2 s, sobram 58 → 30 s; 3ª: após 62 + 4, sobram 24 → 24 s
    assert cliente.timeouts == [30_000, 30_000, 24_000]


def test_usa_fallback_quando_principal_esgota():
    cliente = ClienteFalso([erro(503)] * 4 + ["{}"])
    r, _ = chamar(cliente)
    assert r.modelo == "reserva-1"
    assert cliente.chamadas == ["principal"] * 4 + ["reserva-1"]


def test_modelo_fixo_com_504_nao_tenta_outro():
    cliente = ClienteFalso([erro(504)])
    with pytest.raises(gemini.LLMIndisponivel) as exc:
        chamar(cliente, modelos=["principal"])
    assert exc.value.motivo == "modelos_esgotados" and cliente.chamadas == ["principal"]


def test_modelo_fixo_desliga_o_fallback():
    cliente = ClienteFalso([erro(503)] * 4)
    with pytest.raises(gemini.LLMIndisponivel) as exc:
        chamar(cliente, modelos=["principal"])
    assert exc.value.motivo == "modelos_esgotados"
    assert set(cliente.chamadas) == {"principal"}


def test_orcamento_esgotado():
    relogio = Relogio()
    cliente = ClienteFalso([erro(503)] * 12, relogio=relogio, custo=30)
    with pytest.raises(gemini.LLMIndisponivel) as exc:
        chamar(cliente, relogio)
    assert exc.value.motivo == "orcamento_esgotado"
    assert relogio.agora <= config.ORCAMENTO_EXTRACAO_S


def test_todos_esgotados_levanta_indisponivel():
    with pytest.raises(gemini.LLMIndisponivel) as exc:
        chamar(ClienteFalso([erro(503)] * 12))
    assert len(exc.value.tentativas) == 12


def test_erro_nao_retentavel_sobe_sem_retentar():
    cliente = ClienteFalso([erro(400)])
    with pytest.raises(errors.APIError):
        chamar(cliente)
    assert cliente.chamadas == ["principal"]


def test_modelos_sem_repeticao(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_FALLBACK_MODELS", ["principal", "reserva-1"])
    assert gemini.modelos_em_ordem() == ["principal", "reserva-1"]
