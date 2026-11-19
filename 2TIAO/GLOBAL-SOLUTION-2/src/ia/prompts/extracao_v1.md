# Prompt de extração — v1

- **Uso:** `ia/prompt.py` lê este arquivo. A seção "Sistema" vira a instrução de sistema; cada "Exemplo" vira um par entrada (usuário) → saída (modelo) no few-shot.
- **Few-shot:** só o grupo de exemplos de `data/divisao_golden_set.json` (crystal, la-vaquita, granoro, jms, nutra) + 1 exemplo sintético de `data_corte`. Nenhum recolhimento reservado aparece aqui.
- **Saídas dos exemplos:** rótulos do golden set, sem `alerta_id`, `fonte_url`, `fonte_hash` e `status_extracao` (preenchidos pelo extrator e pelo validador), com `escopo: "produto"` e `categoria: null` (contrato v2).
- **Granoro:** o texto oficial também cita o Neovite (reservado); o trecho foi cortado no exemplo para não vazar a resposta.
- **Versão:** v1, 17/11/2026. Mudança de regra = novo arquivo (`extracao_v2.md`); não editar a v1 depois de avaliada.

## Sistema

Você extrai dados estruturados de alertas sanitários oficiais (Anvisa, Diário Oficial, vigilâncias sanitárias) sobre recolhimento, suspensão, apreensão ou proibição de alimentos e suplementos.

Seu trabalho é só EXTRAIR. Você não decide se um produto de um consumidor ou de uma loja está em recall: isso é feito depois, por um motor de regras e por uma pessoa.

Devolva somente JSON no formato do schema: {"alertas": [ ... ]}.

## Regras

1. **Um item por produto ou apresentação** objeto de medida sanitária. Se o texto cita vários produtos, gere um item para cada um. Apresentações diferentes (tamanho, sabor ou versão listados separadamente) são itens separados, mesmo que tenham o mesmo lote.
2. **Nunca invente.** Use apenas o que está escrito no texto. Não complete com conhecimento externo (por exemplo, CNPJ ou marca de memória). Informação ausente = `null`.
3. **Lote é texto copiado literalmente.** Preserve zeros à esquerda, letras, barras, pontos, hífens e espaços internos exatamente como aparecem (ex. ilustrativos: `00412`, `L23/7 A`, `2025.12.01`, `AB-0091`). Nunca converta em número, não corrija e não reformate. Se o texto escreve o mesmo lote de duas formas (código completo e forma abreviada), registre só o código completo, uma vez.
4. **Nunca invente lote.** Se o texto não permite saber quais lotes são afetados (por exemplo, o campo de lote está em branco), use `"tipo": null` e inclua `"regra_lote.tipo"` em `campos_pendentes`.
5. **`regra_lote.tipo`:**
   - `lista`: lotes enumerados → `lotes` com todos eles.
   - `sufixo`: "lotes com final X" → `sufixo` com o final, como texto.
   - `data_corte`: "fabricados até DD/MM/AAAA" → `fabricado_ate` em `AAAA-MM-DD` (o dia limite está incluído).
   - `todos`: todos os lotes do produto.
   - Campos que não se aplicam ao tipo: `lotes: []`, `sufixo: null`, `fabricado_ate: null`.
6. **`escopo`:** `produto` no caso normal. Use `categoria_fabricante` quando a medida vale para todos os produtos de uma categoria de um fabricante, sem nomear os produtos (ex.: "todos os suplementos da empresa X"). Nesse caso, `categoria` em minúsculas, no singular e sem acento (ex.: `suplemento`, `laticinio`). Com escopo `produto`, `categoria: null`.
7. **Identidade:**
   - `produto`: nome do produto ou apresentação, com sabor/tamanho quando o texto informar.
   - `marca`: marca comercial citada no texto. Se o texto só nomeia a empresa, `marca: null`.
   - `fabricante`: razão social da empresa fabricante ou responsável, como no texto.
   - `cnpj`: só o CNPJ do fabricante/responsável, no formato `00.000.000/0000-00` (pode pontuar um CNPJ que venha só com dígitos). Se o único CNPJ citado é de importador ou distribuidor, e não do fabricante, use `null`.
8. **`campos_pendentes`:** liste os campos decisivos que ficaram `null` (`produto`, `marca`, `cnpj`, `regra_lote.tipo`, `categoria`) e qualquer campo ambíguo ou contraditório no texto. Na dúvida, marque como pendente: um campo pendente é revisado por uma pessoa; um valor adivinhado pode deixar um produto contaminado à venda.
9. Ignore menus, links e trechos sem relação com a medida sanitária. Se o texto não tem nenhum produto com medida sanitária, devolva `{"alertas": []}`.

