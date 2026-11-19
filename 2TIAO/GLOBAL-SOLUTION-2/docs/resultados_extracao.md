# Resultados da extração

| Item | Valor |
|---|---|
| Modelo avaliado (`EVAL_MODEL`) | `gemini-3.5-flash-lite` |
| Modelo que respondeu | `gemini-3.5-flash-lite` (versão: gemini-3.5-flash-lite) |
| Fallback | desligado |
| Prompt | `extracao_v1` · temperatura 0.0 |
| Executado em | 2026-11-17T19:36:07-03:00 |
| Conjunto | 15 recolhimentos reservados · 26 registros · 13 textos (militao+cecco e bento+equaliv compartilham o texto) |
| Falhas de serviço | 0 texto(s) |

## Resumo para o PDF

- **Regra de lote correta em 25/26 registros.**
- **0 falsos "sem recall":** o único erro de regra terminou em `verificacao_pendente`. Dos 21 registros com alguma divergência, 19 ficaram pendentes; 2 ficaram `ok` com divergência só de identidade (`neovite`, `cecco`).
- **0 alucinações** entre os 11 alertas não rotulados (todos com trecho do texto que os sustenta).
- **Erros de identidade:** 25/39 campos com erro têm valor de gabarito ausente do texto de entrada; os erros reais do extrator se concentram em **marca** (14).

## Resumo

Acerto **por registro** (cada apresentação de produto conta uma vez). "Totalmente correto" = regra + os 4 campos de identidade.

- **Contra o gabarito:** todos os campos contam.
- **Sobre o recuperável:** só contam os campos cujo valor do gabarito aparece no texto de entrada (coluna de diagnóstico); o denominador muda por campo. "Totalmente correto" = todos os campos recuperáveis do registro corretos.

| Escopo | Métrica | Registros | Regra completa | Produto | Marca | Fabricante | CNPJ | **Totalmente correto** |
|---|---|---|---|---|---|---|---|---|
| Todos os reservados | contra o gabarito | 26 | 25/26 (96%) | 17/26 (65%) | 12/26 (46%) | 23/26 (88%) | 14/26 (54%) | **5/26 (19%)** |
| | sobre o recuperável | 26 | 25/25 (100%) | 17/17 (100%) | 12/26 (46%) | 23/23 (100%) | 14/14 (100%) | **12/26 (46%)** |
| Sem a Nestlé | contra o gabarito | 17 | 16/17 (94%) | 11/17 (65%) | 10/17 (59%) | 14/17 (82%) | 14/17 (82%) | **5/17 (29%)** |
| | sobre o recuperável | 17 | 16/16 (100%) | 11/11 (100%) | 10/17 (59%) | 14/14 (100%) | 14/14 (100%) | **10/17 (59%)** |
| Nestlé (entrada transcrita) | contra o gabarito | 9 | 9/9 (100%) | 6/9 (67%) | 2/9 (22%) | 9/9 (100%) | 0/9 (0%) | **0/9 (0%)** |
| | sobre o recuperável | 9 | 9/9 (100%) | 6/6 (100%) | 2/9 (22%) | 9/9 (100%) | — | **2/9 (22%)** |

Status (pendência) igual ao do gabarito: Todos os reservados: 12/26 (46%) · Sem a Nestlé: 12/17 (71%) · Nestlé (entrada transcrita): 0/9 (0%).

Acerto **por recolhimento** (o recolhimento só conta se **todos** os seus registros acertarem).

| Escopo | Métrica | Recolhimentos | Regra completa | Identidade (4 campos) | **Totalmente correto** |
|---|---|---|---|---|---|
| Todos os reservados | contra o gabarito | 15 | 14/15 (93%) | 5/15 (33%) | **5/15 (33%)** |
| | sobre o recuperável | 15 | 15/15 (100%) | 10/15 (67%) | **10/15 (67%)** |
| Sem a Nestlé | contra o gabarito | 14 | 13/14 (93%) | 5/14 (36%) | **5/14 (36%)** |
| | sobre o recuperável | 14 | 14/14 (100%) | 10/14 (71%) | **10/14 (71%)** |
| Nestlé (entrada transcrita) | contra o gabarito | 1 | 1/1 (100%) | 0/1 (0%) | **0/1 (0%)** |
| | sobre o recuperável | 1 | 1/1 (100%) | 0/1 (0%) | **0/1 (0%)** |

## Por tipo de regra (tipo do gabarito)

