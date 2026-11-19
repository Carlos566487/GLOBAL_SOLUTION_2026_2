from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.app.motor_regras import avaliar_recebimento, normalizar_texto
from backend.app.repositorio import (
    adicionar_alerta,
    adicionar_match,
    alertas,
    buscar_match,
    matches,
)
from backend.app.schemas_api import (
    ColetaAlerta,
    DecisaoMatch,
    ProcessamentoMotor,
)
from ia.embalagem import ler_embalagem
from ia.extrator import extrair_alertas


app = FastAPI(
    title="Recall de Alimentos API",
    description=(
        "API da POC CitizenTech para cruzamento determinístico "
        "de alertas de recall de alimentos."
    ),
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


CATALOGO_DEMO = {
    "2000000001531": ("Ricota Fresca", "Vaidosa"),
}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "servico": "backend-recall",
    }


@app.get("/alertas")
def listar_alertas():
    return {
        "total": len(alertas),
        "alertas": alertas,
    }


@app.get("/matches")
def listar_matches(
    alerta_id: str | None = Query(default=None),
):
    resultado = matches

    if alerta_id:
        resultado = [
            match
            for match in matches
            if match.get("alerta_id") == alerta_id
        ]

    return {
        "total": len(resultado),
        "matches": resultado,
    }


@app.post("/alertas/coletar")
def coletar_alertas(dados: ColetaAlerta):
    extraidos = extrair_alertas(
        texto=dados.texto,
        fonte_url=dados.fonte_url,
        fonte_hash=dados.fonte_hash,
    )

    alertas_ok = []
    pendentes = []

    for item in extraidos:
        if hasattr(item, "model_dump"):
            alerta = item.model_dump(mode="json")
        else:
            alerta = dict(item)

        alerta_id = alerta.get("alerta_id")

        if alerta_id and not any(
            existente.get("alerta_id") == alerta_id
            for existente in alertas
        ):
            adicionar_alerta(alerta)

        if (
            alerta.get("status_extracao") == "ok"
            and not alerta.get("campos_pendentes")
        ):
            alertas_ok.append(alerta)
        else:
            pendentes.append(alerta)

    return {
        "total_extraidos": len(extraidos),
        "alertas_ok": alertas_ok,
        "pendentes": pendentes,
    }


@app.post("/motor/processar")
def processar_motor(dados: ProcessamentoMotor):
    alerta = dados.alerta

    alerta_id = alerta.get("alerta_id")

    if not alerta_id:
        raise HTTPException(
            status_code=422,
            detail="O alerta precisa possuir alerta_id.",
        )

    if not any(
        item.get("alerta_id") == alerta_id
        for item in alertas
    ):
        adicionar_alerta(alerta)

    resultados = []
    matches_criados = []
    pendentes = []

    for recebimento in dados.recebimentos:
        avaliacao = avaliar_recebimento(
            alerta,
            recebimento,
        )

        resultado_recebimento = {
            "loja_id": recebimento.get("loja_id"),
            "resultado": avaliacao["resultado"],
            "match": avaliacao["match"],
            "revisao_manual": avaliacao["revisao_manual"],
            "motivos": avaliacao["motivos"],
            "evidencia": avaliacao["evidencia"],
        }

        resultados.append(resultado_recebimento)

        if avaliacao["resultado"] == "verificacao_pendente":
            pendentes.append(resultado_recebimento)
            continue

        if not avaliacao["match"]:
            continue

        match = {
            "match_id": f"m-{uuid4().hex[:8]}",
            "alerta_id": alerta_id,
            "loja_id": recebimento.get("loja_id"),
            "regra_aplicada": (
                alerta.get("regra_lote") or {}
            ).get("tipo"),
            "evidencia": avaliacao["evidencia"],
            "revisao_manual": avaliacao["revisao_manual"],
            "motivos_revisao": avaliacao["motivos"],
            "status": "aguardando_aprovacao",
        }

        adicionar_match(match)
        matches_criados.append(match)

    return {
        "alerta_id": alerta_id,
        "recebimentos_processados": len(dados.recebimentos),
        "matches_criados": matches_criados,
        "pendentes": pendentes,
        "resultados": resultados,
    }