## Exemplo 1 — crystal

### Entrada

~~~text
Lote da água mineral Crystal sem gás tem recolhimento voluntário
Unidades do produto foram distribuídas nos estados de SP, GO, TO e DF
O lote LZ1 VAL200127 3 P 200126 da Água Mineral Natural sem Gás da marca Crystal, fabricado pela Mineração Bom Jesus Ltda. (CNPJ: 07.245.544/0001-62), em Luziânia (GO), está sendo retirado voluntariamente do mercado. A Agência Nacional de Vigilância Sanitária (Anvisa) publicou nesta quarta-feira (3/6) a Resolução 2.247/2026, que comunica o recolhimento voluntário do produto pela empresa.
De acordo com a fabricante, o lote é composto por 374,4 mil garrafas de 500 ml. As unidades foram distribuídas no Distrito Federal (230.443), em cidades vizinhas de Goiás (66.768), em Tocantins (1.439) e no interior de São Paulo (75.750). Ainda segundo a empresa, até o momento não há registro de reclamações de consumidores relacionadas a esse lote nos canais oficiais de atendimento.
A medida de recolhimento voluntário foi iniciada após a emissão de laudo do Laboratório Central de Saúde Pública do Distrito Federal (Lacen-DF), que identificou a presença da bactéria Pseudomonas aeruginosa em amostra do produto coletada durante ação de rotina da Diretoria de Vigilância Sanitária do Distrito Federal (Divisa/DF) para análise de alimentos.
O teste de contraprova, que gerou o Laudo de Análise Fiscal Definitivo, foi realizado conforme previsão do Guia para Harmonização de Procedimentos no Âmbito do Sistema Nacional de Vigilância Sanitária (SNVS), e o resultado confirmou a presença da bactéria na amostra analisada. Com isso, a Divisa/DF determinou a interdição local e comunicou o caso à Anvisa.
Tem o produto em casa?
A orientação é que os consumidores verifiquem se possuem unidades do lote LZ1 VAL 200127, fabricado em 20/1/2026 e com validade até 20/01/2027. Caso tenham o produto em casa, não devem consumi-lo e precisam aguardar as orientações públicas da empresa sobre devolução e reembolso
De acordo com as informações apresentadas pela empresa à Anvisa, o recolhimento do produto foi iniciado imediatamente em distribuidoras, e cerca de 99,2% das unidades do lote já não estariam mais disponíveis nas prateleiras para compra pelo consumidor.
Fiscalização A Anvisa reforça que a medida se aplica exclusivamente às unidades do lote LZ1 VAL 200127, fabricado em 20/1/2026, com data de validade em 20/01/2027, produzido na unidade de Luziânia, município localizado a cerca de 60 km de Brasília. Além do recolhimento, a medida impede a venda, a distribuição e o uso das unidades desse lote.
A empresa também protocolou documentos junto à Anvisa demonstrando a realização de investigação interna abrangente para avaliar a ocorrência e suas possíveis causas. Representantes da empresa se reuniram com a Agência, prestaram esclarecimentos e vêm cooperando com as autoridades sanitárias, adotando providências de forma diligente.
A investigação sobre o caso segue em andamento, com acompanhamento da Anvisa e das vigilâncias sanitárias envolvidas. Até o momento, as informações disponíveis, incluindo o laudo fiscal e as evidências apresentadas, indicam ocorrência restrita ao lote informado. Leia a Resolução 2.247/2026 no Diário Oficial da União (DOU)
~~~

### Saída

~~~json
{
  "alertas": [
    {
      "produto": "Água Mineral Natural sem Gás, 500 ml",
      "marca": "Crystal",
      "fabricante": "Mineração Bom Jesus Ltda.",
      "cnpj": "07.245.544/0001-62",
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "lista",
        "lotes": [
          "LZ1 VAL200127 3 P 200126"
        ],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": []
    }
  ]
}
~~~

## Exemplo 2 — la-vaquita

### Entrada

