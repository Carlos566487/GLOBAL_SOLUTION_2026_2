# Recall de alimentos
## Nota de produto e matriz de riscos

**Global Solution 2026.2 · CitizenTech**  
**Responsável:** Tayná Esteves, Product Owner & Pesquisadora  
**Data:** 16/11/2026

## Etapa 1 · Nota de produto

### Problema e hipótese

Depois que um alerta de recolhimento é publicado, a equipe de qualidade precisa identificar rapidamente quais recebimentos estão dentro do escopo da medida. O texto oficial pode especificar lotes, uma terminação de lote, uma data de fabricação ou todos os lotes de um produto. Para o consumidor, a mesma informação precisa ser transformada em uma orientação compreensível a partir dos dados da embalagem.

O levantamento do projeto documentou **27 recolhimentos distintos** por motivos sanitários em publicações oficiais consultadas de **01/01/2025 a 16/11/2026**. Esse número corresponde aos casos encontrados na busca documentada. Destes, **20 alertas reais** compõem o gabarito manual, com **36 registros de produtos ou apresentações**. A base de recebimentos usada nos testes é simulada.

**Hipótese da POC.** Estruturar os alertas e cruzá-los com os recebimentos por regras determinísticas pode reduzir o tempo de triagem e preservar a capacidade de explicar cada sinalização. A hipótese será testada comparando o fluxo manual e o automatizado na mesma tarefa. A consulta do cidadão testa se a solução consegue devolver uma orientação clara e lidar com embalagens que deixam dúvidas.

### Públicos e resultados esperados

| Público | Necessidade | Resultado esperado |
|---|---|---|
| **Responsável pela qualidade da rede** | Identificar as lojas com recebimentos afetados e decidir com base em evidências. | O painel mostra o alerta, a loja, a regra aplicada e os valores comparados. Um match começa em `aguardando_aprovacao`. A confirmação ou rejeição humana fica registrada com responsável e horário. |
| **Consumidor** | Verificar se a embalagem corresponde a um alerta e entender o próximo passo. | A consulta usa os dados legíveis da embalagem. Em caso de correspondência, informa a fonte e apresenta a orientação aplicável. Se a identidade do produto ou o dado necessário à regra ficar incerto, retorna `verificacao_pendente`. |

