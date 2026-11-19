# Evidências de testes

Registro das execuções usadas no README e no PDF. Executado em **19/11/2026**.

## 1. Suítes automatizadas (pytest)

| Suíte | Comando (a partir de `src/`) | Resultado |
|---|---|---|
| IA — schemas, prompt, extrator, Gemini, métricas, leitor OCR | `cd ia && python -m pytest` | **187 passed, 6 skipped, 1 failed** (194 testes) |
| Motor de regras | `cd backend && python -m pytest tests/test_motor_regras.py` | **12 passed** |
| Cenários de demo ponta a ponta (API) | `cd backend && python -m pytest tests/test_cenarios_demo.py -v` | **4 passed, 1 xfailed** |

**Sobre os 6 skipped e o 1 failed da IA (ambiente, não código):**

- *Skipped:* 5 testes de integração do EasyOCR (pacote de ~100 MB não instalado no ambiente de verificação) e 1 teste de integração com o Gemini (sem `GEMINI_API_KEY`). Os resultados reais dessas integrações estão em `resultados_ocr.md` e `resultados_extracao.md`.
- *Failed:* `test_avaliar_ocr` reconstrói a versão anterior do leitor com `git show 07fcf16^:...`. Falha quando o repositório é baixado como ZIP (sem a pasta `.git`). Em um `git clone` o teste passa.

## 2. Cenários de demonstração (API FastAPI)

Fonte dos alertas: registros **reais** `vaidosa` e `sanibras` do `data/Golden_Set_Recall.json`. Recebimentos **simulados** (`simulado: true`). Código: `src/backend/tests/test_cenarios_demo.py`.

### Cenário 1 — Vaidosa · lista de lotes (148, 153, 166, 167)

Entrada: Loja A lote `153`, Loja B lote `154`.

```json
{"loja_id": "LOJA-A", "resultado": "match", "match": true,
 "evidencia": {"campo": "lote", "valor_alerta": ["148","153","166","167"], "valor_recebimento": "153"}}
{"loja_id": "LOJA-B", "resultado": "sem_match", "match": false,
 "evidencia": {"campo": "lote", "valor_alerta": ["148","153","166","167"], "valor_recebimento": "154"}}
```

Decisão humana (`POST /matches/{id}/decisao`):

```json
{"match_id": "m-7b2dd14d", "alerta_id": "vaidosa", "loja_id": "LOJA-A", "regra_aplicada": "lista",
 "status": "confirmado",
 "decisao": {"responsavel": "qualidade.loja03", "motivo": null, "em": "2026-11-19T20:58:14+00:00"}}
```

Segunda decisão sobre o mesmo match → **HTTP 409** ("Este match já possui uma decisão").

### Cenário 2 — Sanibras · data de corte (fabricado até 2026-06-12)

```json
{"loja_id": "LOJA-A", "resultado": "match",
 "evidencia": {"campo": "data_fabricacao", "valor_alerta": "2026-06-12", "valor_recebimento": "2026-06-12"}}
{"loja_id": "LOJA-B", "resultado": "sem_match",
 "evidencia": {"campo": "data_fabricacao", "valor_alerta": "2026-06-12", "valor_recebimento": "2026-06-13"}}
```

O dia limite é **incluído** e a regra usa a **data de fabricação**, não a validade.

**Lacuna encontrada (teste `xfail`):** com um suplemento de nome comercial próprio (ex.: `Whey Protein 900 g`, mesmo CNPJ, fabricado em 2026-06-12), o motor responde `sem_match`, porque compara o nome do produto com `Suplementos alimentares do fabricante`. O contrato v2 prevê `escopo = categoria_fabricante` (casar por CNPJ + categoria), ainda não implementado. É um **falso negativo** e deve ser corrigido antes de usar alertas desse tipo.

### Cenário 3 — Vaidosa · lote ilegível

```json
{"loja_id": "LOJA-C", "resultado": "verificacao_pendente", "motivos": ["lote"], "evidencia": null}
{"loja_id": "LOJA-D", "resultado": "verificacao_pendente", "motivos": ["lote"], "evidencia": null}
```

Lote só com espaços e lote `null` ficam pendentes; nenhum match conclusivo é criado.

### Teste de escala

| Recebimentos | Lojas | Matches (esperado) | Pendentes (esperado) | Tempo |
|---|---|---|---|---|
| 1.000 | 20 | **501 (501)** | **126 (126)** | **53 ms** |

![Motor em escala](img/graficos/motor_escala.png)

## 3. Painel da rede (captura de 19/11/2026)

API local + painel React com os cenários 1 e 2 carregados e o match da loja SP-ZL-03 já confirmado:

![Painel da rede](img/telas/painel_rede.png)

Observação: o alerta `bento` (sem regra de lote, `verificacao_pendente`) aparece com o selo "Recall Ativo". O selo deveria refletir `status_extracao` (melhoria registrada em `revisao_entrega_checklist.md`).

## 4. Extração e OCR

- Extração (Gemini): [`resultados_extracao.md`](resultados_extracao.md) — regra correta em 25/26, 0 falsos "sem recall", 0 alucinações.
- OCR: [`resultados_ocr.md`](resultados_ocr.md) — 0/12 erros confiantes, EAN 6/6, lote 4/7.

## 5. Ainda não medido

- **Tempo manual × automatizado** com cronômetro e o mesmo conjunto de alertas e recebimentos (métrica prevista na Nota de Produto). O tempo automatizado já está medido (53 ms / 1.000 recebimentos); falta o fluxo manual.
- **Fluxo do cidadão de ponta a ponta** (`POST /cidadao/verificar` com `data/demo/*.png`).
