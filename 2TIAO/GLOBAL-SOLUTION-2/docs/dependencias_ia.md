# Dependências do papel Engenheiro de IA

O que a parte de IA usa de outros papéis e como fica até a integração (a partir de 18/11).

| Dependência | Dono | Situação | Enquanto isso |
|---|---|---|---|
| `fonte_hash` dos alertas | Tech Lead (coletor) | Pendente | Golden set com `fonte_hash: null`; o validador aceita `null` |
| Textos oficiais em `data/alertas_brutos/` | Tech Lead (coletor) | Pendente | A avaliação lê `data/textos_avaliacao/` (baixados por `src/ia/avaliacao/baixar_textos.py`, sem hash oficial). **Quando o coletor existir, a avaliação passa a ler `data/alertas_brutos/`.** |
| PDF com tabela em imagem (Nestlé, NT 17/2026) | Tech Lead (coletor) | Achado | Para a avaliação, as tabelas foram **transcritas à mão** (ver abaixo). Em produção, o coletor precisará de OCR para PDFs escaneados ou de outra fonte textual; sem isso o extrator não vê os lotes |
| Lote `183/3B` × `183/3 B` (La Vaquita) | PO / Full-Stack | Decidido na avaliação | Ver "Comparação de lotes" abaixo |
| `escopo`/`categoria` no registro `sanibras` do gabarito | PO | Pendente | Os dois campos ficam fora da acurácia da extração |
| URL do caso `agua-da-serra` (`anttlegis` × `anvisalegis`) | Tech Lead | Pendente | URL atual passa na whitelist (`*.datalegis.net`); revisar o texto quando confirmada |
| Aprovação do contrato v2 | Grupo | Pendente | Código segue a v2 |
| Uso de `LeituraEmbalagem.pendencias(tipo_regra)` | Full-Stack (motor / `POST /cidadao/verificar`) | A integrar | Documentado em `docs/interface_ia.md` (tarefa 7) |

## Decisões do validador que os outros papéis precisam conhecer

- `campos_pendentes` e `status_extracao` são **recalculados** pelo validador; o que o LLM disser é mantido, mas não pode retirar uma pendência.
- Campos decisivos de identidade: `produto`, `marca`, `cnpj` (critério do golden set). `fabricante` nulo não bloqueia.
- CNPJ fora do formato `00.000.000/0000-00` vira pendência `cnpj`.
- Fonte fora de `*.gov.br` / `*.datalegis.net` é **rejeitada** (erro de validação), não vira pendente.
- Nomes de pendência: `produto`, `marca`, `cnpj`, `categoria`, `regra_lote.tipo`, `regra_lote.lotes`, `regra_lote.sufixo`, `regra_lote.fabricado_ate`, `revisao_manual`.
- Pendências de falha do extrator, no formato `extracao:<motivo>`: `json_invalido`, `item_invalido`, `nenhum_alerta_extraido`, `texto_vazio`, `fonte_hash_invalido`, `orcamento_esgotado`, `modelos_esgotados`, `erro_llm:<Tipo>`, `erro_interno`. O alerta vem com `regra_lote.tipo = null` e nunca chega ao motor.

## Extrator (`ia.extrator`)

- `extrair_alertas(texto, fonte_url, fonte_hash)` **nunca levanta exceção**. Fonte não oficial → lista vazia. Qualquer falha → um alerta pendente com `extracao:<motivo>`.
- `alerta_id` é gerado pelo extrator: `<marca ou fabricante>-<produto>-<6 hex do sha256 da URL>`, determinístico e único dentro da chamada.
- O modelo que respondeu, as tentativas e o motivo de falha estão em `extrair_alertas_detalhado(...)`, que devolve `ResultadoExtracao`. Esses dados ficam fora do formato 1 (o contrato não tem campo para eles).
- Antes do envio ao LLM, o texto passa por máscara de CPF, e-mail e telefone formatados. Lotes e CNPJs não são alterados.

## Nestlé: transcrição manual × gabarito

A Nota Técnica Conjunta 17/2026 traz as 9 tabelas de apresentações e lotes como **imagem** (páginas 1–2). Para a avaliação, elas foram transcritas à mão em `data/textos_avaliacao/nestle-formulas.txt`, num bloco marcado "TRANSCRIÇÃO MANUAL DE TABELA EM IMAGEM". A transcrição foi feita só a partir das imagens e **não foi ajustada** depois da comparação.

