# Testes (pytest)

| Arquivo | Cobre |
|---|---|
| `test_schemas.py` | Formatos 1 e 5; os 36 registros do golden set validam com as pendências esperadas |
| `test_prompt.py` | Few-shot só com o grupo de exemplos; nenhum lote reservado no prompt; schema de resposta |
| `test_gemini.py` | Retentativa, troca de modelo no 504/timeout, orçamento de tempo (cliente falso, sem rede) |
| `test_extrator.py` | Extrator nunca levanta exceção; motivos de falha; máscara de dados pessoais; integração real com o Gemini (pulada sem chave) |
| `test_metricas.py` | Regras de comparação da avaliação |
| `test_embalagem.py` | Leitor da embalagem com imagens sintéticas em memória; integração real com EasyOCR/pyzbar |
| `test_avaliar_ocr.py` | Script de teste das fotos, numa pasta temporária com imagens sintéticas |

Rodar: `cd 2TIAO/GLOBAL-SOLUTION-2/src/ia && python -m pytest`.
