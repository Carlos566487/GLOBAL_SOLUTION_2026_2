# Imagens simuladas para a demonstração

**IMAGEM SIMULADA — DEMONSTRAÇÃO.** Não são fotos: são rótulos desenhados com PIL por `python -m ia.avaliacao.gerar_demo` (na pasta `src/`). Cada imagem traz a faixa e o nome do arquivo visíveis.

| Arquivo | Conteúdo | Leitura esperada | Resultado esperado no motor |
|---|---|---|---|
| `demo_vaidosa_153.png` | Ricota Fresca, Vaidosa, lote 153, fab. 10/06/2026, val. 01/08/2026 | completa, sem pendência | `em_recall` (lote 153 está no alerta da Vaidosa) |
| `demo_vaidosa_154.png` | mesmo produto, lote 154 | completa, sem pendência | `sem_recall` |
| `demo_ilegivel.png` | mesmo produto, lote borrado | pendência `lote` | `verificacao_pendente` |

- **EAN fictício:** `2000000001531` (prefixo GS1 `200`, reservado para uso interno: nunca é EAN de produto real; dígito verificador correto). Catálogo para o teste de ponta a ponta: `{"2000000001531": ("Ricota Fresca", "Vaidosa")}` (também em `docs/interface_ia.md`).
- **Fora das métricas** das fotos reais. A leitura das três imagens está em `docs/resultados_ocr.md`, seção "Imagens simuladas para demonstração".
- O desenho do rótulo (fonte monoespaçada, tamanho e espaçamento das linhas) foi escolhido para ficar legível ao leitor; o leitor e o limite de confiança de 0,8 são os mesmos usados nas fotos reais.
