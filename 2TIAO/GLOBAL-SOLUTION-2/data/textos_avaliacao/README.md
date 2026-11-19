# Textos de avaliação do extrator

Texto oficial de cada recolhimento do golden set: a **entrada** do extrator na avaliação. O JSON do gabarito é a saída esperada.

- **Origem:** coluna "Fonte oficial" da aba "Alertas" de `../Dataset_Recall_Anvisa.xlsx`. Só domínios `*.gov.br` e `*.datalegis.net`.
- **Como foram obtidos:** `python -m ia.avaliacao.baixar_textos` (na pasta `src/`). Página do gov.br novo (Volto): texto lido do JSON `window.__data`. PDF: pdfplumber.
- **Não é o coletor:** sem agendamento e sem `fonte_hash` oficial. `manifesto.json` guarda URL, data, formato e um `sha256_local` só para reprodutibilidade.
- Recolhimentos com o mesmo texto-fonte têm arquivos idênticos: `militao` = `cecco`, `bento` = `equaliv`.

## Conferência: lotes do gabarito presentes no texto

Todos os textos contêm os lotes rotulados, com duas observações:

| Recolhimento | Situação |
|---|---|
| `la-vaquita` | O texto da RE traz `183/3 B` (com espaço); o gabarito tem `183/3B`. A avaliação compara lotes sem espaços + upper. |
| `nestle-formulas` | As tabelas da Nota Técnica 17/2026 estão **em imagem** no PDF (o pdfplumber extrai 0 dos 31 lotes). Foram **transcritas à mão** no bloco "TRANSCRIÇÃO MANUAL DE TABELA EM IMAGEM" (páginas 1–2). O script não sobrescreve esse arquivo. Entrada reportada como "transcrita" na avaliação. |