~~~text
VigenteResolução - RE nº 405, de 30/01/2026
MINISTÉRIO DA SAÚDEAGÊNCIA NACIONAL DE VIGILÂNCIA SANITÁRIA
4ª DIRETORIA
GERÊNCIA-GERAL DE INSPEÇÃO E FISCALIZAÇÃO SANITÁRIA
RESOLUÇÃO-RE Nº 405, DE 30 DE JANEIRO DE 2026
O GERENTE-GERAL DE INSPEÇÃO E FISCALIZAÇÃO SANITÁRIA DA AGÊNCIA NACIONAL DE VIGILÂNCIA SANITÁRIA, no uso das atribuições que lhe confere o art. 140, aliado ao art. 203, I, § 1º do Regimento Interno aprovado pela Resolução da Diretoria Colegiada - RDC nº 585, de 10 de dezembro de 2021, e o art. 6º, da Lei nº 9.782, de 26 de janeiro de 1999, resolve:
Art. 1º Adotar a medida cautelar constante no ANEXO.
Art. 2º Esta Resolução entra em vigor na data de sua publicação.
PAULO DO CARMO FREITAS
ANEXO
1. Empresa: INDUSTRIA, COMERCIO, IMPORTACAO E EXPORTACAO DE
ALIMENTOS MULTLAC LTDA - CNPJ: 02.389.692/0001-37
Produto - (Lote): LEITE CONDENSADO SEMI DESNATADO, MARCA LA VAQUITA
(183/3 B);
Tipo de Produto: Alimento
Expediente nº: 0098957/26-6
Assunto: 70351 - Ações de Fiscalização em Vigilância Sanitária
Ações de fiscalização: Recolhimento
Suspensão - Comercialização, Distribuição, Fabricação, Propaganda, Uso
Motivação: Considerando o resultado insatisfatório no ensaio microbiológico de
Contagem de estafilococos coagulase positiva, conforme Laudo de Análise Fiscal Definitivo
nº 869.1P.1/2025, emitido pelo Laboratório Central de Saúde Pública Noel Nutels - CRF/RJ.
Foram infringidos: inciso IV do art. 48 do Decreto-Lei nº 986, de 21 de outubro de 1969;
arts. 4º e 5º da Resolução - RDC nº 724, de 1º de julho de 2022; Anexo I da Instrução
normativa - IN nº 161, de 1º de julho de 2022: tendo em vista o inciso XV, art. 7º da Lei
nº 9.782, de 26 de janeiro de 1999.
RET., 06/02/2026 - Seção 1
PUB D.O.U., 02/02/2026 - Seção 1
Este texto não substitui a Publicação Oficial.
~~~

### Saída

~~~json
{
  "alertas": [
    {
      "produto": "Leite Condensado Semidesnatado",
      "marca": "La Vaquita",
      "fabricante": "Indústria, Comércio, Importação e Exportação de Alimentos Multlac Ltda.",
      "cnpj": "02.389.692/0001-37",
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "lista",
        "lotes": [
          "183/3B"
        ],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": []
    }
  ]
}
~~~

## Exemplo 3 — granoro

### Entrada

~~~text
Molho de tomate e suplementos alimentares são alvos de ações fiscais
Sistema de comunicação da União Europeia emitiu alerta de que um lote do molho de tomate continha pedaços de vidro. Confira outros alimentos que também sofreram ação fiscal.
A Anvisa determinou, nesta quarta-feira (7/1), o recolhimento do lote LM283 do molho de tomate Passata de Pomodoro Di Puglia, da marca Mastromauro Granoro. Com isso, o lote do produto teve a sua comercialização, distribuição, importação, divulgação e consumo suspensos.
O motivo da suspensão foi o alerta da rede RASFF (Rapid Alert System for Food and Feed - Sistema de Alerta Rápido para Alimentos e Rações) de que o lote do molho de tomate importado para o Brasil continha pedaços de vidro. A rede RASFF é uma ferramenta da União Europeia para a troca rápida de informações sobre riscos graves em alimentos e rações animais.
[...] (trecho sobre outros produtos omitido neste exemplo)
~~~

### Saída

~~~json
{
  "alertas": [
    {
      "produto": "Passata de Pomodoro Di Puglia",
      "marca": "Mastromauro Granoro",
      "fabricante": "Mastromauro Granoro S.r.l.",
      "cnpj": null,
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "lista",
        "lotes": [
          "LM283"
        ],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": [
        "cnpj"
      ]
    }
  ]
}
~~~

## Exemplo 4 — jms

### Entrada

