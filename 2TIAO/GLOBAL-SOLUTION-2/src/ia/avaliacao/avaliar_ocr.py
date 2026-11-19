"""Teste do leitor da embalagem nas fotos de data/fotos_teste/ contra gabarito_fotos.csv.

Uso (na pasta src/):  python -m ia.avaliacao.avaliar_ocr

Roda duas versões do leitor nas mesmas fotos:
- "regra original": embalagem.py do commit anterior à mudança da convenção de lote (lido do git
  para uma pasta temporária, sem alterar o repositório). É a medição sem contaminação.
- "regra alinhada": o embalagem.py atual, com a convenção de lote do gabarito.

gabarito_fotos.csv: arquivo, produto, marca, ean, lote, data_fabricacao, validade, legivel_sim_nao, observacao.
As fotos são só lidas (nada é copiado, gravado ou enviado ao LLM); o relatório lista nomes de
arquivo e campos, nunca a imagem nem o texto bruto do OCR.
Saída: docs/resultados_ocr.md + docs/resultados_ocr.csv.
"""
from __future__ import annotations

import csv
import importlib.util
import re
import subprocess
import tempfile
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ia.avaliacao.metricas import chave_lote
from ia.embalagem import ler_embalagem
from ia.schemas import LIMITE_CONFIANCA_OCR, LeituraEmbalagem

RAIZ = Path(__file__).resolve().parents[3]
PASTA_FOTOS = RAIZ / "data" / "fotos_teste"
DOCS = RAIZ / "docs"
BRT = timezone(timedelta(hours=-3))
CAMPOS = ("ean", "lote", "data_fabricacao", "validade")
TIPO_REGRA = "lista"  # a foto é avaliada como se o alerta fosse por lote (o caso mais exigente)

# Commit que alinhou a convenção de lote ao gabarito, depois da inspeção das fotos.
COMMIT_REGRA_ALINHADA = "07fcf16"
CAMINHO_EMBALAGEM = "2TIAO/GLOBAL-SOLUTION-2/src/ia/embalagem.py"

ACERTO, FALSO_PENDENTE, PENDENTE_CORRETO, ERRO_CONFIANTE = (
    "acerto", "pendente (legível)", "pendente correto", "ERRO CONFIANTE")
GRUPOS = (
    ("lote_legivel", "Lote legível"),
    ("so_ean", "Só EAN (lote fora do quadro)"),
    ("controle_negativo", "Controle negativo (lote ilegível)"),
    ("validade_mes_ano", "Validade só de mês/ano"),
)


def _data(valor: str) -> date | None:
    valor = (valor or "").strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            pass
    return None