| Tipo | Recolhimentos | Registros | Regra completa (registro) | Totalmente correto (registro) | Totalmente correto, sobre o recuperável (registro) | Regra completa (recolhimento) |
|---|---|---|---|---|---|---|
| `lista` | 12 | 23 | 23/23 (100%) | 5/23 (22%) | 11/23 (48%) | 12/12 (100%) |
| `sufixo` | 0 | 0 | — | — | — | sem caso real no gabarito |
| `data_corte` | 1 | 1 | 1/1 (100%) | 0/1 (0%) | 0/1 (0%) | 1/1 (100%) |
| `todos` | 1 | 1 | 0/1 (0%) | 0/1 (0%) | 1/1 (100%) | 0/1 (0%) |
| `null` | 1 | 1 | 1/1 (100%) | 0/1 (0%) | 0/1 (0%) | 1/1 (100%) |

## Por recolhimento

| Recolhimento | Tipo | Registros | Pareados | Regra | Produto | Marca | Fabricante | CNPJ | Totalmente correto | Obs. |
|---|---|---|---|---|---|---|---|---|---|---|
| aptamil | `lista` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |  |
| neovite | `lista` | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 |  |
| de-marchi | `lista` | 1 | 1/1 | 1/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 |  |
| ubon | `lista` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 |  |
| vaidosa | `lista` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |  |
| italy | `lista` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |  |
| kf | `lista` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |  |
| militao | `lista` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |  |
| cecco | `lista` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 0/1 |  |
| agua-da-serra | `lista` | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |  |
| dviez | `lista` | 4 | 4/4 | 4/4 | 3/4 | 0/4 | 4/4 | 4/4 | 0/4 |  |
| sanibras | `data_corte` | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 |  |
| bento | `null` | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 |  |
| equaliv | `todos` | 1 | 1/1 | 0/1 | 0/1 | 1/1 | 1/1 | 1/1 | 0/1 |  |
| nestle-formulas | `lista` | 9 | 9/9 | 9/9 | 6/9 | 2/9 | 9/9 | 0/9 | 0/9 | entrada transcrita |

## Falsos negativos (0)

Registros do gabarito sem alerta extraído pareado (erro do extrator).

- Nenhum.

## Divergências nos registros pareados (21 registros, 39 campos com erro)

**Diagnóstico (não altera a acurácia):** em **25 de 39** campos com erro, o valor do gabarito **não aparece no texto de entrada** (a PO completou com outra fonte, como a RE). Nesses casos o extrator devolveu `null` ou o valor do texto, como manda o prompt ("nunca invente").

| Campo | Erros | Valor do gabarito ausente do texto |
|---|---|---|
| Regra completa | 1 | 1 |
| Produto | 9 | 9 |
| Marca | 14 | 0 |
| Fabricante | 3 | 3 |
| CNPJ | 12 | 12 |

