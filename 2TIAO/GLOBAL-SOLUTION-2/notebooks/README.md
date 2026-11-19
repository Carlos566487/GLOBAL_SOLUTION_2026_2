# Notebooks

A avaliação foi feita com **scripts versionados e reprodutíveis** em vez de notebooks, para que os mesmos cálculos rodem nos testes:

| Avaliação | Script (a partir de `src/`) | Relatório |
|---|---|---|
| Extrator LLM × golden set | `python -m ia.avaliacao.avaliar_extracao` (`--so-relatorio` recalcula sem chamar o LLM) | `docs/resultados_extracao.md` |
| Leitor OCR × 12 fotos | `python -m ia.avaliacao.avaliar_ocr` | `docs/resultados_ocr.md` |
| Imagens da demo | `python -m ia.avaliacao.gerar_demo` | `data/demo/` |
