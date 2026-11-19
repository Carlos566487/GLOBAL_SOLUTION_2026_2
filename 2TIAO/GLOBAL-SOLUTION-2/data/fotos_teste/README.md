# Fotos de teste do leitor da embalagem

- **Origem:** 12 fotos **próprias**, tiradas em **18/11/2026**. Nenhuma imagem da internet.
- **Privacidade:** sem metadados EXIF. A `foto04` foi recortada para remover uma pessoa ao fundo. As fotos mostram só embalagens.
- **Uso:** só para medir o leitor (`python -m ia.avaliacao.avaliar_ocr`). Fotos enviadas por cidadãos no app **não** são armazenadas.

## Gabarito (`gabarito_fotos.csv`)

Colunas: `arquivo, produto, marca, ean, lote, data_fabricacao, validade, legivel_sim_nao, observacao, fonte_url, licenca`.

- **Rotulado por inspeção visual ampliada** das regiões de lote e datas, e **revisado pelo integrante Engenheiro de IA**. Ambiguidades de caractere e o critério usado estão em `observacao` (ex.: `U`/`0` e `I`/`1` na `foto01`).
- **Produto e marca:** fotos com EAN → cadastro do Open Food Facts (fonte citada em `observacao`); fotos sem EAN → texto visível na foto; sem texto suficiente → `nao_identificado`.
- **Datas:** `AAAA-MM-DD`; validade só de mês/ano fica como `AAAA-MM`. `data_fabricacao` só quando a embalagem rotula a data como fabricação (`EMP` = empacotamento não conta).
- **`legivel_sim_nao`:** o lote está legível na foto? `nao` inclui fotos sem lote no quadro (só EAN) e o controle negativo.

### Convenção de lote

A mesma do `ler_embalagem` (detalhes em `docs/interface_ia.md`):

1. Marcador `L`, `L:` ou `L.` → lote = texto logo após o marcador, sem o marcador, na mesma linha, até a primeira hora (`HH:MM`), data ou o fim da linha. Espaços internos são preservados.
2. Sem marcador, com rótulo `Lote` ou `Validade/Lote` → lote = a linha de código inteira que não é data.

## Composição

| Grupo | Fotos |
|---|---|
| Lote legível | foto01, foto02, foto04, foto08, foto09, foto11, foto12 |
| Só EAN (lote fora do quadro) | foto03, foto05, foto06, foto07 |
| Controle negativo (lote ilegível) | foto10 |
| Validade só de mês/ano | foto04, foto08, foto11 |

## Limitações

- Amostra pequena (12 fotos, 7 com lote legível).
- Validade só de mês/ano em 3 fotos: o leitor não preenche o dia, então esse campo fica fora da conta de acerto.
- Reflexo sobre o lote (foto12) e pouca luz (foto06, foto08 a foto12).
- Texto girado 90° (foto01) e superfície curva (foto04, foto10).
