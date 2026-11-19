# Resultados do leitor da embalagem (OCR + código de barras)

| Item | Valor |
|---|---|
| Motor | OpenCV (CLAHE) + EasyOCR (pt, en; CPU, local) + pyzbar |
| Limite de confiança | `confianca_ocr` < 0.8 → pendente |
| Avaliado como regra | `lista` (exige lote e produto identificado) |
| Executado em | 2026-11-18T19:24:45-03:00 |
| Fotos | 12 próprias (`data/fotos_teste/`), gabarito `gabarito_fotos.csv` |
| Tempo médio por foto | 8.0 s |

## Duas versões do leitor (transparência)

- A **convenção de delimitação do lote** do leitor foi **alinhada à convenção do gabarito depois da inspeção das fotos de teste** (commit `07fcf16`; os testes novos dessa mudança usam os padrões das fotos).
- É uma mudança de **convenção** (onde o lote começa e termina no texto lido), não um ajuste de modelo: o EasyOCR, o pré-processamento, o limite de confiança e o pyzbar são os mesmos nas duas versões.
- Mesmo assim, a **regra original é a medição sem contaminação**. As duas são reportadas lado a lado.
- A **rotação continua sem correção** (limitação declarada antes das fotos, não ajustada): a foto01 está girada 90°.

Leitura dos resultados: **acerto** = sem pendência, lote e EAN corretos; **pendente (legível)** = pediu revisão sem necessidade (seguro, pouco útil); **pendente correto** = foto sem lote legível e o sistema não respondeu de forma conclusiva; **erro confiante** = sem pendência, mas com lote/EAN errado, ou foto sem lote legível sem pendência. É o erro que pode virar falso "sem recall". As fotos podem estar em mais de um grupo (validade só de mês/ano também tem lote legível).

## Regra original (medição sem contaminação)

Leitor do commit anterior a `07fcf16`: marcadores `LOTE`/`LOT`/`L:`/`L.`; o lote vai até uma sigla de outro campo ou o fim da linha; não para em hora/data; não reconhece `L029` nem o rótulo "Validade/Lote".

| Grupo | Fotos | Acerto | Pendente (legível) | Pendente correto | **Erro confiante** | Lote correto | EAN correto |
|---|---|---|---|---|---|---|---|
| Lote legível | 7 | 0/7 (0%) | 7/7 (100%) | 0/7 (0%) | **0/7 (0%)** | 3/7 (43%) | 2/2 (100%) |
| Só EAN (lote fora do quadro) | 4 | 0/4 (0%) | 0/4 (0%) | 4/4 (100%) | **0/4 (0%)** | — | 4/4 (100%) |
| Controle negativo (lote ilegível) | 1 | 0/1 (0%) | 0/1 (0%) | 1/1 (100%) | **0/1 (0%)** | — | — |
| Validade só de mês/ano | 3 | 0/3 (0%) | 3/3 (100%) | 0/3 (0%) | **0/3 (0%)** | 1/3 (33%) | 1/1 (100%) |
| **Todas** | 12 | 0/12 (0%) | 7/12 (58%) | 5/12 (42%) | **0/12 (0%)** | 3/7 (43%) | 6/6 (100%) |

Acerto por campo (denominador = fotos em que o gabarito tem o valor; "lido errado" = leu um valor diferente, pior que não ler):

| Campo | Correto | Não lido | Lido errado |
|---|---|---|---|
| ean | 6/6 (100%) | 0 | 0 |
| lote | 3/7 (43%) | 4 | 0 |
| data_fabricacao | 0/1 (0%) | 1 | 0 |
| validade | 1/5 (20%) | 4 | 0 |

Motivos de pendência nas 7 fotos com lote legível (uma foto pode ter mais de um). Só 2 dessas fotos têm EAN no quadro; sem EAN o produto não é identificado e a foto fica pendente por desenho, então o teto de "acerto" neste grupo é 2/7.

| Motivo | Fotos |
|---|---|
| produto não identificado (sem EAN legível) | 5/7 (foto02, foto04, foto08, foto09, foto12) |
| lote não lido | 4/7 (foto01, foto02, foto04, foto08) |
| confiança do OCR < 0.8 | 7/7 (foto01, foto02, foto04, foto08, foto09, foto11, foto12) |

<details><summary>Detalhe por foto</summary>

