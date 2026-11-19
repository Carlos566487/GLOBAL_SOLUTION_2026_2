# Avaliação

| Arquivo | Conteúdo |
|---|---|
| `baixar_textos.py` | Baixa o texto oficial de cada recolhimento para `data/textos_avaliacao/` (não é o coletor: sem agendamento e sem hash oficial) |
| `avaliar_extracao.py` | Roda o extrator nos 15 recolhimentos reservados com modelo fixo e gera `docs/resultados_extracao.*` |
| `metricas.py` | Regras de comparação: normalização, pareamento (Jaccard ≥ 0,3 + CNPJ), regra completa, trecho de suporte, diagnóstico "valor no texto" |
| `gerar_demo.py` | Gera as 3 imagens SIMULADAS da demo em `data/demo/` (EAN fictício de uso interno) |
| `avaliar_ocr.py` | Teste do leitor da embalagem nas fotos de `data/fotos_teste/` → `docs/resultados_ocr.*` |

Comandos: ver `../README.md`.
