# Recall de alimentos
## Cenários sugeridos para implementação e teste

Use o `Golden_Set_Recall.json` como gabarito dos alertas. Os recebimentos e os identificadores de loja abaixo são simulados. Em cada caso, mantenha produto, marca e fabricante coerentes com o alerta e altere apenas o campo indicado no controle.

### Cenário 1 · Vaidosa com lista de lotes

O alerta da Ricota Fresca Vaidosa abrange os lotes `148`, `153`, `166` e `167`.

| Entrada na base simulada | Resultado esperado |
|---|---|
| Loja A recebe Ricota Fresca Vaidosa, lote `153`. | O motor cria um match em `aguardando_aprovacao`. O painel exibe o código `153` e a evidência de que ele pertence à lista do alerta. |
| Loja B recebe o mesmo produto, lote `154`. | O motor não cria match para esse alerta. |

**Teste de ponta a ponta**  
No painel, confirme o match da Loja A. Confira se o status passa a `confirmado` e se a decisão aparece no log de auditoria, vinculada ao match.

### Cenário 2 · Sanibras com data de corte

A regra abrange os suplementos do fabricante produzidos até **12/06/2026**, inclusive. Use o mesmo suplemento nos dois recebimentos para testar o limite da regra.

| Entrada na base simulada | Resultado esperado |
|---|---|
| Loja A recebe um suplemento abrangido pela medida, fabricado em `2026-06-12`. | O motor cria um match em `aguardando_aprovacao`. A evidência mostra a data de fabricação e o limite do alerta. |
| Loja B recebe o mesmo suplemento, fabricado em `2026-06-13`. | O motor não cria match para esse alerta. |

**Teste de ponta a ponta**  
Compare as duas lojas no painel. Confira se a regra usa o campo de **data de fabricação**. A validade da embalagem não substitui esse dado.

### Cenário 3 · Vaidosa com lote ilegível

| Entrada na base simulada | Resultado esperado |
|---|---|
| Loja C recebe Ricota Fresca Vaidosa com o campo de lote ausente ou vazio. | O recebimento fica em `verificacao_pendente`, com a falta do lote identificada para revisão. |

**Teste de ponta a ponta**  
Confira se o registro aparece como pendente e se o motor deixa de gerar um match conclusivo. Se a equipe repetir o caso pelo app com uma foto cujo lote permaneça ilegível, a resposta esperada também é `verificacao_pendente`.

### Evidências para o PDF final

Para cada cenário, guarde a entrada usada, o resultado esperado, o resultado observado e um print do painel ou um trecho do retorno da API. No cenário 1, guarde também a evidência da decisão humana no log.