| Foto | Grupo | Resultado | EAN | Lote (gabarito → lido) | Fab. | Val. | Confiança | Pendências |
|---|---|---|---|---|---|---|---|---|
| foto01.jpg | Lote legível | pendente (legível) | ok | 172U404I → — | não lido | não lido | 0.00 | confianca_ocr, lote |
| foto02.jpg | Lote legível | pendente (legível) | — | LJA 076 4051 2 → — | — | não lido | 0.00 | confianca_ocr, produto, lote |
| foto03.jpg | Só EAN (lote fora do quadro) | pendente correto | ok | — → — | — | — | 0.00 | confianca_ocr, lote |
| foto04.jpg | Lote legível, Validade só de mês/ano | pendente (legível) | — | 029 SF → — | — | — | 0.00 | confianca_ocr, produto, lote |
| foto05.jpg | Só EAN (lote fora do quadro) | pendente correto | ok | — → — | — | — | 0.00 | confianca_ocr, lote |
| foto06.jpg | Só EAN (lote fora do quadro) | pendente correto | ok | — → — | — | — | 0.00 | confianca_ocr, lote |
| foto07.jpg | Só EAN (lote fora do quadro) | pendente correto | ok | — → — | — | — | 0.00 | confianca_ocr, lote |
| foto08.jpg | Lote legível, Validade só de mês/ano | pendente (legível) | — | 23 → — | — | — | 0.00 | confianca_ocr, produto, lote |
| foto09.jpg | Lote legível | pendente (legível) | — | JGU 080926 → JGU 080926 | — | não lido | 0.79 | confianca_ocr, produto |
| foto10.jpg | Controle negativo (lote ilegível) | pendente correto | — | — → — | — | não lido | 0.00 | confianca_ocr, produto, lote |
| foto11.jpg | Lote legível, Validade só de mês/ano | pendente (legível) | ok | H26H0115 → H26H0115 | — | — | 0.69 | confianca_ocr |
| foto12.jpg | Lote legível | pendente (legível) | — | 3260 → 3260 | — | ok | 0.54 | confianca_ocr, produto |

</details>

## Regra alinhada (convenção do gabarito)

Leitor atual: marcador `L`, `L:`, `L.` (ou `L` colado ao número); o lote vai até a primeira hora/data, rótulo de outro campo ou o fim da linha; com o rótulo "Lote" sem marcador, a linha de código seguinte que não é data. Ver `docs/interface_ia.md`.

| Grupo | Fotos | Acerto | Pendente (legível) | Pendente correto | **Erro confiante** | Lote correto | EAN correto |
|---|---|---|---|---|---|---|---|
| Lote legível | 7 | 0/7 (0%) | 7/7 (100%) | 0/7 (0%) | **0/7 (0%)** | 4/7 (57%) | 2/2 (100%) |
| Só EAN (lote fora do quadro) | 4 | 0/4 (0%) | 0/4 (0%) | 4/4 (100%) | **0/4 (0%)** | — | 4/4 (100%) |
| Controle negativo (lote ilegível) | 1 | 0/1 (0%) | 0/1 (0%) | 1/1 (100%) | **0/1 (0%)** | — | — |
| Validade só de mês/ano | 3 | 0/3 (0%) | 3/3 (100%) | 0/3 (0%) | **0/3 (0%)** | 1/3 (33%) | 1/1 (100%) |
| **Todas** | 12 | 0/12 (0%) | 7/12 (58%) | 5/12 (42%) | **0/12 (0%)** | 4/7 (57%) | 6/6 (100%) |

Acerto por campo (denominador = fotos em que o gabarito tem o valor; "lido errado" = leu um valor diferente, pior que não ler):

| Campo | Correto | Não lido | Lido errado |
|---|---|---|---|
| ean | 6/6 (100%) | 0 | 0 |
| lote | 4/7 (57%) | 3 | 0 |
| data_fabricacao | 0/1 (0%) | 1 | 0 |
| validade | 1/5 (20%) | 4 | 0 |

Motivos de pendência nas 7 fotos com lote legível (uma foto pode ter mais de um). Só 2 dessas fotos têm EAN no quadro; sem EAN o produto não é identificado e a foto fica pendente por desenho, então o teto de "acerto" neste grupo é 2/7.

| Motivo | Fotos |
|---|---|
| produto não identificado (sem EAN legível) | 5/7 (foto02, foto04, foto08, foto09, foto12) |
| lote não lido | 3/7 (foto01, foto04, foto08) |
| confiança do OCR < 0.8 | 6/7 (foto01, foto04, foto08, foto09, foto11, foto12) |

