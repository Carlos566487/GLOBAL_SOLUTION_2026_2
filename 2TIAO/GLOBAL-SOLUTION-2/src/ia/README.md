# IA — extração de alertas e leitura da embalagem

Parte do **Engenheiro de IA** na POC de recall de alimentos:

- **Extrator:** texto oficial do alerta → JSON do formato 1, com o Google Gemini (temperatura 0, saída no schema). O LLM **só extrai**; quem decide é o motor de regras.
- **Validador:** modelos Pydantic dos formatos 1 e 5 (contrato v2). Campo decisivo nulo → `verificacao_pendente`.
- **Leitor da embalagem:** foto → formato 5, com OpenCV + EasyOCR + pyzbar, tudo local. A foto não é salva nem enviada ao LLM.

Como os outros papéis usam essas funções: [`docs/interface_ia.md`](../../docs/interface_ia.md). Limites e riscos: [`docs/ia_limites_e_riscos.md`](../../docs/ia_limites_e_riscos.md).

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `schemas.py` | `AlertaExtraido` (formato 1) e `LeituraEmbalagem` (formato 5), com cálculo determinístico de `campos_pendentes` |
| `extrator.py` | `extrair_alertas(texto, fonte_url, fonte_hash)`: nunca levanta exceção; falha → alerta pendente com `extracao:<motivo>`. `extrair_alertas_detalhado` devolve também modelo, tentativas e motivo |
| `embalagem.py` | `ler_embalagem(imagem: bytes, *, catalogo=None)`: lote, datas e EAN; nunca levanta exceção |
| `gemini.py` | Cliente Gemini: JSON no schema; 429/500/503 → esperas de 2/4/8 s; 504/timeout → próximo modelo; timeout de 30 s por chamada; teto de 90 s por extração |
| `prompt.py` | Lê o prompt versionado, monta o few-shot e gera o schema de resposta a partir do Pydantic |
| `config.py` | Variáveis do `.env` e constantes (modelos, temperatura, retentativa) |
| `prompts/` | Prompts versionados (`extracao_v1.md`) |
| `avaliacao/` | Download dos textos, avaliação da extração, teste do OCR e regras de comparação |
| `tests/` | pytest |

## Configuração

```bash
# na raiz do repositório
python -m venv .venv
.venv/Scripts/activate            # Windows (Linux/macOS: source .venv/bin/activate)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu   # PyTorch só-CPU, para o OCR
pip install -r 2TIAO/GLOBAL-SOLUTION-2/src/ia/requirements.txt
cp .env.example .env              # preencha GEMINI_API_KEY
```

| Variável (`.env`) | Padrão | Uso |
|---|---|---|
| `GEMINI_API_KEY` | — | Chave do Google AI Studio. Sem ela, os testes que chamam o Gemini são pulados |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Modelo principal (operação e demo) |
| `GEMINI_FALLBACK_MODELS` | `gemini-3.7-flash,gemini-3.8-flash` | Usados em ordem se o principal falhar |
| `EVAL_MODEL` | igual a `GEMINI_MODEL` | Modelo fixo da avaliação (sem fallback) |

No Linux, o pyzbar precisa do pacote do sistema `libzbar0`.

### Antes da demo: rodar o OCR uma vez, com internet

Na **primeira** execução, o EasyOCR baixa cerca de **100 MB** de pesos do modelo para `~/.EasyOCR`. Depois roda offline. Para não depender da rede na hora da demo:

```bash
cd 2TIAO/GLOBAL-SOLUTION-2/src
python -c "from ia.embalagem import _easyocr; _easyocr(); print('pesos do EasyOCR prontos')"
```

## Como rodar

Todos os comandos abaixo, exceto os testes, a partir de `2TIAO/GLOBAL-SOLUTION-2/src/`.

### Testes

```bash
cd 2TIAO/GLOBAL-SOLUTION-2/src/ia
python -m pytest
```

Inclui a validação dos 36 registros do golden set, o teste de vazamento de lotes reservados no prompt, os testes do extrator com gerador falso e os testes do leitor com imagens sintéticas geradas em memória. Os testes de integração com o Gemini são pulados sem `GEMINI_API_KEY`; os de integração com o EasyOCR, sem o pacote `easyocr`.

### Extração de um texto

```bash
python -m ia.extrator ../data/textos_avaliacao/vaidosa.txt \
  --url "https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2026/ricota-fresca-da-marca-vaidosa-sera-recolhida-voluntariamente-pelo-fabricante"
```

Imprime o JSON com os alertas (formato 1), o modelo que respondeu e o motivo de falha, se houver. `--hash sha256:<64 hex>` opcional.

### Avaliação da extração

```bash
python -m ia.avaliacao.avaliar_extracao                  # chama o Gemini (EVAL_MODEL) nos 15 reservados
python -m ia.avaliacao.avaliar_extracao --so-relatorio   # recalcula o relatório da última execução, sem LLM
python -m ia.avaliacao.avaliar_extracao --modelo gemini-3.8-flash   # comparação separada (arquivos com sufixo)
```

Saída: `docs/resultados_extracao.md`, `.csv` e a execução bruta `resultados_extracao_execucao.json`.

### Teste do leitor da embalagem

```bash
python -m ia.avaliacao.avaliar_ocr
```

Lê as fotos de `data/fotos_teste/` contra `data/fotos_teste/gabarito_fotos.csv` e gera `docs/resultados_ocr.md` e `.csv`.

### Imagens simuladas da demo

```bash
python -m ia.avaliacao.gerar_demo   # gera data/demo/demo_vaidosa_153.png, demo_vaidosa_154.png e demo_ilegivel.png
```

Rótulos desenhados (com a faixa "IMAGEM SIMULADA — DEMONSTRAÇÃO"), EAN fictício `2000000001531`. O `avaliar_ocr` também lê essas imagens e registra o resultado numa seção à parte do relatório.

### Textos de avaliação

```bash
python -m ia.avaliacao.baixar_textos            # baixa só os que faltam
python -m ia.avaliacao.baixar_textos --forcar   # baixa de novo (não sobrescreve transcrição manual)
```