def carregar_gabarito(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        amostra = f.read(2048)
        f.seek(0)
        dialeto = csv.Sniffer().sniff(amostra, delimiters=",;")
        linhas = []
        for linha in csv.DictReader(f, dialect=dialeto):
            linha = {k.strip(): (v or "").strip() for k, v in linha.items() if k}
            linha["legivel"] = linha.get("legivel_sim_nao", "").lower() in ("sim", "s", "yes")
            linha["validade_bruta"] = linha.get("validade", "")
            linha["data_fabricacao"] = _data(linha.get("data_fabricacao", ""))
            linha["validade"] = _data(linha.get("validade", ""))
            linhas.append(linha)
    return linhas


def grupos_da_foto(g: dict) -> list[str]:
    grupos = []
    if g["legivel"] and g.get("lote"):
        grupos.append("lote_legivel")
    elif g.get("ean") and not g.get("lote"):
        grupos.append("so_ean")
    elif not g["legivel"]:
        grupos.append("controle_negativo")
    if re.fullmatch(r"\d{4}-\d{2}", g.get("validade_bruta", "")):
        grupos.append("validade_mes_ano")
    return grupos


def comparar(gabarito: dict, leitura: LeituraEmbalagem) -> dict[str, bool | None]:
    """True/False por campo; None quando o gabarito não tem o valor (fora do denominador)."""
    resultado = {}
    for campo in CAMPOS:
        esperado, lido = gabarito.get(campo) or None, getattr(leitura, campo)
        if esperado is None:
            resultado[campo] = None
        elif campo == "lote":
            resultado[campo] = lido is not None and chave_lote(lido) == chave_lote(esperado)
        else:
            resultado[campo] = lido == esperado
    return resultado


def classificar(gabarito: dict, leitura: LeituraEmbalagem, campos: dict) -> str:
    pendente = bool(leitura.pendencias(TIPO_REGRA))
    if not gabarito["legivel"]:
        return PENDENTE_CORRETO if pendente else ERRO_CONFIANTE
    if pendente:
        return FALSO_PENDENTE
    # Sem pendência, lote e EAN precisam bater: senão é uma resposta conclusiva errada.
    return ACERTO if campos["lote"] is not False and campos["ean"] is not False else ERRO_CONFIANTE


def avaliar(pasta: Path = PASTA_FOTOS, leitor=None, ler=ler_embalagem) -> dict:
    gabarito = carregar_gabarito(pasta / "gabarito_fotos.csv")
    catalogo = {g["ean"]: (g.get("produto"), g.get("marca")) for g in gabarito if g.get("ean")}
    linhas = []
    for g in gabarito:
        caminho = pasta / g["arquivo"]
        base = {"arquivo": g["arquivo"], "gabarito": g, "grupos": grupos_da_foto(g)}
        if not caminho.is_file():
            linhas.append({**base, "ausente": True})
            continue
        inicio = time.perf_counter()
        leitura = ler(caminho.read_bytes(), catalogo=catalogo, leitor=leitor)
        duracao = time.perf_counter() - inicio
        campos = comparar(g, leitura)
        linhas.append({**base, "ausente": False, "leitura": leitura, "campos": campos,
                       "pendencias": leitura.pendencias(TIPO_REGRA),
                       "resultado": classificar(g, leitura, campos), "duracao_s": round(duracao, 2)})
    return {"linhas": linhas, "executado_em": datetime.now(BRT).isoformat(timespec="seconds")}


def carregar_leitor_original(commit: str = f"{COMMIT_REGRA_ALINHADA}^"):
    """`ler_embalagem` do embalagem.py de `commit`, lido do git para uma pasta temporária."""
    codigo = subprocess.run(["git", "show", f"{commit}:{CAMINHO_EMBALAGEM}"], cwd=RAIZ, check=True,
                            capture_output=True).stdout
    arquivo = Path(tempfile.mkdtemp(prefix="embalagem_original_")) / "embalagem_original.py"
    arquivo.write_bytes(codigo)
    spec = importlib.util.spec_from_file_location("ia._embalagem_original", arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.ler_embalagem


def avaliar_demo(ler=ler_embalagem) -> list[dict]:
    """Lê as imagens SIMULADAS de data/demo/ (fora das métricas das fotos reais)."""
    from ia.avaliacao.gerar_demo import CATALOGO_DEMO, DEMOS, PASTA_DEMO

    linhas = []
    for demo in DEMOS:
        caminho = PASTA_DEMO / demo["arquivo"]
        if not caminho.is_file():
            continue
        leitura = ler(caminho.read_bytes(), catalogo=CATALOGO_DEMO)
        pendencias = leitura.pendencias(TIPO_REGRA)
        conforme = (bool(pendencias) == demo["borrar_lote"]
                    and (demo["borrar_lote"] or leitura.lote == demo["lote"]))
        linhas.append({**demo, "leitura": leitura, "pendencias": pendencias, "conforme": conforme})
    return linhas


def _secao_demo(demo: list[dict]) -> list[str]:
    if not demo:
        return []
    o = ["", "## Imagens simuladas para demonstração", "",
         "**Fora das métricas acima.** Rótulos desenhados com PIL (`python -m ia.avaliacao.gerar_demo`), com a faixa "
         "\"IMAGEM SIMULADA — DEMONSTRAÇÃO\" e o nome do arquivo visíveis, para o vídeo e o teste de ponta a ponta do "
         "Full-Stack. EAN fictício com prefixo GS1 `200` (uso interno, nunca produto real) e dígito verificador correto. "
         "O desenho do rótulo foi escolhido para ficar legível; o leitor e o limite de 0,8 são os mesmos das fotos reais.", "",
         "| Imagem | EAN | Produto / marca (catálogo) | Lote | Fab. | Val. | Confiança | Pendências | Esperado | Confere |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for d in demo:
        r = d["leitura"]
        o.append(f"| `{d['arquivo']}` | {r.ean or '—'} | {r.produto or '—'} / {r.marca or '—'} | {r.lote or '—'} | "
                 f"{r.data_fabricacao or '—'} | {r.validade or '—'} | {r.confianca_ocr:.2f} | "
                 f"{', '.join(d['pendencias']) or '—'} | {d['esperado']} | {'sim' if d['conforme'] else '**não**'} |")
    return o


# --- relatório ---------------------------------------------------------------

def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "—"


def _tabela_grupos(av: dict) -> list[str]:
    o = ["| Grupo | Fotos | Acerto | Pendente (legível) | Pendente correto | **Erro confiante** | Lote correto | EAN correto |",
         "|---|---|---|---|---|---|---|---|"]
    lidas = [l for l in av["linhas"] if not l["ausente"]]
    for chave, nome in (*GRUPOS, ("todas", "**Todas**")):
        ls = lidas if chave == "todas" else [l for l in lidas if chave in l["grupos"]]
        n = len(ls)
        cont = Counter(l["resultado"] for l in ls)

        def campo(c):
            avaliaveis = [l["campos"][c] for l in ls if l["campos"][c] is not None]
            return _pct(sum(avaliaveis), len(avaliaveis))

        o.append(f"| {nome} | {n} | {_pct(cont[ACERTO], n)} | {_pct(cont[FALSO_PENDENTE], n)} | "
                 f"{_pct(cont[PENDENTE_CORRETO], n)} | **{_pct(cont[ERRO_CONFIANTE], n)}** | {campo('lote')} | {campo('ean')} |")
    return o


def _tabela_campos(av: dict) -> list[str]:
    lidas = [l for l in av["linhas"] if not l["ausente"]]
    o = ["| Campo | Correto | Não lido | Lido errado |", "|---|---|---|---|"]
    for campo in CAMPOS:
        com_valor = [l for l in lidas if l["campos"][campo] is not None]
        corretos = sum(l["campos"][campo] for l in com_valor)
        nao_lidos = sum(1 for l in com_valor if not l["campos"][campo] and getattr(l["leitura"], campo) is None)
        o.append(f"| {campo} | {_pct(corretos, len(com_valor))} | {nao_lidos} | {len(com_valor) - corretos - nao_lidos} |")
    return o


def _tabela_motivos(av: dict) -> list[str]:
    """Por que as fotos com lote legível ficaram pendentes (uma foto pode ter vários motivos)."""
    ls = [l for l in av["linhas"] if not l["ausente"] and "lote_legivel" in l["grupos"]]
    com_ean = sum(1 for l in ls if l["gabarito"].get("ean"))
    o = [f"Motivos de pendência nas {len(ls)} fotos com lote legível (uma foto pode ter mais de um). "
         f"Só {com_ean} dessas fotos têm EAN no quadro; sem EAN o produto não é identificado e a foto fica pendente "
         f"por desenho, então o teto de \"acerto\" neste grupo é {com_ean}/{len(ls)}.", "",
         "| Motivo | Fotos |", "|---|---|"]
    rotulos = {"produto": "produto não identificado (sem EAN legível)", "lote": "lote não lido",
               "confianca_ocr": f"confiança do OCR < {LIMITE_CONFIANCA_OCR}", "data_fabricacao": "fabricação não lida"}
    for motivo, nome in rotulos.items():
        fotos = [l["arquivo"].removesuffix(".jpg") for l in ls if motivo in l["pendencias"]]
        if fotos:
            o.append(f"| {nome} | {len(fotos)}/{len(ls)} ({', '.join(fotos)}) |")
    return o


def _tabela_detalhe(av: dict) -> list[str]:
    o = ["| Foto | Grupo | Resultado | EAN | Lote (gabarito → lido) | Fab. | Val. | Confiança | Pendências |",
         "|---|---|---|---|---|---|---|---|---|"]
    nomes = dict(GRUPOS)

    def marca(ok, lido):
        return "—" if ok is None else "ok" if ok else ("não lido" if lido is None else "**lido errado**")

    for l in av["linhas"]:
        g = l["gabarito"]
        grupos = ", ".join(nomes[c] for c in l["grupos"])
        if l["ausente"]:
            o.append(f"| {l['arquivo']} | {grupos} | arquivo ausente | | | | | | |")
            continue
        r, c = l["leitura"], l["campos"]
        resultado = f"**{l['resultado']}**" if l["resultado"] == ERRO_CONFIANTE else l["resultado"]
        o.append(f"| {l['arquivo']} | {grupos} | {resultado} | {marca(c['ean'], r.ean)} | "
                 f"{g.get('lote') or '—'} → {r.lote or '—'} | {marca(c['data_fabricacao'], r.data_fabricacao)} | "
                 f"{marca(c['validade'], r.validade)} | "
                 f"{r.confianca_ocr:.2f} | {', '.join(l['pendencias']) or '—'} |")
    return o


def escrever_relatorio(versoes: list[tuple[str, str, dict]], md: Path, csv_path: Path,
                       demo: list[dict] | None = None) -> None:
    """`versoes`: [(nome, descrição, avaliação)]; `demo`: leituras das imagens simuladas (seção à parte)."""
    primeira = versoes[0][2]
    lidas = [l for l in primeira["linhas"] if not l["ausente"]]
    tempos = [l["duracao_s"] for _, _, av in versoes for l in av["linhas"] if not l["ausente"]]
    o = [
        "# Resultados do leitor da embalagem (OCR + código de barras)",
        "",
        "| Item | Valor |",
        "|---|---|",
        "| Motor | OpenCV (CLAHE) + EasyOCR (pt, en; CPU, local) + pyzbar |",
        f"| Limite de confiança | `confianca_ocr` < {LIMITE_CONFIANCA_OCR} → pendente |",
        f"| Avaliado como regra | `{TIPO_REGRA}` (exige lote e produto identificado) |",
        f"| Executado em | {primeira['executado_em']} |",
        f"| Fotos | {len(lidas)} próprias (`data/fotos_teste/`), gabarito `gabarito_fotos.csv` |",
        f"| Tempo médio por foto | {sum(tempos) / len(tempos):.1f} s |" if tempos else "| Tempo médio por foto | — |",
        "",
        "## Duas versões do leitor (transparência)",
        "",
        "- A **convenção de delimitação do lote** do leitor foi **alinhada à convenção do gabarito depois da inspeção das "
        f"fotos de teste** (commit `{COMMIT_REGRA_ALINHADA}`; os testes novos dessa mudança usam os padrões das fotos).",
        "- É uma mudança de **convenção** (onde o lote começa e termina no texto lido), não um ajuste de modelo: o EasyOCR, "
        "o pré-processamento, o limite de confiança e o pyzbar são os mesmos nas duas versões.",
        "- Mesmo assim, a **regra original é a medição sem contaminação**. As duas são reportadas lado a lado.",
        "- A **rotação continua sem correção** (limitação declarada antes das fotos, não ajustada): a foto01 está girada 90°.",
        "",
        "Leitura dos resultados: **acerto** = sem pendência, lote e EAN corretos; **pendente (legível)** = pediu revisão sem "
        "necessidade (seguro, pouco útil); **pendente correto** = foto sem lote legível e o sistema não respondeu de forma "
        "conclusiva; **erro confiante** = sem pendência, mas com lote/EAN errado, ou foto sem lote legível sem pendência. "
        "É o erro que pode virar falso \"sem recall\". As fotos podem estar em mais de um grupo (validade só de mês/ano "
        "também tem lote legível).",
    ]
    for nome, descricao, av in versoes:
        o += ["", f"## {nome}", "", descricao, "", *_tabela_grupos(av), "", "Acerto por campo (denominador = fotos em que o "
              "gabarito tem o valor; \"lido errado\" = leu um valor diferente, pior que não ler):", "", *_tabela_campos(av),
              "", *_tabela_motivos(av),
              "", "<details><summary>Detalhe por foto</summary>", "", *_tabela_detalhe(av), "", "</details>"]
    o += _secao_demo(demo or [])
    o += ["", "## Regras", "",
          "- A foto é lida do disco só para o teste; `ler_embalagem` recebe bytes e não grava, não loga e não envia a imagem a serviço externo.",
          "- Produto identificado = EAN lido (pyzbar, dígito verificador conferido). O catálogo EAN → produto usado aqui vem do próprio "
          "`gabarito_fotos.csv` (stub da base de produtos, que é de outro papel).",
          "- Lote comparado sem espaços + maiúsculas; datas comparadas como data. Validade só de mês/ano fica fora do denominador de validade.",
          "- O texto bruto do OCR não é salvo no relatório.", ""]
    md.write_text("\n".join(o), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["versao", "arquivo", "grupos", "legivel", "resultado", *(f"{c}_ok" for c in CAMPOS),
                    "lote_gabarito", "lote_lido", "confianca_ocr", "pendencias", "duracao_s"])
        for nome, _, av in versoes:
            for l in av["linhas"]:
                if l["ausente"]:
                    w.writerow([nome, l["arquivo"], "|".join(l["grupos"]), l["gabarito"].get("legivel_sim_nao"), "arquivo ausente"])
                    continue
                w.writerow([nome, l["arquivo"], "|".join(l["grupos"]), l["gabarito"]["legivel"], l["resultado"],
                            *(l["campos"][c] for c in CAMPOS), l["gabarito"].get("lote"), l["leitura"].lote,
                            l["leitura"].confianca_ocr, "|".join(l["pendencias"]), l["duracao_s"]])


def main() -> None:
    original = avaliar(ler=carregar_leitor_original())
    alinhada = avaliar()
    escrever_relatorio([
        ("Regra original (medição sem contaminação)",
         f"Leitor do commit anterior a `{COMMIT_REGRA_ALINHADA}`: marcadores `LOTE`/`LOT`/`L:`/`L.`; o lote vai até uma "
         "sigla de outro campo ou o fim da linha; não para em hora/data; não reconhece `L029` nem o rótulo \"Validade/Lote\".",
         original),
        ("Regra alinhada (convenção do gabarito)",
         "Leitor atual: marcador `L`, `L:`, `L.` (ou `L` colado ao número); o lote vai até a primeira hora/data, rótulo de "
         "outro campo ou o fim da linha; com o rótulo \"Lote\" sem marcador, a linha de código seguinte que não é data. "
         "Ver `docs/interface_ia.md`.",
         alinhada),
    ], DOCS / "resultados_ocr.md", DOCS / "resultados_ocr.csv", demo=avaliar_demo())
    print(f"relatório: {DOCS / 'resultados_ocr.md'}")


if __name__ == "__main__":
    main()