<details><summary>Detalhe por foto</summary>

| Foto | Grupo | Resultado | EAN | Lote (gabarito → lido) | Fab. | Val. | Confiança | Pendências |
|---|---|---|---|---|---|---|---|---|
| foto01.jpg | Lote legível | pendente (legível) | ok | 172U404I → — | não lido | não lido | 0.00 | confianca_ocr, lote |
| foto02.jpg | Lote legível | pendente (legível) | — | LJA 076 4051 2 → LJA 076 4051 2 | — | não lido | 0.88 | produto |
| foto03.jpg | Só EAN (lote fora do quadro) | pendente correto | ok | — → — | — | — | 0.00 | confianca_ocr, lote |
| foto04.jpg | Lote legível, Validade só de mês/ano | pendente (legível) | — | 029 SF → — | — | — | 0.00 | confianca_ocr, produto, lote |
| foto05.jpg | Só EAN (lote fora do quadro) | pendente correto | ok | — → — | — | — | 0.00 | confianca_ocr, lote |
| foto06.jpg | Só EAN (lote fora do quadro) | pendente correto | ok | — → — | — | — | 0.00 | confianca_ocr, lote |
| foto07.jpg | Só EAN (lote fora do quadro) | pendente correto | ok | — → — | — | — | 0.00 | confianca_ocr, lote |
| foto08.jpg | Lote legível, Validade só de mês/ano | pendente (legível) | — | 23 → — | — | — | 0.00 | confianca_ocr, produto, lote |
| foto09.jpg | Lote legível | pendente (legível) | — | JGU 080926 → JGU 080926 | — | não lido | 0.79 | confianca_ocr, produto |
| foto10.jpg | Controle negativo (lote ilegível) | pendente correto | — | — → — | — | não lido | 0.00 | confianca_ocr, produto, lote |
| foto11.jpg | Lote legível, Validade só de mês/ano | pendente (legível) | ok | H26H0115 → H26H0115 | — | — | 0.69 | confianca_ocr |
| foto12.jpg | Lote legível | pendente (legível) | — | 3260 → 3260 | — | ok | 0.54 | confianca_ocr, produto |

</details>

## Imagens simuladas para demonstração

**Fora das métricas acima.** Rótulos desenhados com PIL (`python -m ia.avaliacao.gerar_demo`), com a faixa "IMAGEM SIMULADA — DEMONSTRAÇÃO" e o nome do arquivo visíveis, para o vídeo e o teste de ponta a ponta do Full-Stack. EAN fictício com prefixo GS1 `200` (uso interno, nunca produto real) e dígito verificador correto. O desenho do rótulo foi escolhido para ficar legível; o leitor e o limite de 0,8 são os mesmos das fotos reais.

| Imagem | EAN | Produto / marca (catálogo) | Lote | Fab. | Val. | Confiança | Pendências | Esperado | Confere |
|---|---|---|---|---|---|---|---|---|---|
| `demo_vaidosa_153.png` | 2000000001531 | Ricota Fresca / Vaidosa | 153 | 2026-06-10 | 2026-08-01 | 0.99 | — | leitura completa, sem pendência → em_recall no motor (lote 153 está no alerta da Vaidosa) | sim |
| `demo_vaidosa_154.png` | 2000000001531 | Ricota Fresca / Vaidosa | 154 | 2026-06-10 | 2026-08-01 | 0.98 | — | leitura completa, sem pendência → sem_recall no motor (lote 154 não está no alerta) | sim |
| `demo_ilegivel.png` | 2000000001531 | Ricota Fresca / Vaidosa | — | 2026-06-10 | 2026-08-01 | 0.94 | lote | lote ilegível → pendência → verificacao_pendente | sim |

## Regras

- A foto é lida do disco só para o teste; `ler_embalagem` recebe bytes e não grava, não loga e não envia a imagem a serviço externo.
- Produto identificado = EAN lido (pyzbar, dígito verificador conferido). O catálogo EAN → produto usado aqui vem do próprio `gabarito_fotos.csv` (stub da base de produtos, que é de outro papel).
- Lote comparado sem espaços + maiúsculas; datas comparadas como data. Validade só de mês/ano fica fora do denominador de validade.
- O texto bruto do OCR não é salvo no relatório.