@app.post("/cidadao/verificar")
async def verificar_cidadao(
    imagem: UploadFile = File(...),
):
    conteudo = await imagem.read()

    if not conteudo:
        raise HTTPException(
            status_code=400,
            detail="A imagem está vazia.",
        )

    leitura = ler_embalagem(
        conteudo,
        catalogo=CATALOGO_DEMO,
    )

    leitura_dict = leitura.model_dump(mode="json")

    if not leitura.produto or not leitura.marca:
        return {
            "resultado": "verificacao_pendente",
            "orientacao": (
                "Não foi possível identificar o produto "
                "com segurança. Faça uma nova leitura."
            ),
            "pendencias": ["produto"],
            "leitura": leitura_dict,
        }

    alertas_validos = [
        alerta
        for alerta in alertas
        if alerta.get("status_extracao") == "ok"
        and not alerta.get("campos_pendentes")
    ]

    candidatos = []

    for alerta in alertas_validos:
        produto_compativel = (
            normalizar_texto(alerta.get("produto"))
            == normalizar_texto(leitura.produto)
        )

        marca_compativel = (
            normalizar_texto(alerta.get("marca"))
            == normalizar_texto(leitura.marca)
        )

        if produto_compativel and marca_compativel:
            candidatos.append(alerta)

    if not candidatos:
        return {
            "resultado": "sem_recall",
            "orientacao": (
                "Nenhum recall correspondente foi encontrado "
                "na base consultada para o produto identificado."
            ),
            "leitura": leitura_dict,
        }

    recebimento = {
        "loja_id": "cidadao",
        "produto": leitura.produto,
        "marca": leitura.marca,
        "ean": leitura.ean,
        "lote": leitura.lote,
        "data_fabricacao": (
            leitura.data_fabricacao.isoformat()
            if leitura.data_fabricacao
            else None
        ),
    }

    pendencias_encontradas = []

    for alerta in candidatos:
        tipo_regra = (
            alerta.get("regra_lote") or {}
        ).get("tipo")

        pendencias = leitura.pendencias(tipo_regra)

        if pendencias:
            pendencias_encontradas.extend(pendencias)
            continue

        avaliacao = avaliar_recebimento(
            alerta,
            recebimento,
        )

        if avaliacao["match"]:
            return {
                "resultado": "em_recall",
                "alerta_id": alerta.get("alerta_id"),
                "orientacao": (
                    "Não consuma o produto. "
                    "Procure o estabelecimento responsável "
                    "para orientação sobre devolução."
                ),
                "fonte_url": alerta.get("fonte_url"),
                "evidencia": avaliacao.get("evidencia"),
                "leitura": leitura_dict,
            }

    if pendencias_encontradas:
        return {
            "resultado": "verificacao_pendente",
            "orientacao": (
                "Não foi possível concluir a verificação. "
                "Faça uma nova leitura da embalagem."
            ),
            "pendencias": sorted(set(pendencias_encontradas)),
            "leitura": leitura_dict,
        }

    return {
        "resultado": "sem_recall",
        "orientacao": (
            "Nenhum recall correspondente foi encontrado "
            "na base consultada para os dados identificados."
        ),
        "leitura": leitura_dict,
    }


@app.post("/matches/{match_id}/decisao")
def decidir_match(
    match_id: str,
    dados: DecisaoMatch,
):
    match = buscar_match(match_id)

    if match is None:
        raise HTTPException(
            status_code=404,
            detail="Match não encontrado.",
        )

    if match.get("status") != "aguardando_aprovacao":
        raise HTTPException(
            status_code=409,
            detail="Este match já possui uma decisão.",
        )

    match["status"] = dados.decisao
    match["decisao"] = {
        "responsavel": dados.responsavel,
        "motivo": dados.motivo,
        "em": datetime.now().astimezone().isoformat(),
    }

    return match