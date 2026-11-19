# IA — limites, riscos e governança

Escopo: extrator de alertas (LLM), validador (Pydantic) e leitor da embalagem (OCR). Resultados medidos em `docs/resultados_extracao.md` e `docs/resultados_ocr.md`.

## 1. Princípios

- **O LLM só extrai.** Ele transforma o texto oficial em JSON (formato 1). Quem decide se uma loja ou um produto está em recall é o motor de regras determinístico, e a ação passa por aprovação humana.
- **Temperatura 0** em todas as chamadas, para reduzir variação entre execuções.
- **Fonte citada em cada extração:** todo alerta carrega `fonte_url` (só `*.gov.br` e `*.datalegis.net`; outras fontes são recusadas) e `fonte_hash` do texto bruto, quando o coletor o fornece. O modelo, a versão, o prompt e as tentativas ficam em `extrair_alertas_detalhado`, para o log de auditoria.
- **Na dúvida, pendente.** Campo decisivo nulo, regra incompleta, resposta ilegível, serviço fora do ar ou orçamento de tempo estourado viram `verificacao_pendente` com o motivo. Nenhuma falha vira "sem recall".
- **Validação dupla:** o schema JSON (gerado do Pydantic) restringe a saída do modelo, e o `AlertaExtraido` valida de novo e recalcula `campos_pendentes`. O LLM não consegue retirar uma pendência.

## 2. Escolha do LLM: Google Gemini, SDK `google-genai`

- **Saída validada direto no schema:** `response_mime_type="application/json"` com `response_json_schema` gerado do modelo Pydantic do formato 1.
- **Nulos explícitos reduzem valores inventados:** todos os campos são obrigatórios e anuláveis no schema; o modelo tem uma saída válida para "não está no texto", em vez de ser empurrado a preencher.
- **Custo baixo** da família Flash, adequado a uma POC com avaliação repetida.

### Modelo: `gemini-3.5-flash-lite` (decisão de 17/11/2026)

| Uso | Modelo | Fallback |
|---|---|---|
| Operação (pipeline e demo) | `gemini-3.5-flash-lite` | `gemini-3.7-flash`, depois `gemini-3.8-flash` |
| Avaliação | `gemini-3.5-flash-lite` (`EVAL_MODEL`) | desligado |

- **Disponibilidade observada em 17/11/2026:** `gemini-3.8-flash` e `gemini-3.7-flash` responderam 503 ou 504 em **todas** as chamadas de teste do dia; `gemini-3.5-flash-lite` respondeu **100%** das chamadas, em cerca de 2 s.
- **Coerência:** o modelo avaliado é o mesmo da demonstração.
- **Custo:** o Flash-Lite é a opção mais barata da família.
- **Retentativa:** 429/500/503 → esperas de 2, 4 e 8 s no mesmo modelo; 504 ou timeout (30 s) → próximo modelo, sem nova tentativa; teto de 90 s por extração.
- **Comparação opcional:** se o `gemini-3.8-flash` voltar a responder até 19/11, a avaliação será repetida com `EVAL_MODEL=gemini-3.8-flash` e reportada à parte.

## 3. Privacidade e LGPD

- **Foto do cidadão:** processada só em memória, localmente (OpenCV + EasyOCR + pyzbar). Não é salva, não é logada e **não é enviada ao Gemini** nem a outro serviço. O texto bruto do OCR também não é logado nem devolvido. Há teste automatizado que falha se a leitura gravar arquivo.
- **Texto enviado ao LLM:** só textos oficiais públicos. Antes do envio, CPF, e-mail e telefone formatados são mascarados (`[CPF]`, `[EMAIL]`, `[TELEFONE]`). A máscara é conservadora para não alterar lotes nem CNPJs (ex.: o lote `13099022444` tem 11 dígitos, como um CPF sem pontuação, e não é mascarado).
- **Chave da API:** só no `.env` (fora do git); `.env.example` sem valores secretos.

## 4. Riscos

| Risco | Severidade | Mitigação | Evidência |
|---|---|---|---|
| **Alucinação** (alerta, lote ou campo inventado) | Crítica | Prompt "nunca invente"; schema com nulos; validador; alerta sem registro no gabarito vai para `revisao_manual` com o trecho do texto que o sustenta | 0 possíveis alucinações entre os 11 alertas não rotulados |
| **Falso "sem recall" pela regra** | Crítica | Regra incompleta ou tipo nulo → pendente | Regra correta em 25/26 registros; o único erro (Equaliv) ficou pendente |
| **Marca errada com status `ok` → falso "sem recall" no motor** | Crítica | Recomendação ao motor: identidade pelo CNPJ quando houver; divergência só de marca → revisão humana (ver abaixo) | Caso Neovite: marca "Bausch Lomb", CNPJ correto, status `ok` |
| **Lote lido errado na foto com confiança alta** | Crítica | Limite de 0,8; pendência por campo; EAN com dígito verificador | 12 fotos próprias: **0 erros confiantes** nas duas versões do leitor; nenhum lote lido errado (`resultados_ocr.md`) |
| **Fonte não oficial** | Alta | Whitelist de domínios no validador e no extrator | Testes com domínios falsos (ex.: `gov.br.exemplo.com`) |
| **Serviço do LLM indisponível** | Média | Retentativa, fallback, orçamento de 90 s, alerta pendente com motivo | 17/11: Flash 3.7/3.8 indisponíveis; troca para o Flash-Lite |

### Marca divergente no motor (caso Neovite)

