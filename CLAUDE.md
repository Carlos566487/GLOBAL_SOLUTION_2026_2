# CLAUDE.md — Global Solution 2026.2 (FIAP · IA · 2º ano)

Contexto persistente do projeto para o Claude Code. Responda sempre em português do Brasil, de forma direta. Código primeiro, explicação curta depois.

- **Projeto:** `2TIAO/GLOBAL-SOLUTION-2/` (o resto do repositório é o template FIAP-PORTFOLIO-AI).
- **Meu papel no grupo:** **Engenheiro de IA** (papel 2, ver seção 6). Escopo de IA encerrado em 18/11/2026.
- **Integrantes:**

  | Função | Integrante(s) | RM |
  |---|---|---|
  | Product Owner e Pesquisador | João / Tayná Esteves | RM565999 / RM562491 |
  | Engenheiro de IA | João | RM565999 |
  | Dev Full Stack | Endrew Alves | RM563646 |
  | Tech Lead e Documentador | Carlos Eduardo | RM566487 |

- **Turma:** [PREENCHER]
- **Repositório:** [`Carlos566487/GLOBAL_SOLUTION_2026_2`](https://github.com/Carlos566487/GLOBAL_SOLUTION_2026_2) (https://github.com/Carlos566487/GLOBAL_SOLUTION_2026_2.git), com a estrutura do template `fiap-tutoria/FIAP-PORTFOLIO-AI`; deve ficar privado e compartilhado com `fiap-tutoria`. Repositório anterior: `JV-004/GS-2`.

---

## Escopo de IA: ENCERRADO (18/11/2026)

O escopo restrito ao papel de Engenheiro de IA foi **concluído e aprovado** em 18/11/2026. Não há escopo ativo: qualquer tarefa nova (inclusive em arquivos de outros papéis) depende de instrução explícita do usuário. O `Golden_Set_Recall.json` continua só leitura.

### O que foi entregue (código em `2TIAO/GLOBAL-SOLUTION-2/src/ia/`, 194 testes pytest)

| Entrega | Onde | Resultado |
|---|---|---|
| Modelos Pydantic dos formatos 1 e 5 (v2), pendências recalculadas | `schemas.py` | 36/36 registros do golden set validam com as pendências da PO |
| Divisão do golden set (opção A) | `data/divisao_golden_set.json` | 5 recolhimentos/10 registros no prompt + 1 sintético; 15/26 reservados |
| Textos oficiais de avaliação (Nestlé transcrita à mão) | `data/textos_avaliacao/`, `avaliacao/baixar_textos.py` | 20 textos; conferência de lotes 100% |
| Prompt de extração v1 (congelado) | `prompts/extracao_v1.md`, `prompt.py` | few-shot sem nenhum reservado (teste de vazamento) |
| Cliente Gemini | `gemini.py`, `config.py` | `gemini-3.5-flash-lite`; fallback 3.7/3.8-flash; 429/500/503 retentam, 504/timeout trocam de modelo; 90 s por extração |
| Extrator (nunca levanta exceção) + CLI | `extrator.py` | falha → alerta pendente `extracao:<motivo>`; fonte não oficial → lista vazia |
| Avaliação da extração | `docs/resultados_extracao.md` | regra de lote 25/26; 0 falsos "sem recall"; 0 alucinações em 11 alertas não rotulados; 25/39 erros de identidade são valores fora do texto; 14 erros reais de marca |
| Leitor da embalagem (OpenCV + EasyOCR + pyzbar, local) | `embalagem.py` | foto não salva nem enviada ao LLM; convenção de lote documentada |
| Teste do leitor em 12 fotos próprias | `data/fotos_teste/`, `docs/resultados_ocr.md` | erro confiante 0/12; EAN 6/6; lote 3/7 (regra original) e 4/7 (alinhada); 0 acertos conclusivos (sem EAN ou confiança < 0,8) |
| Imagens simuladas da demo | `data/demo/`, `avaliacao/gerar_demo.py` | 153 → leitura completa; 154 → leitura completa; ilegível → pendente `lote` |
| Documentação | `docs/interface_ia.md`, `docs/ia_limites_e_riscos.md`, `docs/dependencias_ia.md`, READMEs | interface, riscos, vieses, limitações e próximos passos |

### Pendências que ficam com outros papéis

- **Full-Stack (motor):** identidade pelo CNPJ quando houver; divergência só de marca → revisão humana (caso Neovite). Comparar lote sem espaços (`183/3B` × `183/3 B`). Usar `leitura.pendencias(tipo_regra)` no `POST /cidadao/verificar`.
- **Tech Lead:** catálogo EAN → (produto, marca) a partir da base de recebimentos; quando o coletor existir, a avaliação passa a ler `data/alertas_brutos/`; OCR para PDFs escaneados (caso Nestlé).
- **PO:** `escopo`/`categoria` no registro `sanibras`; marcar no gabarito os valores que vêm da RE; rotular os 7 recolhimentos fora do gabarito para o prompt v2.

---

## 1. Contexto acadêmico

- **Desafio:** CitizenTech — tecnologia centrada no cidadão. POC demonstrável que resolva um problema real do cotidiano.
- **Grupo:** 4 integrantes. Até 20 pontos por disciplina (até 20% da nota anual).
- **Entrega: 20/11/2026.** Sem atraso. O repositório não pode ser alterado depois do prazo.
- **Plágio:** soluções, arquiteturas ou códigos muito parecidos com os de outros grupos podem ser considerados plágio.
- **Linguagens:** só as do curso: **Python** e **JavaScript** (React / React Native).

### Requisitos obrigatórios do edital
- Problema real, público-alvo e justificativa com dados.
- Componente funcional que aplique conteúdos do curso.
- Dados reais ou de demonstração **identificados**: origem, limitações e cuidados de uso. Bases simuladas marcadas como tais.
- Pelo menos um resultado objetivo: tabela, gráfico, indicador ou tela.
- Pelo menos uma abordagem atual (IA Generativa, visão computacional etc.), justificada.
- Qualidade, governança, rastreabilidade, privacidade e segurança. Vieses e riscos identificados.
- Evidência de testes e limitações. **Tudo apresentado como funcional precisa ter sido testado.**
- Pelo menos um ODS da ONU, com a forma de medir o impacto.

### Entregáveis
1. **PDF único:** nomes completos + turma na 1ª página; Introdução, Desenvolvimento, Resultados, Conclusões; código como **texto legível** (sem prints, sem .zip); links do vídeo e do GitHub.
2. **GitHub privado** a partir do template; README.md em cada pasta; nomes dos integrantes no README da raiz; instruções de execução; compartilhado com **fiap-tutoria**. Proibido .zip, prints de código e venv compactado.
3. **Vídeo de até 5 min** no YouTube como "Não listado". Dizer **"QUERO CONCORRER"** nos primeiros segundos. Para o pódio, integrar e explicar o máximo de disciplinas.

---

## 2. Tema: Recall de alimentos

### Problema
Quando a Anvisa publica um recolhimento, a rede de supermercados precisa responder rápido **"quais lojas receberam esse lote?"**. Hoje isso é manual, ou se retira tudo da marca. O consumidor não sabe se o produto que tem em casa está afetado.

### Público
- **Cidadão:** fotografa a embalagem e descobre se o produto está em recall (foco CitizenTech).
- **Responsável de qualidade da rede:** vê as lojas afetadas, com evidência, e aprova a ação.

### Caso de referência
Em 24/07/2026, a Anvisa suspendeu a **Ricota Fresca Vaidosa** (Vaidosa Indústria e Comércio de Alimentos Ltda., CNPJ 02.896.434/0001-47), com recolhimento voluntário dos **lotes 148, 153, 166 e 167** (RE 2.905/2026).
Fonte: https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2026/ricota-fresca-da-marca-vaidosa-sera-recolhida-voluntariamente-pelo-fabricante

### Tipos de regra de lote (justificativa para usar LLM)
| Tipo | Exemplo |
|---|---|
| `lista` | Ricota Vaidosa: lotes 148, 153, 166, 167 |
| `sufixo` | Lotes com final X (no gabarito, só como teste sintético) |
| `data_corte` | Sanibras: todos os suplementos do fabricante fabricados até 12/06/2026 |
| `todos` | Equaliv, Nutra: todos os lotes do produto |

### Governança da fonte
Um site não oficial publicou o caso da ricota com lotes **L2305A a L2308D**, que não batem com os da Anvisa. O sistema **aceita só fonte governamental**: domínios `*.gov.br` (Anvisa, Ministério da Saúde, Prefeitura de SP) e `datalegis.net` (resoluções da Anvisa). A linhagem é rastreável por URL + hash.

### ODS
- **ODS 3 — Saúde e Bem-Estar.**
- A POC mede se o sistema acelera a identificação dos lotes que exigem ação. Medir quantas unidades deixariam de ser vendidas exige um piloto com uma rede real (limitação declarada).

---

## 3. Arquitetura

**Princípio central:** o LLM **só extrai**. Quem decide é o **motor de regras determinístico** e um **humano**.

```
LINHA 1 — Pipeline de alertas
Fonte oficial → Coletor (RPA · URL + hash) → Extrator LLM (texto → JSON) → Validador (Pydantic)
                                                                            │            │
                                                                      JSON válido     pendente
                                                                            ↓            ↓
LINHA 2 — Rede de supermercados
Recebimentos (base simulada) → Motor de regras → Aprovação humana → Painel da rede
                                     ↑                                    ┆ grava decisão
                                 lote lido                                ↓
LINHA 3 — Cidadão                                                   Log de auditoria
Foto da embalagem → Leitor OCR + EAN (foto não é salva) → Resposta (em_recall · sem_recall · pendente)
```

- Alerta com campo decisivo faltando **nunca chega ao motor**: vai ao painel como `verificacao_pendente`.
- Um único backend FastAPI serve o painel e o app do cidadão.

### Componentes
| # | Componente | O que faz | Tecnologia | Papel |
|---|---|---|---|---|
| 1 | Coletor | Busca notícias da Anvisa, resoluções e PDFs; salva texto bruto + URL + hash + data | requests, BeautifulSoup, pdfplumber | 4 |
| 2 | Extrator LLM | Texto do alerta → JSON (formato 1) | LLM via API, schema + few-shot, temperatura 0 | **2** |
| 3 | Validador | Checa o JSON; campo decisivo ausente → `verificacao_pendente` | Pydantic | **2** |
| 4 | Motor de regras | Cruza a regra com os recebimentos; gera match com evidência | Python puro, sem LLM | 3 |
| 5 | Base de recebimentos | Estoques fictícios de 10 a 20 lojas, `simulado: true` | Faker + SQLite | 4 |
| 6 | Aprovação humana | Confirma ou rejeita cada match | FastAPI + tela no painel | 3 |
| 7 | Log de auditoria | Fonte → extração → match → decisão, com quem e quando | SQLite append-only | 4 |
| 8 | Painel da rede | Alertas, lojas, evidências, indicadores | React + Vite | 3 |
| 9 | Leitor da embalagem | Lote, validade, fabricação e EAN da foto | EasyOCR/Tesseract + pyzbar + OpenCV | **2** |
| 10 | App do cidadão | Foto → resultado + orientação | Expo ou web responsiva | 3 |

### Endpoints
- `POST /alertas/coletar`
- `GET /alertas`
- `GET /matches?alerta_id=`
- `POST /matches/{id}/decisao`
- `POST /cidadao/verificar` — recebe a imagem e **não a armazena**.

---

## 4. Contrato de dados

Acordo sobre nomes, tipos e valores entre componentes. **Não alterar sem aprovação do grupo.**
As mudanças marcadas com **[v2]** foram propostas em 16/11 e estão em aprovação. O código já segue a v2.

### Normalização de lote (vale para todo o sistema)
- Lote, quando existe, é **sempre `str`**, nunca número. Preservar zeros à esquerda (`07225288`), barras (`183/3B`, `21/08/2026`), pontos (`2026.09.07`) e espaços internos (`LZ1 VAL200127 3 P 200126`).
- Normalizar = **`strip()` + `upper()`**. Nenhuma outra transformação.
- String vazia (ou só espaços) vira **`null`** na ingestão.

### Formato 1 — Alerta extraído (Extrator → Validador → Motor)
```json
{
  "alerta_id": "vaidosa",
  "fonte_url": "https://www.gov.br/anvisa/...",
  "fonte_hash": "sha256:...",
  "produto": "Ricota Fresca",
  "marca": "Vaidosa",
  "fabricante": "Vaidosa Indústria e Comércio de Alimentos Ltda.",
  "cnpj": "02.896.434/0001-47",
  "escopo": "produto",
  "categoria": null,
  "regra_lote": {
    "tipo": "lista",
    "lotes": ["148", "153", "166", "167"],
    "sufixo": null,
    "fabricado_ate": null
  },
  "status_extracao": "ok",
  "campos_pendentes": []
}
```
Exemplo `categoria_fabricante` (Sanibras):
```json
{
  "alerta_id": "sanibras",
  "produto": "Suplementos alimentares do fabricante",
  "marca": "Sanibras",
  "fabricante": "Sanibras Medicamentos e Nutrição Ltda.",
  "cnpj": "82.268.269/0001-18",
  "escopo": "categoria_fabricante",
  "categoria": "suplemento",
  "regra_lote": { "tipo": "data_corte", "lotes": [], "sufixo": null, "fabricado_ate": "2026-06-12" },
  "status_extracao": "ok",
  "campos_pendentes": []
}
```
- `regra_lote.tipo`: `lista` | `sufixo` | `data_corte` | `todos` | `null`.
- **[v2]** `escopo`: `produto` (padrão) | `categoria_fabricante`. **[v2]** `categoria`: `str | null`, obrigatória quando `escopo = categoria_fabricante`.
- `status_extracao`: `ok` | `verificacao_pendente`. Qualquer item em `campos_pendentes` bloqueia o match automático.
- **Nulos válidos (`Optional` no Pydantic):** `marca` (JMS, Nutra), `cnpj` (fabricante estrangeiro, ex.: Granoro) e `regra_lote.tipo` (Bentô). Nulo em campo decisivo vai para `campos_pendentes`; nulo em campo não decisivo só é registrado.
- **Um texto pode gerar vários alertas**, com a mesma URL e o mesmo `fonte_hash` (Militão + Cecco; Bentô + Equaliv; 9 apresentações Nestlé).

### Formato 2 — Recebimento (base fictícia → Motor)
```json
{
  "recebimento_id": "r-0001",
  "loja_id": "SP-ZL-03",
  "produto": "Ricota Fresca",
  "marca": "Vaidosa",
  "fabricante": "Vaidosa Indústria e Comércio de Alimentos Ltda.",
  "cnpj": "02.896.434/0001-47",
  "categoria": "laticinio",
  "ean": "7890000000000",
  "lote": "153",
  "data_fabricacao": "2026-06-10",
  "quantidade": 24,
  "recebido_em": "2026-06-14",
  "simulado": true
}
```
- **[v2]** `recebimento_id`: único.
- **[v2]** `lote`: `str | null`. Vazio vira `null` na ingestão.
- `fabricante`, `cnpj` e `categoria` são necessários para alertas `todos` e `categoria_fabricante`.

### Formato 3 — Match (Motor → Painel)
```json
{
  "match_id": "m-0001",
  "alerta_id": "vaidosa",
  "recebimento_id": "r-0001",
  "loja_id": "SP-ZL-03",
  "regra_aplicada": "lista",
  "evidencia": [
    { "campo": "cnpj",    "operador": "igual",   "valor_alerta": "02.896.434/0001-47", "valor_estoque": "02.896.434/0001-47" },
    { "campo": "produto", "operador": "igual",   "valor_alerta": "Ricota Fresca",      "valor_estoque": "Ricota Fresca" },
    { "campo": "lote",    "operador": "pertence", "valor_alerta": ["148", "153", "166", "167"], "valor_estoque": "153" }
  ],
  "status": "aguardando_aprovacao",
  "campos_pendentes": []
}
```
- **[v2]** `recebimento_id` adicionado.
- **[v2]** `status`: `aguardando_aprovacao` | `verificacao_pendente` | `confirmado` | `rejeitado`.
- **[v2]** `campos_pendentes`: lista dos dados a conferir (ex.: `["lote"]` no cenário 3). Não vazia → `status = verificacao_pendente`.
- **[v2]** `evidencia` é uma **lista de comparações** `{campo, operador, valor_alerta, valor_estoque}`, incluindo as de identidade (cnpj/produto/marca/categoria).
  - `operador` ∈ `pertence` (lista) | `termina_com` (sufixo) | `ate_inclusive` (data_corte) | `igual` (identidade).
  - Exemplo `data_corte`: `{"campo":"data_fabricacao","operador":"ate_inclusive","valor_alerta":"2026-06-12","valor_estoque":"2026-06-12"}`.
  - Em `todos`, a evidência contém só as comparações de identidade.

### Formato 4 — Decisão humana (Painel → Log)
```json
{ "match_id": "m-0001", "decisao": "confirmado", "responsavel": "qualidade.loja03", "em": "2026-11-20T10:15:00-03:00", "motivo": null }
```

### Formato 5 — Leitura da embalagem (Leitor OCR → Motor)
```json
{ "ean": "7890000000000", "produto": "Ricota Fresca", "marca": "Vaidosa", "lote": "153", "data_fabricacao": null, "validade": "2026-08-01", "confianca_ocr": 0.91 }
```
- **`confianca_ocr` < 0.8 → `verificacao_pendente`.**
- Alerta `data_corte` com `data_fabricacao` nula → `verificacao_pendente`. A validade não substitui a fabricação.
- Produto não identificado com segurança → `verificacao_pendente`.
- `sem_recall` significa apenas "sem correspondência na base consultada, com dados suficientes". A interface deixa esse alcance claro.

### Formato 6 — Resposta ao cidadão (API → App)
```json
{
  "resultado": "em_recall",
  "alerta_id": "vaidosa",
  "orientacao": "Não consuma. Devolva no local de compra ou contate o SAC do fabricante.",
  "fonte_url": "https://www.gov.br/anvisa/..."
}
```
- `resultado`: `em_recall` | `sem_recall` | `verificacao_pendente`.

### Formato 7 — Evento de auditoria (todas as etapas → Log)
```json
{ "evento": "match_confirmado", "entidade_id": "m-0001", "ator": "qualidade.loja03", "em": "2026-11-20T10:15:00-03:00", "hash_entrada": "sha256:..." }
```

---

## 5. Regras do motor (determinístico)

1. **Identidade antes do lote.** Escopo `produto`: confirmar produto + (marca ou CNPJ). Escopo `categoria_fabricante`: confirmar CNPJ + categoria. Só depois comparar o lote ou a data. Motivo: o mesmo código aparece em produtos diferentes (`5321046041` = NAN 400 g e 800 g; `5338046041` = NANLAC Supreme e Comfor; `251027` = 4 panetones D'Viez).
2. `lista`: lote normalizado **pertence** à lista normalizada.
3. `sufixo`: lote normalizado **termina exatamente** com o sufixo normalizado. Teste sintético `07`: `A107` → casa; `07A` → não casa; `null` → pendente.
4. `data_corte`: `data_fabricacao` **≤** `fabricado_ate` (inclui o dia limite). Nunca usar a validade.
5. `todos`: identidade confirmada basta.
6. Identidade confirmada, mas dado da regra ausente (lote/fabricação `null`) → match com `status = verificacao_pendente` e `campos_pendentes` preenchido.
7. **Na dúvida, `verificacao_pendente`.** Um falso "sem recall" é o pior erro possível.
8. **Vigência:** fica fora do contrato, em `data/alertas_nao_vigentes.json` (`alerta_id`, `motivo`, `fonte_url`). O motor ignora esses alertas nas consultas do cidadão. Primeiro caso: `de-marchi` (recurso administrativo posterior).

---

## 6. Papéis

1. **PO & Pesquisador:** dados oficiais, golden set, público, ODS, riscos/vieses/LGPD, PDF.
2. **Engenheiro de IA (meu papel):**
   - Prompt de extração com schema JSON e exemplos dos 4 tipos de regra.
   - Validador Pydantic + regra de `verificacao_pendente`.
   - Acurácia da extração por tipo de regra, por recolhimento e por registro, contra o golden set.
   - Leitor da embalagem (OCR + código de barras), testado com 10 a 15 fotos reais.
   - Limites do LLM: temperatura 0, sem decisão final, fonte citada em cada extração.
3. **Dev Full-Stack:** FastAPI, motor com testes por tipo, painel React, app do cidadão, acessibilidade, deploy opcional (Vercel/Render).
4. **Tech Lead & Documentador:** repositório, coletor com hash/URL, base fictícia, log de auditoria, teste ponta a ponta, READMEs e vídeo.

---

## 7. Cronograma

| Fase | Datas | Conteúdo |
|---|---|---|
| 1. Contrato | sáb 14/11 | Schemas e casos de demo |
| 2. Paralelo | 14 a 17/11 | Golden set, extrator, motor + API, coletor + base fictícia |
| 3. Integração | 17 a 18/11 | Coletor → extrator → validador → motor → painel; depois app + OCR |
| 4. Testes e métricas | 18 a 19/11 | Acurácia, falsos positivos/negativos, tempo, demo |
| 5. Entrega | 19/11 | PDF, READMEs, vídeo, convite à fiap-tutoria |
| 6. Folga | 20/11 | Só correções; nada no repositório após o envio |

---

## 8. Dados da PO — `2TIAO/GLOBAL-SOLUTION-2/data/`

| Arquivo | Conteúdo | Quem usa |
|---|---|---|
| `Golden_Set_Recall.json` | 20 recolhimentos reais, 36 registros (formato 1) + `teste_sintetico_sufixo` | IA (gabarito) |
| `Dataset_Recall_Anvisa.xlsx` | Abas "Alertas" (RE, pendência, fonte oficial) e "Produtos e lotes" | Tech Lead (coletor) |
| `Cenarios_Implementacao_e_Testes.md` | Os 3 cenários de demo | Full-Stack, Tech Lead |
| `Nota_de_Produto_e_Matriz_de_Riscos.md` | Hipótese, critérios de aceite, métricas, 8 riscos | PDF |
| `alertas_nao_vigentes.json` | Alertas excluídos das consultas do cidadão | Motor |

- 27 recolhimentos levantados (01/01/2025 a 16/11/2026); 20 no gabarito.
- **Tipos por recolhimento:** `lista` 16, `todos` 2 (Equaliv, Nutra), `data_corte` 1 (Sanibras), `null` 1 (Bentô); `sufixo` só sintético.
- **Pendências rotuladas:** Granoro, Militão, D'Viez (falta CNPJ); JMS (falta marca); Bentô (falta regra).
- **O gabarito não é base operacional:** não carregar no motor. `fonte_hash` está `null` e quem preenche é o coletor.
- Estrutura do JSON: `alertas[]` agrupa por `recolhimento_id`; cada item tem `rotulos[]` (um registro por produto, formato 1). `alerta_id` é único entre os 36 registros.

### Divisão do golden set (extrator)
- **Regras:** decidir exemplos × reservados **antes** de montar o prompt. Todas as apresentações de um recolhimento ficam no mesmo grupo. **Recolhimentos que compartilham o mesmo texto-fonte também ficam no mesmo grupo** (Militão + Cecco; Bentô + Equaliv). A entrada do extrator é o **texto oficial**; o JSON é o gabarito. Enviar a lista dos reservados à PO.
- **Decisão (Engenheiro de IA, 17/11, opção A):** Equaliv e Bentô vêm do mesmo texto, então ficam juntos nos reservados.
  - **Exemplos do prompt:** crystal, la-vaquita, jms, nutra, granoro (5 recolhimentos, 10 registros) + 1 `data_corte` **sintético**.
  - **Reservados:** os outros 15 recolhimentos (26 registros).
  - Lista em `data/divisao_golden_set.json`.
- Reportar acurácia **por recolhimento e por registro** (Nestlé tem 9 registros).
- **Até a PO atualizar o registro Sanibras com `escopo`/`categoria`, excluir esses dois campos da acurácia.**

### Pendências externas (não bloqueiam o código)
- Tech Lead: conferir a URL do caso `agua-da-serra` (`anttlegis` × `anvisalegis`).
- PO: incluir `escopo` e `categoria` no registro `sanibras` do gabarito.
- Grupo: aprovar as mudanças [v2] do contrato.

---

## 9. Testes, demo e métricas

### Cenários de demo (`data/Cenarios_Implementacao_e_Testes.md`)
| Cenário | Entrada simulada | Esperado |
|---|---|---|
| 1. Vaidosa · lista | Loja A lote `153`; Loja B lote `154` | A: match `aguardando_aprovacao` → confirmar → `confirmado` + evento no log. B: sem match |
| 2. Sanibras · data de corte | Mesmo suplemento: Loja A fabricado `2026-06-12`; Loja B `2026-06-13` | A: match com evidência `ate_inclusive`. B: sem match |
| 3. Vaidosa · lote ilegível | Loja C com lote ausente/vazio | Match `verificacao_pendente`, `campos_pendentes: ["lote"]`. App com foto de lote ilegível → também pendente |

Para cada cenário, guardar: entrada, esperado, observado e um print do painel ou trecho da API. No cenário 1, guardar também o evento de decisão no log.

### Testes extras do motor
- Mesmo lote em produtos diferentes: `5321046041`, `5338046041`, `251027`.
- Sufixo sintético `07` (`A107`, `07A`, `null`). **Fora da acurácia com alertas reais.**

### Métricas
- Tempo para localizar lojas afetadas: manual × automatizado.
- Falsos negativos e falsos positivos.
- Acurácia da extração por tipo de regra, por recolhimento e por registro.

### Integração de disciplinas (pódio)
| Componente | Disciplina |
|---|---|
| Coleta automática | Automação / RPA |
| Extração estruturada | IA Generativa / prompts |
| Cruzamento + pendente | Regras de negócio / qualidade de dados |
| Leitura do lote na foto | Visão computacional |
| Linhagem fonte → extração → match → aprovação | Governança / rastreabilidade |
| Painel + app | React / React Native |

---

## 10. Estrutura do repositório

```
GLOBAL_SOLUTION_2026_2/  (template FIAP-PORTFOLIO-AI)
├── CLAUDE.md
├── .gitignore
└── 2TIAO/GLOBAL-SOLUTION-2/
    ├── README.md            # descrição, execução, integrantes, links
    ├── data/                # dados da PO, alertas brutos, recebimentos, fotos de teste
    ├── docs/                # contratos, arquitetura, riscos/LGPD, métricas
    ├── notebooks/           # avaliação do extrator e do OCR
    └── src/
        ├── ia/              # Engenheiro de IA: schemas (formatos 1 e 5), prompts, extrator, avaliação, OCR + tests/
        ├── backend/         # FastAPI: coletor, motor, auditoria, db + tests/
        ├── painel/          # React + Vite
        └── app-cidadao/     # Expo ou web responsiva
```

---

## 11. Regras para o Claude Code

- Nunca deixe o LLM decidir um match. Ele só extrai; quem decide é o motor de regras.
- O motor confirma a identidade do produto antes de comparar o lote. Lote, quando existe, é texto.
- `data_corte` compara `data_fabricacao` (inclusive o dia limite), nunca a validade.
- Na dúvida, devolva `verificacao_pendente`.
- Toda base simulada leva `simulado: true` e é identificada no README e no PDF.
- Não armazene as fotos do cidadão. Mascare dados pessoais antes de qualquer envio ao LLM.
- Respeite exatamente os 7 formatos da seção 4 (versão [v2]).
- Cada funcionalidade apresentada como pronta precisa de teste (pytest no backend).
- README.md em cada pasta, conforme o template FIAP.
- Não commite .zip, venv, `.env` nem chaves de API.
