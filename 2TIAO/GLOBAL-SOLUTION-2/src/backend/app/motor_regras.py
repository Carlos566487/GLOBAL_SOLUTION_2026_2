from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any


TIPOS_REGRA = {"lista", "sufixo", "data_corte", "todos"}
ESCOPO_CATEGORIA_FABRICANTE = "categoria_fabricante"


def normalizar_lote(valor: str | None) -> str | None:
    """
    Lotes são comparados sem espaços e em maiúsculas.

    Exemplo:
        "183/3 B" -> "183/3B"
    """
    if valor is None:
        return None

    normalizado = re.sub(r"\s+", "", str(valor)).upper()

    return normalizado or None


def normalizar_cnpj(valor: str | None) -> str | None:
    """
    Mantém somente os dígitos do CNPJ.
    """
    if valor is None:
        return None

    digitos = re.sub(r"\D", "", str(valor))

    return digitos or None


def normalizar_texto(valor: str | None) -> str | None:
    """
    Normalização simples para comparação de produto e marca.
    Remove diferenças de caixa, acentos, pontuação e espaços extras.
    """
    if valor is None:
        return None

    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    texto = texto.casefold()
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto or None


def converter_data(valor: str | date | datetime | None) -> date | None:
    """
    Converte data ISO YYYY-MM-DD para date.
    """
    if valor is None:
        return None

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        return None


