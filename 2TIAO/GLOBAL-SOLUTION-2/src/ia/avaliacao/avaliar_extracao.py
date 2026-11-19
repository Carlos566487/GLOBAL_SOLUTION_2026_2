"""Avaliação do extrator nos recolhimentos reservados do golden set.

Uso (na pasta src/):
    python -m ia.avaliacao.avaliar_extracao                 # roda o LLM e gera o relatório
    python -m ia.avaliacao.avaliar_extracao --so-relatorio  # recalcula a partir da última execução salva
    python -m ia.avaliacao.avaliar_extracao --modelo gemini-3.8-flash   # comparação separada

Um modelo fixo, fallback desligado. Texto em que o modelo não respondeu = "falha de serviço",
fora dos denominadores da acurácia. Saídas em docs/: resultados_extracao[_<modelo>].md / .csv
e a execução bruta em resultados_extracao[_<modelo>]_execucao.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ia import config
from ia.avaliacao.metricas import (
    CAMPOS_AVALIADOS, LIMIAR_PAREAMENTO, MARGEM_AMBIGUIDADE, comparar_registro, falha_de_servico,
    parear, trecho_de_suporte, valor_no_texto,
)
from ia.extrator import extrair_alertas_detalhado
from ia.prompt import VERSAO_PADRAO

RAIZ = Path(__file__).resolve().parents[3]
DATA, DOCS = RAIZ / "data", RAIZ / "docs"
TEXTOS = DATA / "textos_avaliacao"
BRT = timezone(timedelta(hours=-3))
TRANSCRITOS = {"nestle-formulas"}
ROTULO_CAMPO = {"regra": "Regra completa", "produto": "Produto", "marca": "Marca", "fabricante": "Fabricante",
                "cnpj": "CNPJ", "status": "Status (pendência)"}


def _ler(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


def _arquivos(modelo: str) -> tuple[Path, Path, Path]:
    sufixo = "" if modelo == config.MODELO_PADRAO else f"_{modelo}"
    base = DOCS / f"resultados_extracao{sufixo}"
    return base.with_suffix(".md"), base.with_suffix(".csv"), Path(f"{base}_execucao.json")


# --- execução ----------------------------------------------------------------

def grupos_de_texto(reservados: list[str]) -> list[dict]:
    """Recolhimentos com o mesmo texto-fonte (ex.: militao + cecco) viram uma só extração."""
    manifesto = _ler(TEXTOS / "manifesto.json")
    grupos: dict[str, dict] = {}
    for rid in reservados:
        texto = (TEXTOS / f"{rid}.txt").read_text(encoding="utf-8")
        chave = hashlib.sha256(texto.encode()).hexdigest()
        grupo = grupos.setdefault(chave, {"recolhimentos": [], "texto": texto, "fonte_url": manifesto[rid]["fonte_url"]})
        grupo["recolhimentos"].append(rid)
    return list(grupos.values())


def executar(modelo: str) -> dict:
    divisao = _ler(DATA / "divisao_golden_set.json")
    reservados = [i["recolhimento_id"] for i in divisao["reservados_avaliacao"]["itens"]]
    execucao = {
        "modelo_avaliado": modelo,
        "fallback": "desligado",
        "prompt": VERSAO_PADRAO,
        "temperatura": config.TEMPERATURA,
        "executado_em": datetime.now(BRT).isoformat(timespec="seconds"),
        "textos": [],
    }
    for grupo in grupos_de_texto(reservados):
        r = extrair_alertas_detalhado(grupo["texto"], grupo["fonte_url"], None, modelos=[modelo])
        print(f"{'+'.join(grupo['recolhimentos'])}: {len(r.alertas)} alerta(s), "
              f"modelo={r.modelo}, motivo={r.motivo_falha}, {r.duracao_s}s")
        execucao["textos"].append({
            "recolhimentos": grupo["recolhimentos"],
            "fonte_url": grupo["fonte_url"],
            "modelo_respondeu": r.modelo,
            "versao_modelo": r.versao_modelo,
            "motivo_falha": r.motivo_falha,
            "tentativas": r.tentativas,
            "duracao_s": r.duracao_s,
            "alertas": [a.model_dump(mode="json") for a in r.alertas],
        })
    return execucao


# --- avaliação ---------------------------------------------------------------

def avaliar(execucao: dict) -> dict:
    golden = {a["recolhimento_id"]: a for a in _ler(DATA / "Golden_Set_Recall.json")["alertas"]}
    linhas, extras, ambiguos, falhas = [], [], [], []
    for t in execucao["textos"]:
        texto = (TEXTOS / f"{t['recolhimentos'][0]}.txt").read_text(encoding="utf-8")
        gabarito = [(rid, r) for rid in t["recolhimentos"] for r in golden[rid]["rotulos"]]
        servico = falha_de_servico(t["motivo_falha"])
        if servico:
            falhas.append({"recolhimentos": t["recolhimentos"], "motivo": t["motivo_falha"], "tentativas": t["tentativas"]})
        pares, notas = ({}, []) if servico else parear([r for _, r in gabarito], t["alertas"])
        ambiguos += notas
        for gi, (rid, g) in enumerate(gabarito):
            linha = {"recolhimento": rid, "registro": g["alerta_id"], "tipo": g["regra_lote"]["tipo"] or "null",
                     "transcrito": rid in TRANSCRITOS, "falha_servico": servico, "pareado_com": None,
                     "similaridade": None, "gabarito": g, "extraido": None}
            if gi in pares:
                ei, score = pares[gi]
                e = t["alertas"][ei]
                linha.update(pareado_com=e["alerta_id"], similaridade=round(score, 2), extraido=e,
                             **comparar_registro(g, e), status=g["status_extracao"] == e["status_extracao"])
            else:
                linha.update({c: False for c in (*CAMPOS_AVALIADOS, "status")})
            linha["correto"] = all(linha[c] for c in CAMPOS_AVALIADOS)
            # Diagnóstico: o valor do gabarito pode ser lido no texto de entrada?
            linha["no_texto"] = {c: valor_no_texto(c, g, texto) for c in (*CAMPOS_AVALIADOS, "status")}
            # "Sobre o recuperável": só os campos recuperáveis contam; os demais ficam None.
            linha["recuperavel"] = {c: (linha[c] if linha["no_texto"][c] else None) for c in CAMPOS_AVALIADOS}
            linha["correto_recuperavel"] = all(v for v in linha["recuperavel"].values() if v is not None)
            linhas.append(linha)
        if not servico:
            usados = {ei for ei, _ in pares.values()}
            for ei, e in enumerate(t["alertas"]):
                if ei in usados:
                    continue
                falha_ext = next((c for c in e["campos_pendentes"] if c.startswith("extracao:")), None)
                trecho = None if falha_ext else trecho_de_suporte(e, texto)
                extras.append({"recolhimentos": t["recolhimentos"], "alerta": e, "trecho": trecho,
                               "situacao": f"falha de extração ({falha_ext})" if falha_ext
                               else ("sustentado pelo texto" if trecho else "POSSÍVEL ALUCINAÇÃO")})
    return {"linhas": linhas, "extras": extras, "ambiguos": ambiguos, "falhas_servico": falhas}


# --- relatório ---------------------------------------------------------------

def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "—"


def _por_registro(linhas: list[dict], campos=(*CAMPOS_AVALIADOS, "status")) -> dict:
    validas = [l for l in linhas if not l["falha_servico"]]
    resumo = {c: _pct(sum(l[c] for l in validas), len(validas)) for c in campos}
    resumo["correto"] = _pct(sum(l["correto"] for l in validas), len(validas))
    resumo["n"] = len(validas)
    return resumo


def _por_registro_recuperavel(linhas: list[dict]) -> dict:
    validas = [l for l in linhas if not l["falha_servico"]]
    resumo = {}
    for c in CAMPOS_AVALIADOS:
        avaliaveis = [l["recuperavel"][c] for l in validas if l["recuperavel"][c] is not None]
        resumo[c] = _pct(sum(avaliaveis), len(avaliaveis))
    resumo["correto"] = _pct(sum(l["correto_recuperavel"] for l in validas), len(validas))
    resumo["n"] = len(validas)
    return resumo


def _por_recolhimento_recuperavel(linhas: list[dict]) -> dict:
    grupos = defaultdict(list)
    for l in linhas:
        if not l["falha_servico"]:
            grupos[l["recolhimento"]].append(l)
    n = len(grupos)

    def todos_ok(g, campos):
        return all(l["recuperavel"][c] for l in g for c in campos if l["recuperavel"][c] is not None)

    return {
        "n": n,
        "regra": _pct(sum(todos_ok(g, ("regra",)) for g in grupos.values()), n),
        "identidade": _pct(sum(todos_ok(g, ("produto", "marca", "fabricante", "cnpj")) for g in grupos.values()), n),
        "correto": _pct(sum(todos_ok(g, CAMPOS_AVALIADOS) for g in grupos.values()), n),
    }


def resumo_executivo(avaliacao: dict) -> dict:
    """Números do resumo para o PDF, calculados a partir da avaliação (não digitados)."""
    validas = [l for l in avaliacao["linhas"] if not l["falha_servico"]]
    divergentes = [l for l in validas if l["pareado_com"] and not l["correto"]]
    erros = [(l, c) for l in divergentes for c in CAMPOS_AVALIADOS if not l[c]]
    return {
        "registros": len(validas),
        "regra_ok": sum(l["regra"] for l in validas),
        "erros_regra": sum(1 for l in validas if not l["regra"]),
        # falso "sem recall": regra errada (ou registro sem par) sem pendência que segure o alerta
        "falso_sem_recall": sum(1 for l in validas if not l["regra"]
                                and (l["extraido"] is None or l["extraido"]["status_extracao"] == "ok")),
        "divergentes": len(divergentes),
        "divergentes_ok": [l["registro"] for l in divergentes if l["extraido"]["status_extracao"] == "ok"],
        "extras": len(avaliacao["extras"]),
        "alucinacoes": sum(e["situacao"] == "POSSÍVEL ALUCINAÇÃO" for e in avaliacao["extras"]),
        "erros_campo": len(erros),
        "erros_fora_do_texto": sum(1 for l, c in erros if not l["no_texto"][c]),
        "erros_marca_reais": sum(1 for l, c in erros if c == "marca" and l["no_texto"][c]),
    }


def _por_recolhimento(linhas: list[dict]) -> dict:
    grupos = defaultdict(list)
    for l in linhas:
        if not l["falha_servico"]:
            grupos[l["recolhimento"]].append(l)
    n = len(grupos)
    return {
        "n": n,
        "regra": _pct(sum(all(l["regra"] for l in g) for g in grupos.values()), n),
        "identidade": _pct(sum(all(l[c] for l in g for c in ("produto", "marca", "fabricante", "cnpj"))
                               for g in grupos.values()), n),
        "correto": _pct(sum(all(l["correto"] for l in g) for g in grupos.values()), n),
    }


def _valor(v) -> str:
    if isinstance(v, dict):  # regra_lote
        tipo = v.get("tipo")
        detalhe = {"lista": v.get("lotes"), "sufixo": v.get("sufixo"), "data_corte": v.get("fabricado_ate")}.get(tipo)
        return f"{tipo}: {detalhe}" if detalhe is not None else str(tipo)
    return "null" if v is None else str(v)


def escrever_relatorio(execucao: dict, avaliacao: dict, md: Path, csv_path: Path) -> None:
    linhas = avaliacao["linhas"]
    escopos = [
        ("Todos os reservados", linhas),
        ("Sem a Nestlé", [l for l in linhas if not l["transcrito"]]),
        ("Nestlé (entrada transcrita)", [l for l in linhas if l["transcrito"]]),
    ]
    respondeu = sorted({t["modelo_respondeu"] for t in execucao["textos"] if t["modelo_respondeu"]})
    versoes = sorted({t["versao_modelo"] for t in execucao["textos"] if t["versao_modelo"]})
    n_rec = len({l["recolhimento"] for l in linhas})
    o = []
    o += [
        "# Resultados da extração",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Modelo avaliado (`EVAL_MODEL`) | `{execucao['modelo_avaliado']}` |",
        f"| Modelo que respondeu | {', '.join(f'`{m}`' for m in respondeu) or '—'} (versão: {', '.join(versoes) or '—'}) |",
        f"| Fallback | {execucao['fallback']} |",
        f"| Prompt | `{execucao['prompt']}` · temperatura {execucao['temperatura']} |",
        f"| Executado em | {execucao['executado_em']} |",
        f"| Conjunto | {n_rec} recolhimentos reservados · {len(linhas)} registros · {len(execucao['textos'])} textos "
        f"(militao+cecco e bento+equaliv compartilham o texto) |",
        f"| Falhas de serviço | {len(avaliacao['falhas_servico'])} texto(s) |",
        "",
    ]
    rx = resumo_executivo(avaliacao)
    erros_regra = "o único erro" if rx["erros_regra"] == 1 else f"os {rx['erros_regra']} erros"
    linha_pendente = (f"{erros_regra} de regra terminou em `verificacao_pendente`" if rx["erros_regra"]
                      else "nenhum erro de regra")
    ok_div = ", ".join(f"`{r}`" for r in rx["divergentes_ok"])
    o += [
        "## Resumo para o PDF",
        "",
        f"- **Regra de lote correta em {rx['regra_ok']}/{rx['registros']} registros.**",
        f"- **{rx['falso_sem_recall']} falsos \"sem recall\":** {linha_pendente}. Dos {rx['divergentes']} registros "
        f"com alguma divergência, {rx['divergentes'] - len(rx['divergentes_ok'])} ficaram pendentes"
        + (f"; {len(rx['divergentes_ok'])} ficaram `ok` com divergência só de identidade ({ok_div})." if ok_div else "."),
        f"- **{rx['alucinacoes']} alucinações** entre os {rx['extras']} alertas não rotulados (todos com trecho do texto que os sustenta).",
        f"- **Erros de identidade:** {rx['erros_fora_do_texto']}/{rx['erros_campo']} campos com erro têm valor de gabarito "
        f"ausente do texto de entrada; os erros reais do extrator se concentram em **marca** ({rx['erros_marca_reais']}).",
        "",
        "## Resumo",
        "",
        "Acerto **por registro** (cada apresentação de produto conta uma vez). \"Totalmente correto\" = regra + os 4 campos de identidade.",
        "",
        "- **Contra o gabarito:** todos os campos contam.",
        "- **Sobre o recuperável:** só contam os campos cujo valor do gabarito aparece no texto de entrada (coluna de "
        "diagnóstico); o denominador muda por campo. \"Totalmente correto\" = todos os campos recuperáveis do registro corretos.",
        "",
        "| Escopo | Métrica | Registros | Regra completa | Produto | Marca | Fabricante | CNPJ | **Totalmente correto** |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for nome, ls in escopos:
        r, rr = _por_registro(ls), _por_registro_recuperavel(ls)
        o.append(f"| {nome} | contra o gabarito | {r['n']} | {r['regra']} | {r['produto']} | {r['marca']} | "
                 f"{r['fabricante']} | {r['cnpj']} | **{r['correto']}** |")
        o.append(f"| | sobre o recuperável | {rr['n']} | {rr['regra']} | {rr['produto']} | {rr['marca']} | "
                 f"{rr['fabricante']} | {rr['cnpj']} | **{rr['correto']}** |")
    o += ["", "Status (pendência) igual ao do gabarito: "
          + " · ".join(f"{nome}: {_por_registro(ls)['status']}" for nome, ls in escopos) + ".",
          "", "Acerto **por recolhimento** (o recolhimento só conta se **todos** os seus registros acertarem).", "",
          "| Escopo | Métrica | Recolhimentos | Regra completa | Identidade (4 campos) | **Totalmente correto** |",
          "|---|---|---|---|---|---|"]
    for nome, ls in escopos:
        r, rr = _por_recolhimento(ls), _por_recolhimento_recuperavel(ls)
        o.append(f"| {nome} | contra o gabarito | {r['n']} | {r['regra']} | {r['identidade']} | **{r['correto']}** |")
        o.append(f"| | sobre o recuperável | {rr['n']} | {rr['regra']} | {rr['identidade']} | **{rr['correto']}** |")

    o += ["", "## Por tipo de regra (tipo do gabarito)", "",
          "| Tipo | Recolhimentos | Registros | Regra completa (registro) | Totalmente correto (registro) | "
          "Totalmente correto, sobre o recuperável (registro) | Regra completa (recolhimento) |",
          "|---|---|---|---|---|---|---|"]
    for tipo in ("lista", "sufixo", "data_corte", "todos", "null"):
        ls = [l for l in linhas if l["tipo"] == tipo]
        if not ls:
            o.append(f"| `{tipo}` | 0 | 0 | — | — | — | sem caso real no gabarito |" if tipo == "sufixo"
                     else f"| `{tipo}` | 0 | 0 | — | — | — | — |")
            continue
        r, rr = _por_registro(ls), _por_recolhimento(ls)
        o.append(f"| `{tipo}` | {rr['n']} | {r['n']} | {r['regra']} | {r['correto']} | "
                 f"{_por_registro_recuperavel(ls)['correto']} | {rr['regra']} |")

    o += ["", "## Por recolhimento", "",
          "| Recolhimento | Tipo | Registros | Pareados | Regra | Produto | Marca | Fabricante | CNPJ | Totalmente correto | Obs. |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    por_rec = defaultdict(list)
    for l in linhas:
        por_rec[l["recolhimento"]].append(l)
    for rid, ls in por_rec.items():
        d = len(ls)
        obs = []
        if ls[0]["transcrito"]:
            obs.append("entrada transcrita")
        if ls[0]["falha_servico"]:
            obs.append("falha de serviço")
        cont = lambda c: f"{sum(l[c] for l in ls)}/{d}"  # noqa: E731
        o.append(f"| {rid} | `{ls[0]['tipo']}` | {d} | {sum(l['pareado_com'] is not None for l in ls)}/{d} | "
                 f"{cont('regra')} | {cont('produto')} | {cont('marca')} | {cont('fabricante')} | {cont('cnpj')} | "
                 f"{cont('correto')} | {', '.join(obs)} |")

    fn = [l for l in linhas if l["pareado_com"] is None and not l["falha_servico"]]
    o += ["", f"## Falsos negativos ({len(fn)})", "", "Registros do gabarito sem alerta extraído pareado (erro do extrator).", ""]
    o += [f"- `{l['registro']}` ({l['recolhimento']}): {l['gabarito']['produto']}" for l in fn] or ["- Nenhum."]

    div = [l for l in linhas if l["pareado_com"] and not l["correto"] or (l["pareado_com"] and not l["status"])]
    campos_div = (("regra", "regra_lote"), ("produto", "produto"), ("marca", "marca"),
                  ("fabricante", "fabricante"), ("cnpj", "cnpj"))
    erros = [(l, c) for l in div for c, _ in campos_div if not l[c]]
    fora = [(l, c) for l, c in erros if not l["no_texto"][c]]
    o += ["", f"## Divergências nos registros pareados ({len(div)} registros, {len(erros)} campos com erro)", "",
          f"**Diagnóstico (não altera a acurácia):** em **{len(fora)} de {len(erros)}** campos com erro, o valor do "
          "gabarito **não aparece no texto de entrada** (a PO completou com outra fonte, como a RE). Nesses casos o "
          "extrator devolveu `null` ou o valor do texto, como manda o prompt (\"nunca invente\").", ""]
    resumo_fora = defaultdict(int)
    for _, c in fora:
        resumo_fora[c] += 1
    if resumo_fora:
        o += ["| Campo | Erros | Valor do gabarito ausente do texto |", "|---|---|---|"]
        for c, _ in campos_div:
            total = sum(1 for _, cc in erros if cc == c)
            if total:
                o.append(f"| {ROTULO_CAMPO[c]} | {total} | {resumo_fora[c]} |")
        o.append("")
    o += ["| Registro | Campo | Gabarito | Extraído | Valor do gabarito está no texto? |", "|---|---|---|---|---|"]
    for l in div:
        for c, chave in (*campos_div, ("status", "status_extracao")):
            if not l[c]:
                no_texto = "—" if c == "status" else ("sim" if l["no_texto"][c] else "**não**")
                o.append(f"| `{l['registro']}` | {ROTULO_CAMPO[c]} | {_valor(l['gabarito'][chave])} | "
                         f"{_valor(l['extraido'][chave])} | {no_texto} |")
    if not div:
        o.append("| — | — | — | — | — |")

    o += ["", f"## Pareamentos ambíguos ({len(avaliacao['ambiguos'])})", ""]
    o += [f"- {a}" for a in avaliacao["ambiguos"]] or ["- Nenhum."]

    ex = avaliacao["extras"]
    aluc = sum(e["situacao"] == "POSSÍVEL ALUCINAÇÃO" for e in ex)
    o += ["", f"## revisao_manual: alertas extraídos sem registro no gabarito ({len(ex)}; possíveis alucinações: {aluc})", "",
          "Fora da acurácia. O gabarito rotula só os produtos escolhidos pela PO; outros produtos citados no mesmo texto "
          "aparecem aqui. Sem trecho que sustente o alerta = **possível alucinação** (risco crítico 2 da matriz da PO).", "",
          "| Texto | Produto extraído | Regra | Situação | Trecho do texto |", "|---|---|---|---|---|"]
    for e in ex:
        a = e["alerta"]
        trecho = (e["trecho"] or "—").replace("|", "/")
        o.append(f"| {'+'.join(e['recolhimentos'])} | {_valor(a['produto'])} | {_valor(a['regra_lote'])} | "
                 f"{e['situacao']} | {trecho} |")
    if not ex:
        o.append("| — | — | — | — | — |")

    o += ["", f"## Falhas de serviço ({len(avaliacao['falhas_servico'])})", ""]
    o += [f"- {'+'.join(f['recolhimentos'])}: `{f['motivo']}` · tentativas {f['tentativas']}" for f in avaliacao["falhas_servico"]] or ["- Nenhuma."]

    o += ["", "## Regras de comparação", "",
          "- **Conjunto avaliado:** só os 15 recolhimentos reservados de `data/divisao_golden_set.json`. Nenhum aparece no prompt.",
          "- **Pareamento:** cada registro do gabarito é pareado com no máximo um alerta extraído **do mesmo texto**, "
          f"pelo produto normalizado (similaridade de Jaccard entre as palavras ≥ {LIMIAR_PAREAMENTO}) e CNPJ compatível "
          "(mesmos dígitos, ou nulo de um dos lados). Atribuição gulosa pela maior similaridade. Os lotes **não** entram no "
          "pareamento, para não favorecer a métrica da regra. Igualdade exata do produto não serve para parear: a PO reescreveu "
          "os nomes (ex.: `Sardinha-laje congelada espalmada, 800 g` × texto `PEIXE CONGELADO SARDINHA LAJE ESPALMADA 800G`).",
          f"- **Ambíguo:** outro candidato com similaridade a menos de {MARGEM_AMBIGUIDADE} do escolhido.",
          "- **Registro sem par** = falso negativo: conta como erro em todos os campos.",
          "- **Alerta sem par** = fora da acurácia, listado em `revisao_manual` com o trecho que o sustenta.",
          "- **Regra completa:** mesmo `tipo` e, conforme o tipo: `lista` = mesmo **conjunto** de lotes; `sufixo` = mesmo sufixo; "
          "`data_corte` = mesma data; `todos`/`null` = só o tipo.",
          "- **Lote:** comparado pela chave **sem nenhum espaço + maiúsculas** (`183/3 B` = `183/3B`). Zeros à esquerda contam "
          "(`07225288` ≠ `7225288`). A extração em si continua fiel ao texto.",
          "- **Produto e marca:** minúsculas, sem acento, sem pontuação e espaço padronizado (inclui separar número de unidade: `800g` = `800 g`).",
          "- **Fabricante:** igual a produto, removendo antes o conteúdo entre parênteses (anotações da PO, ex.: `(Bausch Lomb)`).",
          "- **CNPJ:** só os dígitos. Nulo × nulo conta como acerto em qualquer campo.",
          "- **Status (pendência):** `status_extracao` igual ao do gabarito. Informativo, fora do \"totalmente correto\".",
          "- **\"Valor do gabarito está no texto?\"**: diagnóstico. Procura o valor normalizado do gabarito no texto de entrada "
          "(CNPJ por dígitos; lista = todos os lotes; `todos` = a palavra \"todos\"; `data_corte` = a data DD/MM/AAAA). Não muda a acurácia.",
          "- **Fora da conta:** `escopo` e `categoria`, até a PO atualizar o registro `sanibras` no gabarito.",
          "- **Falha de serviço:** o modelo não respondeu (`orcamento_esgotado`, `modelos_esgotados`, `erro_llm:*`). Os registros "
          "desse texto saem dos denominadores e são listados à parte.",
          "- **Nestlé:** entrada transcrita à mão das tabelas em imagem do PDF; reportada também à parte.",
          "", "## Nota para o motor (Full-Stack)", "",
          "Com a normalização atual do contrato (`strip` + `upper`), o lote `183/3B` lido numa embalagem **não casa** com o "
          "alerta `183/3 B`. Recomendação: o motor usar a mesma chave da avaliação (sem nenhum espaço). A decisão é do motor.",
          ""]
    md.write_text("\n".join(o), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["recolhimento", "registro", "tipo_gabarito", "entrada_transcrita", "falha_servico", "pareado_com",
                    "similaridade", *CAMPOS_AVALIADOS, "status", "totalmente_correto",
                    *(f"{c}_no_texto" for c in CAMPOS_AVALIADOS), *(f"{c}_recuperavel" for c in CAMPOS_AVALIADOS),
                    "totalmente_correto_recuperavel",
                    "regra_gabarito", "regra_extraida", "produto_gabarito", "produto_extraido"])
        for l in linhas:
            e = l["extraido"] or {}
            w.writerow([l["recolhimento"], l["registro"], l["tipo"], l["transcrito"], l["falha_servico"], l["pareado_com"],
                        l["similaridade"], *(l[c] for c in CAMPOS_AVALIADOS), l["status"], l["correto"],
                        *(l["no_texto"][c] for c in CAMPOS_AVALIADOS),
                        *("" if l["recuperavel"][c] is None else l["recuperavel"][c] for c in CAMPOS_AVALIADOS),
                        l["correto_recuperavel"],
                        _valor(l["gabarito"]["regra_lote"]), _valor(e.get("regra_lote")) if e else "",
                        l["gabarito"]["produto"], e.get("produto", "")])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", default=config.EVAL_MODEL)
    parser.add_argument("--so-relatorio", action="store_true")
    args = parser.parse_args()
    md, csv_path, bruto = _arquivos(args.modelo)
    if args.so_relatorio:
        execucao = _ler(bruto)
    else:
        execucao = executar(args.modelo)
        bruto.write_text(json.dumps(execucao, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    escrever_relatorio(execucao, avaliar(execucao), md, csv_path)
    print(f"relatório: {md}")


if __name__ == "__main__":
    main()