| Registro | Campo | Gabarito | Extraído | Valor do gabarito está no texto? |
|---|---|---|---|---|
| `aptamil` | Fabricante | Danone Ltda. | Danone | **não** |
| `aptamil` | CNPJ | 23.643.315/0001-52 | null | **não** |
| `aptamil` | Status (pendência) | ok | verificacao_pendente | — |
| `neovite` | Produto | Suplemento alimentar Neovite Visão | Neovite Visão | **não** |
| `neovite` | Marca | Neovite | Bausch Lomb | sim |
| `de-marchi` | Produto | Polpa de morango | Polpa de fruta de morango | **não** |
| `de-marchi` | Fabricante | De Marchi Indústria e Comércio de Frutas Ltda. | null | **não** |
| `de-marchi` | CNPJ | 52.884.061/0001-62 | null | **não** |
| `de-marchi` | Status (pendência) | ok | verificacao_pendente | — |
| `ubon` | CNPJ | 18.116.328/0001-33 | null | **não** |
| `ubon` | Status (pendência) | ok | verificacao_pendente | — |
| `cecco` | Fabricante | Cia Bel de Alimentos (Festval) | Cia Bel de Alimentlos (Festval) | **não** |
| `dviez-01` | Marca | D’Viez | null | sim |
| `dviez-02` | Produto | Panetone Nossa Língua Trufado com Bombons, 700 g | Panetone Nossa Língua Trufado com Bombons "Formato de Língua de Gato", 700g | **não** |
| `dviez-02` | Marca | D’Viez | null | sim |
| `dviez-03` | Marca | D’Viez | null | sim |
| `dviez-04` | Marca | D’Viez | null | sim |
| `sanibras` | Produto | Suplementos alimentares do fabricante | Suplementos alimentares | **não** |
| `sanibras` | Marca | Sanibras | null | sim |
| `sanibras` | Status (pendência) | ok | verificacao_pendente | — |
| `bento` | Produto | Picolé Magnésio + Inositol Relief 3.0 | Picolé Bentô Gelatos Magnésio + Inositol Relief 3.0 | **não** |
| `bento` | Marca | Bentô Gelatos | Gelatos | sim |
| `equaliv` | Regra completa | todos | None | **não** |
| `equaliv` | Produto | Body Strong Protein, cacau | Body Strong Proetein, sabor cacau | **não** |
| `equaliv` | Status (pendência) | ok | verificacao_pendente | — |
| `nestle-formulas-01` | CNPJ | 60.409.075/0001-52 | null | **não** |
| `nestle-formulas-01` | Status (pendência) | ok | verificacao_pendente | — |
| `nestle-formulas-02` | Marca | NAN Supreme Pro | NAN | sim |
| `nestle-formulas-02` | CNPJ | 60.409.075/0001-52 | null | **não** |
| `nestle-formulas-02` | Status (pendência) | ok | verificacao_pendente | — |
| `nestle-formulas-03` | Marca | NAN Supreme Pro | NAN | sim |
| `nestle-formulas-03` | CNPJ | 60.409.075/0001-52 | null | **não** |
| `nestle-formulas-03` | Status (pendência) | ok | verificacao_pendente | — |
| `nestle-formulas-04` | Marca | NAN Supreme Pro | NAN | sim |
| `nestle-formulas-04` | CNPJ | 60.409.075/0001-52 | null | **não** |
| `nestle-formulas-04` | Status (pendência) | ok | verificacao_pendente | — |
| `nestle-formulas-05` | Produto | NANLAC Supreme Pro, 1–3 anos, 800 g | NANLAC SUPREME PRO 1 A 3 Anos 800g | **não** |
| `nestle-formulas-05` | Marca | NANLAC Supreme Pro | NANLAC | sim |
| `nestle-formulas-05` | CNPJ | 60.409.075/0001-52 | null | **não** |
| `nestle-formulas-05` | Status (pendência) | ok | verificacao_pendente | — |
| `nestle-formulas-06` | Produto | NANLAC Comfor, 1–3 anos, 800 g | NANLAC COMFOR 1 A 3 ANOS 800g | **não** |
| `nestle-formulas-06` | Marca | NANLAC Comfor | NANLAC | sim |
| `nestle-formulas-06` | CNPJ | 60.409.075/0001-52 | null | **não** |
| `nestle-formulas-06` | Status (pendência) | ok | verificacao_pendente | — |
| `nestle-formulas-07` | Produto | NANLAC Comfor, 1–3 anos, 1,6 kg | NANLAC COMFOR 1 A 3 Anos 1,6kg | **não** |
| `nestle-formulas-07` | Marca | NANLAC Comfor | NANLAC | sim |
| `nestle-formulas-07` | CNPJ | 60.409.075/0001-52 | null | **não** |
| `nestle-formulas-07` | Status (pendência) | ok | verificacao_pendente | — |
| `nestle-formulas-08` | Marca | NAN Science Pro Sensitive | NAN | sim |
| `nestle-formulas-08` | CNPJ | 60.409.075/0001-52 | null | **não** |
| `nestle-formulas-08` | Status (pendência) | ok | verificacao_pendente | — |
| `nestle-formulas-09` | CNPJ | 60.409.075/0001-52 | null | **não** |
| `nestle-formulas-09` | Status (pendência) | ok | verificacao_pendente | — |

## Pareamentos ambíguos (0)

- Nenhum.

## revisao_manual: alertas extraídos sem registro no gabarito (11; possíveis alucinações: 0)

Fora da acurácia. O gabarito rotula só os produtos escolhidos pela PO; outros produtos citados no mesmo texto aparecem aqui. Sem trecho que sustente o alerta = **possível alucinação** (risco crítico 2 da matriz da PO).