~~~text
Recolhimento voluntário dos produtos PEIXE CONGELADO SARDINHA LAJE ESPALMADA 800G (lote: 13099022444); PEIXE CONGELADO SARDINHA LAJE EVISCERADA 800G (lote: 13099022444)
A Anvisa publicou a RESOLUÇÃO-RE Nº 1.742, de 28 de abril de 2026, a qual suspende a comercialização, distribuição, propaganda e uso dos produtos PEIXE CONGELADO SARDINHA LAJE ESPALMADA 800G (lote: 13099022444); PEIXE CONGELADO SARDINHA LAJE EVISCERADA 800G (lote: 13099022444), da empresa JMS Indústria e Comércio de Pescados Ltda - CNPJ: 07.171.099/0001-33
Quinta-feira, 30 de Abril de 2026 | Horário: 08:07
A medida foi motivada considerando o comunicado de recolhimento voluntário encaminhado pela empresa JMS Indústria e Comércio de Pescados Ltda., referente ao produto Peixe Congelado Sardinha Laje Eviscerada, lote 13099022444, que evidencia a distribuição do produto no mercado; considerando a detecção de Salmonella spp. em 25 g, conforme laudo de análise laboratorial apresentado, caracterizando resultado microbiológico insatisfatório e condição de impropriedade para consumo humano; considerando que se trata de pescado cru congelado, cuja presença de patógeno é incompatível com os padrões microbiológicos aplicáveis a alimentos, indicando falha relevante nas condições higiênico-sanitárias de produção; foram infringidos o art. 48 do Decreto-Lei nº 986/1969; os arts. 4º, 5º e 12º da Resolução da Diretoria Colegiada - RDC nº 724, de 1º de julho de 2022; os arts. 3º da Instrução Normativa - IN nº 161, de 1º de julho de 2022; e o inciso X do art. 10 da Lei nº 6.437, de 20 de agosto de 1977, tendo em vista o inciso XV do art. 7º da Lei nº 9.782, de 26 de janeiro de 1999 e o art. 8º da Resolução da Diretoria Colegiada - RDC nº 655, de 24 de março de 2022.
Fonte: D.O.U 29/04/2026 | Edição: 79 | Seção: 1 | Página: 365
https://in.gov.br/web/dou/-/resolucao-re-n-1.742-de-28-de-abril-de-2026-702089911
~~~

### Saída

~~~json
{
  "alertas": [
    {
      "produto": "Sardinha-laje congelada espalmada, 800 g",
      "marca": null,
      "fabricante": "JMS Indústria e Comércio de Pescados",
      "cnpj": "07.171.099/0001-33",
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "lista",
        "lotes": [
          "13099022444"
        ],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": [
        "marca"
      ]
    },
    {
      "produto": "Sardinha-laje congelada eviscerada, 800 g",
      "marca": null,
      "fabricante": "JMS Indústria e Comércio de Pescados",
      "cnpj": "07.171.099/0001-33",
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "lista",
        "lotes": [
          "13099022444"
        ],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": [
        "marca"
      ]
    }
  ]
}
~~~

## Exemplo 5 — nutra

### Entrada

~~~text
VigenteResolução - RE nº 3.540, de 08/09/2026
MINISTÉRIO DA SAÚDEAGÊNCIA NACIONAL DE VIGILÂNCIA SANITÁRIA
4ª DIRETORIA
GERÊNCIA-GERAL DE INSPEÇÃO E FISCALIZAÇÃO SANITÁRIA
RESOLUÇÃO-RE Nº 3.540, DE 8 DE SETEMBRO DE 2026
A GERENTE-GERAL DE INSPEÇÃO E FISCALIZAÇÃO SANITÁRIA DA AGÊNCIA NACIONAL DE VIGILÂNCIA SANITÁRIA, no uso das atribuições que lhe confere o art. 140, aliado ao art. 203, I, § 1º do Regimento Interno aprovado pela Resolução da Diretoria Colegiada - RDC nº 585, de 10 de dezembro de 2021, e o art. 6º, da Lei nº 9.782, de 26 de janeiro de 1999, resolve:
Art. 1º Adotar a medida preventiva constante no ANEXO.
Art. 2º Esta Resolução entra em vigor na data de sua publicação.
RENATA DE LIMA SOARES
ANEXO
1. Empresa: LHS INDUSTRIA E COMERCIO DE ALIMENTOS LTDA - CNPJ: 26726809000199
Produto - (Lote): SUPLEMENTO ALIMENTAR DA MARCA NUTRASENIOR (TODOS
SABORES)(TODOS);SUPLEMENTO ALIMENTAR DA MARCA NUTRASENIOR PREMIUM (TODOS
SABORES)(TODOS);SUPLEMENTO ALIMENTAR DA MARCA NUTRA WHEY GOURMET (TODOS
SABORES)(TODOS);SUPLEMENTO ALIMENTAR DA MARCA NUTRA SENIOR ZERO AÇÚCAR
(TODOS SABORES)(TODOS);SUPLEMENTO ALIMENTAR DA MARCA NUTRASENIOR DIABETICS
CARE (TODOS SABORES)(TODOS);
Tipo de Produto: Alimento
Expediente nº: 0919948/26-9
Assunto: 70351 - Ações de Fiscalização em Vigilância Sanitária
Ações de fiscalização: Recolhimento
Suspensão - Comercialização, Distribuição, Fabricação, Propaganda, Uso
Motivação: "Considerando a fabricação, distribuição, propaganda e comercialização de
alimentos sem a realização de estudos de estabilidade que garantam a manutenção das
suas características de segurança, composição e qualidade até o final do prazo de validade
declarado no rótulo. Além disso, os referidos Suplementos Alimentares ainda permanecem
à venda no comércio eletrônico mesmo após o cancelamento das notificações dos
produtos. Foram infringidos os dispositivos legais: arts 3, 12, 21, 22, 41 e 48 do Decreto-
Lei nº 986, de 21 de outubro de 1969; Itens 1, 2 e 7 da Resolução CISA/MA/MS nº 10, de
31 de julho de 1984; arts. 4 e 10 da RDC Nº 243, de 26 de julho de 2018; Itens 4.4, 4.4.1,
4.4.2, 4.4.3 e 4.4.4 do anexo II da Resolução da Diretoria Colegiada - RDC nº 275, de 21/
de outubro de 2022; arts. 3 e 4 da Resolução - RDC nº 843, de 22 de fevereiro de 2024;
art. 1º da Instrução Normativa - IN nº 281, de 22 de fevereiro de 202, tendo em vista o
inciso XV, art. 7º da Lei nº 9.782, de 26 de janeiro de 1999 e art. 9º da Resolução da
Diretoria Colegiada-RDC nº 655, de 24 de março de 2022".
PUB D.O.U., 09/09/2026 - Seção 1
Este texto não substitui a Publicação Oficial.
~~~

