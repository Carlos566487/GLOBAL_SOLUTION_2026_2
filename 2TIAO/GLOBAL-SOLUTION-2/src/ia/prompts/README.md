# Prompts

- `extracao_v1.md`: prompt de extração (instruções de sistema + few-shot com os 5 recolhimentos do grupo de exemplos e 1 `data_corte` sintético). Congelado antes da avaliação.
- Mudança de regra = **novo arquivo** (`extracao_v2.md`). Não editar uma versão já avaliada.
- O few-shot não pode conter nenhum recolhimento reservado; `tests/test_prompt.py` verifica isso.