| Texto | Produto extraído | Regra | Situação | Trecho do texto |
|---|---|---|---|---|
| de-marchi | Azeite extravirgem | todos | sustentado pelo texto | 2) Azeite extravirgem – marca Vale dos Vinhedos. |
| de-marchi | Champignon inteiro em conserva | lista: ['241023CHI'] | sustentado pelo texto | A medida abrange o lote 241023CHI, com data de validade de 10/2026. |
| de-marchi | Molho de alho | lista: ['29'] | sustentado pelo texto | A medida abrange o lote 29, com data de validade de 01/2026. |
| ubon | Alimentos Infantis e Alim. de Transição para Lactentes e Crianças de Primeira Infância "PF da Nina" | todos | sustentado pelo texto | De acordo com a publicação, os produtos Alimentos Infantis e Alim. de Transição para Lactentes e Crianças de Primeira Infância “PF da Nina”, fabricados pela empresa PF da Nina Nutrição Infantil Ltda., devem ser apreendidos. Além disso, todos os produtos tiveram a sua comercialização, a sua distribui |
| dviez | Pasta de Cacau e Avelã com Cogumelos | todos | sustentado pelo texto | Pasta de Cacau e Avelã com Cogumelos da marca Smush Smushnuts (todos os lotes). |
| dviez | Pasta de Amendoim com Cogumelos | todos | sustentado pelo texto | Pasta de Amendoim com Cogumelos da marca Smush Smushnuts (todos os lotes). |
| dviez | Barra de Frutas, Amendoim, Clara de Ovo e Cogumelos | todos | sustentado pelo texto | Barra de Frutas, Amendoim, Clara de Ovo e Cogumelos da marca Smushn Go (todos os lotes). |
| dviez | Granola Coco | todos | sustentado pelo texto | Granola da marca Smush Smushnola Granola Coco (todos os lotes). |
| dviez | Mix de Castanhas, Sementes e Cogumelos | todos | sustentado pelo texto | Mix de Castanhas, Sementes e Cogumelos da marca Smush Smushnola Granola Keto (todos os lotes). |
| dviez | Cápsula de Café | todos | sustentado pelo texto | Cápsula de Café da marca Smush Mushroom Espresso (todos os lotes). |
| dviez | Cápsula de Café | todos | sustentado pelo texto | Cápsula de Café da marca Smush Mushroom Espresso (todos os lotes). |

## Falhas de serviço (0)

- Nenhuma.

## Regras de comparação

- **Conjunto avaliado:** só os 15 recolhimentos reservados de `data/divisao_golden_set.json`. Nenhum aparece no prompt.
- **Pareamento:** cada registro do gabarito é pareado com no máximo um alerta extraído **do mesmo texto**, pelo produto normalizado (similaridade de Jaccard entre as palavras ≥ 0.3) e CNPJ compatível (mesmos dígitos, ou nulo de um dos lados). Atribuição gulosa pela maior similaridade. Os lotes **não** entram no pareamento, para não favorecer a métrica da regra. Igualdade exata do produto não serve para parear: a PO reescreveu os nomes (ex.: `Sardinha-laje congelada espalmada, 800 g` × texto `PEIXE CONGELADO SARDINHA LAJE ESPALMADA 800G`).
- **Ambíguo:** outro candidato com similaridade a menos de 0.05 do escolhido.
- **Registro sem par** = falso negativo: conta como erro em todos os campos.
- **Alerta sem par** = fora da acurácia, listado em `revisao_manual` com o trecho que o sustenta.
- **Regra completa:** mesmo `tipo` e, conforme o tipo: `lista` = mesmo **conjunto** de lotes; `sufixo` = mesmo sufixo; `data_corte` = mesma data; `todos`/`null` = só o tipo.
- **Lote:** comparado pela chave **sem nenhum espaço + maiúsculas** (`183/3 B` = `183/3B`). Zeros à esquerda contam (`07225288` ≠ `7225288`). A extração em si continua fiel ao texto.
- **Produto e marca:** minúsculas, sem acento, sem pontuação e espaço padronizado (inclui separar número de unidade: `800g` = `800 g`).
- **Fabricante:** igual a produto, removendo antes o conteúdo entre parênteses (anotações da PO, ex.: `(Bausch Lomb)`).
- **CNPJ:** só os dígitos. Nulo × nulo conta como acerto em qualquer campo.
- **Status (pendência):** `status_extracao` igual ao do gabarito. Informativo, fora do "totalmente correto".
- **"Valor do gabarito está no texto?"**: diagnóstico. Procura o valor normalizado do gabarito no texto de entrada (CNPJ por dígitos; lista = todos os lotes; `todos` = a palavra "todos"; `data_corte` = a data DD/MM/AAAA). Não muda a acurácia.
- **Fora da conta:** `escopo` e `categoria`, até a PO atualizar o registro `sanibras` no gabarito.
- **Falha de serviço:** o modelo não respondeu (`orcamento_esgotado`, `modelos_esgotados`, `erro_llm:*`). Os registros desse texto saem dos denominadores e são listados à parte.
- **Nestlé:** entrada transcrita à mão das tabelas em imagem do PDF; reportada também à parte.

## Nota para o motor (Full-Stack)

Com a normalização atual do contrato (`strip` + `upper`), o lote `183/3B` lido numa embalagem **não casa** com o alerta `183/3 B`. Recomendação: o motor usar a mesma chave da avaliação (sem nenhum espaço). A decisão é do motor.