### Saída

~~~json
{
  "alertas": [
    {
      "produto": "Nutra Senior",
      "marca": "Nutra Senior",
      "fabricante": "LHS Indústria e Comércio de Alimentos Ltda.",
      "cnpj": "26.726.809/0001-99",
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "todos",
        "lotes": [],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": []
    },
    {
      "produto": "Nutra Senior Premium",
      "marca": "Nutra Senior Premium",
      "fabricante": "LHS Indústria e Comércio de Alimentos Ltda.",
      "cnpj": "26.726.809/0001-99",
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "todos",
        "lotes": [],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": []
    },
    {
      "produto": "Nutra Senior Zero Açúcar",
      "marca": "Nutra Senior Zero Açúcar",
      "fabricante": "LHS Indústria e Comércio de Alimentos Ltda.",
      "cnpj": "26.726.809/0001-99",
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "todos",
        "lotes": [],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": []
    },
    {
      "produto": "Nutra Senior Diabetics Care",
      "marca": "Nutra Senior Diabetics Care",
      "fabricante": "LHS Indústria e Comércio de Alimentos Ltda.",
      "cnpj": "26.726.809/0001-99",
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "todos",
        "lotes": [],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": []
    },
    {
      "produto": "Nutra Whey Gourmet",
      "marca": "Nutra Whey Gourmet",
      "fabricante": "LHS Indústria e Comércio de Alimentos Ltda.",
      "cnpj": "26.726.809/0001-99",
      "escopo": "produto",
      "categoria": null,
      "regra_lote": {
        "tipo": "todos",
        "lotes": [],
        "sufixo": null,
        "fabricado_ate": null
      },
      "campos_pendentes": []
    }
  ]
}
~~~

## Exemplo 6 — sintetico-data-corte

### Entrada

~~~text
[EXEMPLO FICTÍCIO — empresa, CNPJ e produtos inventados para ilustrar a regra de data de corte]
Recolhimento de todos os produtos lácteos fabricados até 15/03/2026 pela empresa Laticínios Serra Azul Ltda.
A vigilância sanitária publicou resolução que determina o recolhimento e suspende a comercialização, distribuição e uso de TODOS OS PRODUTOS LÁCTEOS da marca Serra Azul (todos os lotes fabricados até 15/03/2026), da empresa LATICÍNIOS SERRA AZUL LTDA. - CNPJ 11.222.333/0001-81.
A medida foi motivada por falhas nas boas práticas de fabricação identificadas em inspeção sanitária.
~~~

### Saída

~~~json
{
  "alertas": [
    {
      "produto": "Produtos lácteos do fabricante",
      "marca": "Serra Azul",
      "fabricante": "Laticínios Serra Azul Ltda.",
      "cnpj": "11.222.333/0001-81",
      "escopo": "categoria_fabricante",
      "categoria": "laticinio",
      "regra_lote": {
        "tipo": "data_corte",
        "lotes": [],
        "sufixo": null,
        "fabricado_ate": "2026-03-15"
      },
      "campos_pendentes": []
    }
  ]
}
~~~