Comparação feita em passo separado (17/11/2026):

| Item | Transcrição | Gabarito | Resultado |
|---|---|---|---|
| Apresentações | 9 | 9 | iguais |
| Lotes únicos | 31 | 31 | iguais, nenhum lote só de um lado |
| Lotes por apresentação | — | — | os 9 conjuntos iguais |
| Nome do produto | grafia da imagem (`NAN SUPREME PRO 0-6 Meses 400g`) | grafia editada pela PO (`NAN Supreme Pro, 0–6 meses, 400 g`) | diverge só em caixa, travessão (`-` × `–`), `1 A 3 Anos` × `1–3 anos` e espaço antes da unidade |

Duas observações:
- A tabela repete lotes entre apresentações: `5321046041` em NAN Supreme Pro 400 g e 800 g; `5338046041` em NANLAC Supreme Pro e NANLAC Comfor 800 g. São 33 linhas para 31 lotes únicos, o que confirma a regra "identidade antes do lote".
- A grafia do produto no gabarito não é literal ao texto. Na avaliação (tarefa 5), o campo `produto` precisará de comparação normalizada; a regra será documentada em `resultados_extracao.md`.

A Nestlé será reportada também **separadamente**, sinalizada como "entrada transcrita".

## Comparação de lotes (La Vaquita) — nota para o Full-Stack

- A extração é **fiel ao texto**: o texto da RE 405/2026 traz `183/3 B`, e o extrator deve devolver `183/3 B`.
- **Na avaliação**, os lotes são comparados com uma chave normalizada: **remover todos os espaços em branco + `upper()`**. Assim `183/3 B` e `183/3B` contam como iguais.
- **Para o motor (decisão do Full-Stack, não da IA):** com a normalização atual do contrato (`strip` + `upper`), um lote lido da embalagem como `183/3B` **não casa** com o alerta `183/3 B`. Recomendamos que o motor use a mesma chave (sem nenhum espaço). Até lá, o risco é um falso "sem recall".

## Leitor da embalagem (`ia.embalagem`)

- `ler_embalagem(imagem: bytes, *, catalogo=None) -> LeituraEmbalagem` **nunca levanta exceção**: imagem inválida ou falha do OCR → leitura vazia com `confianca_ocr = 0.0` (leva a pendente).
- **Catálogo EAN → (produto, marca):** depende da base de produtos/recebimentos (Tech Lead) e do endpoint `POST /cidadao/verificar` (Full-Stack). Sem catálogo, `produto` e `marca` ficam nulos e a identificação depende só do EAN (`LeituraEmbalagem.produto_identificado`). No teste com fotos, o catálogo é montado a partir do `gabarito_fotos.csv` (stub).
- **Decisão de pendência fica com o motor:** `leitura.pendencias(tipo_regra)` devolve os motivos (`confianca_ocr`, `produto`, `lote`, `data_fabricacao`) para o tipo de regra do alerta candidato.
- **`confianca_ocr`:** a menor confiança entre as linhas de onde saíram lote e datas; nenhum desses campos lido → 0.0.
- **Privacidade:** a imagem existe só em memória durante a chamada; o texto bruto do OCR não é logado nem devolvido.

## Aviso ao Full-Stack — identidade no motor

- **Existem alertas com `status_extracao = "ok"` e marca divergente.** Caso real da avaliação: Neovite, com marca extraída "Bausch Lomb" (nome da empresa) em vez de "Neovite", e **CNPJ correto** (`27.011.022/0001-03`).
- **Se o motor exigir que a marca bata**, a loja que recebeu o produto **não é sinalizada**. É um falso "sem recall" no nível do motor, mesmo com a regra de lote correta.
- **Recomendação:**
  1. Quando o alerta tiver CNPJ, a identidade do fabricante é decidida pelo **CNPJ, comparado só pelos dígitos**.
  2. A marca é critério **secundário**.
  3. Divergência **só de marca**, com CNPJ igual, deve ir para **revisão humana** (match em `verificacao_pendente`), e não ser descartada.
- A decisão é do motor (Full-Stack). O mesmo risco está registrado em `docs/ia_limites_e_riscos.md`.