**Relação com o ODS 3 — Saúde e Bem-Estar.** A contribuição esperada é facilitar a identificação de alimentos sujeitos a recolhimento e apoiar decisões que reduzam a exposição a riscos sanitários. A POC mede indicadores operacionais, como tempo de triagem, correção das sinalizações e encaminhamento de casos incompletos. O impacto sobre consumo, intoxicações ou desfechos de saúde exigiria dados de operação real. [Nações Unidas Brasil — ODS 3](https://brasil.un.org/pt-br/sdgs/03)

### Fluxo e critérios de aceite

A coleta registra o texto oficial, a URL, a data e o hash do conteúdo. O LLM estrutura os dados e o validador verifica o contrato. O motor aplica a regra aos recebimentos simulados ou aos dados extraídos da embalagem. A aprovação humana se aplica à decisão operacional da rede. O log vincula fonte, extração, match e decisão.

| Cenário | Critério de aceite e evidência |
|---|---|
| **Vaidosa · lista de lotes** | O lote `153` gera match com evidência e aguarda aprovação. O lote `154` fica fora desse alerta. Após a confirmação do `153`, o log registra a decisão, o responsável e o horário. Evidências: painel antes e depois da decisão e evento de auditoria. |
| **Sanibras · data de corte** | Para um suplemento abrangido, a fabricação em `2026-06-12` gera match e a fabricação em `2026-06-13` fica fora. A evidência mostra a data de fabricação comparada ao limite. |
| **Vaidosa · lote ilegível** | O recebimento fica em `verificacao_pendente` e a interface indica o dado a conferir. Na consulta por foto, confiança OCR abaixo de `0,8` ou ausência de um dado decisivo também gera pendência. Evidências: entrada incompleta e resposta observada. |

No app, `sem_recall` indica ausência de correspondência na base consultada para uma embalagem identificada com dados suficientes. A interface deve comunicar esse alcance de forma clara.

### Métricas para a avaliação

| Indicador | Como medir | Evidência ou responsável |
|---|---|---|
| **Acerto da extração por regra** | Dividir os alertas reservados com regra integralmente correta pelo total avaliado daquele tipo. Conferir também os campos de identificação do produto. Para `lista`, comparar o conjunto completo de lotes, preservando zeros à esquerda. Usar como entrada o mesmo texto oficial que sustenta o rótulo. | IA registra casos avaliados, acertos, denominadores e divergências. |
| **Erros de cruzamento** | Comparar o resultado esperado com o observado para cada par alerta–recebimento. Contar falsos positivos e falsos negativos nos casos com resposta definida. Acompanhar separadamente os casos esperados como pendentes. | Full-Stack e Tech Lead guardam a entrada, o resultado, a evidência do match e o log. |
| **Tempo de triagem** | Cronometrar os fluxos manual e automatizado com os mesmos alertas, recebimentos e início e fim definidos. Se a tarefa incluir aprovação, medir essa etapa em ambos. Relatar os tempos, a diferença e o tamanho da base testada. | Tech Lead registra duração, condições da medição e quantidade de casos. |
| **Leitura da embalagem** | Nas 10 a 15 fotos reais previstas, comparar os dados lidos com o que é legível na embalagem e verificar o encaminhamento de leituras inconclusivas. Registrar acertos, erros e pendências com denominador. | IA testa a leitura. Full-Stack verifica o retorno do app e a orientação exibida. |

## Etapa 2 · Riscos, vieses e proteção de dados

A prioridade abaixo foi proposta para organizar o aceite. **Crítica** indica risco de sinalizar incorretamente um produto ou expor dados pessoais. **Alta** indica risco relevante para a rastreabilidade, a decisão operacional ou a interpretação dos resultados. Os controles são previstos ou propostos, com verificação a executar durante a integração.

| Prioridade e risco | Controle previsto ou proposto | Como verificar |
|---|---|---|
| **Crítica · Fonte incorreta ou conflitante**. Comunicado, resolução e retificação podem divergir. Isso muda quais lotes entram no recolhimento. | Coletar de fontes oficiais, registrar URL, data e hash do texto e vincular o gabarito à versão efetivamente usada. Encaminhar divergências sem resolução para revisão. | Reproduzir a revisão do caso JMS. Confirmar qual texto originou o lote usado e rastrear o dado do painel até a fonte. |
| **Crítica · Extração inventa, omite ou altera um valor**. Um JSON bem formado ainda pode conter uma regra errada. | Validar estrutura e campos obrigatórios. Comparar o conteúdo com os rótulos manuais e exigir evidência para a revisão humana. Campos necessários ausentes geram `verificacao_pendente` e bloqueiam o cruzamento automático. | Testar lote omitido, lote extra e alerta com campo necessário ausente. Conferir a regra completa e o encaminhamento para revisão. |
| **Crítica · OCR ilegível ou identificação ambígua**. Uma leitura incorreta pode produzir uma resposta conclusiva para a embalagem errada. | Usar o limiar OCR de `0,8` previsto. Verificar também a identificação do produto e os dados exigidos pela regra. Solicitar nova foto ou revisão quando a informação decisiva estiver ausente. | Testar embalagem nítida, lote ilegível e imagem que mostra validade sem a data de fabricação exigida. Conferir a orientação exibida no app. |
| **Crítica · Erro no cruzamento do lote ou no limite da data**. O mesmo código pode aparecer em produtos diferentes. | Cruzar a identidade do produto e o critério do alerta. Tratar lote como texto e aplicar a data de fabricação para `data_corte`, incluindo o dia limite conforme a fonte. | Testar `153` e `154`, o mesmo código em outro produto, o próprio dia do corte e o dia seguinte. |
| **Crítica · Foto com dados pessoais**. A imagem pode incluir rosto, endereço ou outras informações alheias à consulta. | Orientar o enquadramento da embalagem e limitar o tratamento aos dados necessários. Processar a imagem para a consulta, conforme a finalidade prevista, e verificar que o sistema descarta a foto após o processamento. Evitar imagem e texto incidental de OCR em logs, arquivos temporários persistentes, backups e ferramentas de monitoramento. | Em teste controlado, use dados fictícios visíveis ao lado da embalagem. Inspecione armazenamento e logs após uma consulta bem-sucedida e após uma falha. Confira o aviso exibido antes do envio. |
| **Alta · Ação sem revisão ou sem trilha de auditoria**. Uma sinalização pode ser confundida com decisão final. | Exibir o status inicial e a evidência no painel. Fazer a confirmação ou rejeição mediante ação do responsável e gravar a decisão no log de auditoria append-only. | Confirmar e rejeitar matches em teste. Conferir vínculo entre alerta, recebimento, motivo da sinalização, responsável e horário. |
| **Alta · Viés e cobertura limitada da amostra**. Há concentração de regras em lista e a qualidade da foto pode variar por iluminação, embalagem e contraste. | Reservar alertas antes de montar o prompt. Manter as apresentações de um mesmo recolhimento juntas. Reportar amostra e erros por regra e registrar as condições das fotos. O sufixo tem teste sintético do motor e ficou sem amostra oficial na avaliação da extração. | Revisar a divisão dos alertas, os denominadores e a variedade das fotos. Identificar explicitamente o teste sintético no resultado. |
| **Alta · Interpretação excessiva de `sem_recall`**. A cobertura depende da base de alertas e dos dados lidos. | Mostrar que a resposta se refere à consulta realizada. Encaminhar a revisão se o processamento falhar ou se faltarem dados para comparar uma regra aplicável. | Testar ausência de correspondência com dados suficientes e repetir com falha de leitura. Verificar se os retornos e as mensagens são distintos. |

**Privacidade e LGPD.** O desenho aplica os princípios de finalidade e necessidade ao limitar a consulta à verificação da embalagem. O endpoint previsto recebe a foto para processamento transitório. A equipe deve verificar a prática antes de declarar que a imagem é descartada. O aviso ao usuário deve explicar a finalidade da consulta e orientar o enquadramento da foto. [LGPD — Lei nº 13.709/2018, art. 6º](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html)

### Referências do projeto

- **Arquitetura e papéis — Recall de alimentos**, pp. 1–4 para o fluxo e o contrato, pp. 5–7 para responsabilidades, métricas e cenários.
- **Levantamento_Recolhimentos_Anvisa_2025_2026.md** para o método e os 27 casos documentados.
- **Dataset_Recall_Anvisa.xlsx** e **Golden_Set_Recall.json** para as fontes, os rótulos e as pendências.
- **Cenarios_Implementacao_e_Testes.md** para as entradas e os resultados esperados da demo.

