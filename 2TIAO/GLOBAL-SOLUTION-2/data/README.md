# Dados

| Arquivo / pasta | Origem | Observações |
|---|---|---|
| `Golden_Set_Recall.json` | **Real** — 20 recolhimentos oficiais (Anvisa, Prefeitura de SP, datalegis), rotulados à mão pela PO | Gabarito do extrator. **Não é base operacional.** `fonte_hash` é preenchido pelo coletor. Inclui um teste **sintético** de sufixo, fora da acurácia. |
| `Dataset_Recall_Anvisa.xlsx` | **Real** — levantamento da PO (27 recolhimentos, 01/01/2025 a 16/11/2026) | Fonte oficial indicada para cada alerta. |
| `Cenarios_Implementacao_e_Testes.md` | PO | Os 3 cenários de demo. |
| `Nota_de_Produto_e_Matriz_de_Riscos.md` | PO | Hipótese, critérios de aceite, métricas e riscos. |
| `alertas_nao_vigentes.json` | Grupo | Alertas ignorados nas consultas do cidadão (ex.: recurso administrativo). |
| `alertas_brutos/` | **Real** — coletor | Textos oficiais + URL + hash. |
| `recebimentos/` | **Simulado** | Base fictícia, `simulado: true`. |
| `fotos_teste/` | Real (embalagens) | Sem dados pessoais. |

**Limitações:** o gabarito tem só 20 recolhimentos, com predominância do tipo `lista`. O tipo `sufixo` não tem caso real. A base de recebimentos é fictícia e não representa o estoque de nenhuma rede.