def _identidade_produto(
    alerta: dict[str, Any],
    recebimento: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Confere se alerta e recebimento representam o mesmo produto.

    Quando ambos possuem CNPJ, ele é a principal identidade do fabricante.
    Se o CNPJ for igual mas a marca divergir, o recebimento continua
    candidato ao match, porém exige revisão humana.

    Retorna:
        (identidade_compativel, motivos_revisao)
    """
    revisoes: list[str] = []

    produto_alerta = normalizar_texto(alerta.get("produto"))
    produto_recebimento = normalizar_texto(recebimento.get("produto"))

    if (
        produto_alerta
        and produto_recebimento
        and produto_alerta != produto_recebimento
    ):
        return False, []

    cnpj_alerta = normalizar_cnpj(alerta.get("cnpj"))
    cnpj_recebimento = normalizar_cnpj(recebimento.get("cnpj"))

    marca_alerta = normalizar_texto(alerta.get("marca"))
    marca_recebimento = normalizar_texto(recebimento.get("marca"))

    if cnpj_alerta and cnpj_recebimento:
        if cnpj_alerta != cnpj_recebimento:
            return False, []

        if (
            marca_alerta
            and marca_recebimento
            and marca_alerta != marca_recebimento
        ):
            revisoes.append("marca_divergente_cnpj_compativel")

        return True, revisoes

    if marca_alerta and marca_recebimento:
        if marca_alerta != marca_recebimento:
            return False, []

    return True, revisoes


def _identidade_categoria_fabricante(
    alerta: dict[str, Any],
    recebimento: dict[str, Any],
) -> tuple[str, list[str], list[dict[str, Any]]]:
    """
    Identidade para alertas com escopo ``categoria_fabricante`` (contrato v2).

    Confirma o FABRICANTE (CNPJ; sem CNPJ em um dos lados, razão social
    normalizada) e a CATEGORIA. O nome comercial do produto não é usado.

    Retorna ``(situacao, motivos, comparacoes)``:
        - ``"confirmada"``: mesmo fabricante e mesma categoria;
        - ``"diferente"``: fabricante ou categoria comprovadamente diferentes;
        - ``"pendente"``: algum dado necessário está ausente. Na dúvida, o
          motor nunca presume que o produto está fora do recall.
    """
    pendentes: list[str] = []
    comparacoes: list[dict[str, Any]] = []

    # 1) Fabricante: CNPJ tem prioridade; razão social é o fallback.
    cnpj_alerta = normalizar_cnpj(alerta.get("cnpj"))
    cnpj_recebimento = normalizar_cnpj(recebimento.get("cnpj"))

    if cnpj_alerta and cnpj_recebimento:
        comparacoes.append({
            "campo": "cnpj",
            "operador": "igual",
            "valor_alerta": alerta.get("cnpj"),
            "valor_recebimento": recebimento.get("cnpj"),
        })
        if cnpj_alerta != cnpj_recebimento:
            return "diferente", [], comparacoes
    else:
        fabricante_alerta = normalizar_texto(alerta.get("fabricante"))
        fabricante_recebimento = normalizar_texto(recebimento.get("fabricante"))

        if fabricante_alerta and fabricante_recebimento:
            comparacoes.append({
                "campo": "fabricante",
                "operador": "igual",
                "valor_alerta": alerta.get("fabricante"),
                "valor_recebimento": recebimento.get("fabricante"),
            })
            if fabricante_alerta != fabricante_recebimento:
                return "diferente", [], comparacoes
        else:
            pendentes.append("fabricante")

    # 2) Categoria do produto.
    categoria_alerta = normalizar_texto(alerta.get("categoria"))
    categoria_recebimento = normalizar_texto(recebimento.get("categoria"))

    if categoria_alerta and categoria_recebimento:
        comparacoes.append({
            "campo": "categoria",
            "operador": "igual",
            "valor_alerta": alerta.get("categoria"),
            "valor_recebimento": recebimento.get("categoria"),
        })
        if categoria_alerta != categoria_recebimento:
            return "diferente", [], comparacoes
    else:
        pendentes.append("categoria")

    if pendentes:
        return "pendente", pendentes, comparacoes

    return "confirmada", [], comparacoes


def avaliar_recebimento(
    alerta: dict[str, Any],
    recebimento: dict[str, Any],
) -> dict[str, Any]:
    """
    Aplica uma regra de recall a um recebimento.

    O LLM não participa desta decisão.
    """
    if alerta.get("status_extracao") != "ok":
        return {
            "resultado": "verificacao_pendente",
            "motivos": list(alerta.get("campos_pendentes") or []),
            "match": False,
            "revisao_manual": True,
            "evidencia": None,
        }

    campos_pendentes = alerta.get("campos_pendentes") or []

    if campos_pendentes:
        return {
            "resultado": "verificacao_pendente",
            "motivos": list(campos_pendentes),
            "match": False,
            "revisao_manual": True,
            "evidencia": None,
        }

    regra = alerta.get("regra_lote") or {}
    tipo = regra.get("tipo")

    if tipo not in TIPOS_REGRA:
        return {
            "resultado": "verificacao_pendente",
            "motivos": ["regra_lote.tipo"],
            "match": False,
            "revisao_manual": True,
            "evidencia": None,
        }

    if alerta.get("escopo") == ESCOPO_CATEGORIA_FABRICANTE:
        # Recall de uma categoria inteira do fabricante (ex.: "todos os
        # suplementos da Sanibras"): o nome comercial do recebimento
        # ("Whey Protein 900 g") não precisa coincidir com a descrição
        # genérica do alerta. A identidade é fabricante + categoria.
        situacao, motivos, comparacoes = _identidade_categoria_fabricante(
            alerta,
            recebimento,
        )

        if situacao == "pendente":
            return {
                "resultado": "verificacao_pendente",
                "motivos": motivos,
                "match": False,
                "revisao_manual": True,
                "evidencia": comparacoes,
            }

        if situacao == "diferente":
            return {
                "resultado": "sem_match",
                "motivos": [],
                "match": False,
                "revisao_manual": False,
                "evidencia": comparacoes,
            }

        # Identidade confirmada: aplica a regra de lote/data normalmente e
        # anexa à evidência as comparações de fabricante e categoria.
        resultado = avaliar_recebimento(
            {**alerta, "escopo": "produto"},
            {
                **recebimento,
                "produto": alerta.get("produto"),
                "marca": alerta.get("marca"),
                "cnpj": alerta.get("cnpj"),
            },
        )
        if isinstance(resultado.get("evidencia"), dict):
            resultado["evidencia"] = {
                **resultado["evidencia"],
                "identidade": comparacoes,
            }
        return resultado
    else:
        identidade_compativel, revisoes = _identidade_produto(
            alerta,
            recebimento,
        )

        if not identidade_compativel:
            return {
                "resultado": "sem_match",
                "motivos": [],
                "match": False,
                "revisao_manual": False,
                "evidencia": {
                    "campo": "identidade_produto",
                    "valor_alerta": alerta.get("produto"),
                    "valor_recebimento": recebimento.get("produto"),
                },
            }

    if tipo == "todos":
        return {
            "resultado": "match",
            "motivos": revisoes,
            "match": True,
            "revisao_manual": bool(revisoes),
            "evidencia": {
                "campo": "regra_lote.tipo",
                "valor_alerta": "todos",
                "valor_recebimento": "todos",
            },
        }

    if tipo == "lista":
        lote_recebimento = normalizar_lote(recebimento.get("lote"))

        if not lote_recebimento:
            return {
                "resultado": "verificacao_pendente",
                "motivos": ["lote"],
                "match": False,
                "revisao_manual": True,
                "evidencia": None,
            }

        lotes_alerta = {
            lote_normalizado
            for lote in regra.get("lotes") or []
            if (lote_normalizado := normalizar_lote(lote))
        }

        encontrou = lote_recebimento in lotes_alerta

        return {
            "resultado": "match" if encontrou else "sem_match",
            "motivos": revisoes,
            "match": encontrou,
            "revisao_manual": bool(revisoes) and encontrou,
            "evidencia": {
                "campo": "lote",
                "valor_alerta": regra.get("lotes") or [],
                "valor_recebimento": recebimento.get("lote"),
            },
        }

    if tipo == "sufixo":
        lote_recebimento = normalizar_lote(recebimento.get("lote"))
        sufixo_alerta = normalizar_lote(regra.get("sufixo"))

        if not lote_recebimento:
            return {
                "resultado": "verificacao_pendente",
                "motivos": ["lote"],
                "match": False,
                "revisao_manual": True,
                "evidencia": None,
            }

        if not sufixo_alerta:
            return {
                "resultado": "verificacao_pendente",
                "motivos": ["regra_lote.sufixo"],
                "match": False,
                "revisao_manual": True,
                "evidencia": None,
            }

        encontrou = lote_recebimento.endswith(sufixo_alerta)

        return {
            "resultado": "match" if encontrou else "sem_match",
            "motivos": revisoes,
            "match": encontrou,
            "revisao_manual": bool(revisoes) and encontrou,
            "evidencia": {
                "campo": "lote_sufixo",
                "valor_alerta": regra.get("sufixo"),
                "valor_recebimento": recebimento.get("lote"),
            },
        }

    data_recebimento = converter_data(
        recebimento.get("data_fabricacao")
    )
    data_limite = converter_data(regra.get("fabricado_ate"))

    if data_recebimento is None:
        return {
            "resultado": "verificacao_pendente",
            "motivos": ["data_fabricacao"],
            "match": False,
            "revisao_manual": True,
            "evidencia": None,
        }

    if data_limite is None:
        return {
            "resultado": "verificacao_pendente",
            "motivos": ["regra_lote.fabricado_ate"],
            "match": False,
            "revisao_manual": True,
            "evidencia": None,
        }

    encontrou = data_recebimento <= data_limite

    return {
        "resultado": "match" if encontrou else "sem_match",
        "motivos": revisoes,
        "match": encontrou,
        "revisao_manual": bool(revisoes) and encontrou,
        "evidencia": {
            "campo": "data_fabricacao",
            "valor_alerta": regra.get("fabricado_ate"),
            "valor_recebimento": recebimento.get(
                "data_fabricacao"
            ),
        },
    }