Existem alertas com `status_extracao = "ok"` e marca divergente. No Neovite, o extrator devolveu marca "Bausch Lomb" (nome da empresa) em vez de "Neovite", com o CNPJ correto. Se o motor exigir que a marca bata, a loja que recebeu o Neovite **não é sinalizada**: um falso "sem recall" no nível do motor, sem nenhum erro de regra. Recomendação registrada para o Full-Stack em `docs/dependencias_ia.md`: com CNPJ no alerta, a identidade do fabricante é decidida pelo CNPJ (só dígitos); marca é critério secundário; divergência só de marca, com CNPJ igual, vai para revisão humana.

## 5. Vieses e cobertura

- **Amostra concentrada em `lista`:** 16 dos 20 recolhimentos do gabarito; na avaliação, 12 dos 15 reservados. `todos`, `data_corte` e tipo nulo têm 1 caso cada, e a acurácia nesses tipos não é generalizável.
- **`sufixo` só sintético:** não há caso real; a regra é coberta por teste unitário, fora da acurácia.
- **Peso da Nestlé:** 9 dos 26 registros reservados vêm de um único texto (e transcrito); por isso a avaliação é reportada com e sem a Nestlé.
- **Gabarito com dados de outra fonte:** parte dos valores do gabarito (CNPJ, fabricante, a regra `todos` da Equaliv) veio da RE e não está no texto de entrada; 25 dos 39 campos com erro são desse tipo. A avaliação mostra a métrica "contra o gabarito" e "sobre o recuperável".
- **Fotos:** a leitura varia com iluminação, contraste, curvatura da embalagem e impressão a jato de tinta do lote; as condições das fotos ficam registradas em `gabarito_fotos.csv`.

## 6. Limitações

- **Nestlé (NT Conjunta 17/2026):** a entrada do extrator foi **transcrita manualmente** das tabelas em imagem do PDF (páginas 1–2), porque o texto do PDF não contém os lotes. O **gabarito já tinha sido visto** (parcialmente) antes da transcrição, durante a inspeção dos dados. A transcrição foi feita só pelas imagens e não foi ajustada depois da comparação; o caso é reportado à parte, como "entrada transcrita".
- **Marca (prompt v1):** limitação conhecida. Foram 14 erros reais (a marca estava no texto): marca omitida (D'Viez ×4, Sanibras), empresa no lugar da marca (Neovite → "Bausch Lomb"), marca truncada (Bentô Gelatos → "Gelatos") e linha de produto reduzida à marca-mãe (Nestlé: "NAN Supreme Pro" → "NAN"). Marca nula vira pendente; marca errada **não** vira pendente.
- **Convenção de lote alinhada depois de ver as fotos:** a regra de delimitação do lote no leitor foi alinhada à convenção do gabarito **depois da inspeção das fotos de teste** (commit `07fcf16`; os testes novos usam os padrões das fotos). É convenção de delimitação (onde o lote começa e termina no texto lido), não ajuste de modelo: EasyOCR, pré-processamento, limite de confiança e pyzbar não mudaram. Por isso `resultados_ocr.md` reporta as duas versões: a **regra original é a medição sem contaminação** (lote correto em 3/7 fotos legíveis) e a regra alinhada dá 4/7; erro confiante 0/12 nas duas.
- **Rotação não corrigida:** continua sem correção, de propósito (limitação declarada antes das fotos; não ajustada depois de vê-las). A foto01, girada 90°, não tem o lote lido.
- **Resultado do leitor nas fotos (12 fotos próprias):** EAN lido em 6/6; nenhum "acerto" conclusivo, porque toda foto com lote legível ficou pendente: 5 das 7 não têm EAN no quadro (produto não identificado, por desenho) e as demais ficaram abaixo da confiança 0,8. O leitor é seguro (nunca respondeu de forma conclusiva e errada), mas pouco útil sem o EAN e com fotos escuras.
- **Prompt não ajustado após a avaliação:** o prompt v1 foi congelado antes da avaliação e não foi alterado depois de ver os resultados dos 15 recolhimentos reservados, para não contaminar o teste.
- **Extrator:** depende do texto que recebe; dado que só está na RE (CNPJ, escopo) não é recuperado de uma notícia que não o traz.
- **Leitor da embalagem:**
  - lote segue a convenção do `docs/interface_ia.md` (marcador `L`, até hora/data/fim da linha). Lote no formato de data (ex.: `21/08/2026`) é cortado; texto que vem depois do lote na mesma linha, sem hora/data, entra no lote (ex.: `029 SF`);
  - sem correção de rotação/perspectiva;
  - validade só com mês/ano (`VAL 08/2026`) não é lida (não se inventa o dia);
  - o OCR não corrige caracteres parecidos (`0`/`O`, `1`/`I`, `5`/`S`);
  - produto e marca vêm de um catálogo EAN → produto (base de outro papel); sem EAN legível, a foto fica pendente;
  - o EasyOCR baixa cerca de 100 MB de pesos na primeira execução.

## 7. Próximos passos

- **Prompt v2** (`extracao_v2.md`), com foco em marca, avaliado nos **7 recolhimentos levantados pela PO que estão fora do gabarito**, se ela os rotular: um conjunto que nem o v1 nem o v2 viram.
- Marcar no gabarito os valores que vêm de outra fonte (RE), ou incluir o texto da RE na entrada.
- **Leitor da embalagem:**
  - **correção de rotação** (testar 0°/90°/180°/270° e ficar com a leitura de maior confiança); a foto01, girada 90°, não teve o lote lido;
  - **identificação do produto por texto** (produto + marca lidos no rótulo e conferidos com a base) quando não houver EAN legível: 5 das 7 fotos com lote legível ficaram pendentes só por falta de EAN;
  - **calibração do limite de confiança** com um conjunto **novo** de fotos. O limite de 0,8 foi mantido porque foi definido antes do teste; recalibrá-lo nas mesmas 12 fotos contaminaria a medição.
