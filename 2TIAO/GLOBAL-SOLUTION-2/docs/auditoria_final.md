# Auditoria final — Recall Seguro (GS 2026.2)

**Data:** 19/11/2026 · **Base auditada:** repositório `Carlos566487/GLOBAL_SOLUTION_2026_2` (commit `1b07619`) + alterações desta auditoria.
**Critério:** em caso de divergência, vale o código executável, os testes reproduzíveis e as evidências verificáveis.

> O relatório acadêmico **V3** não foi recebido nesta auditoria. A comparação com "o PDF" foi feita com `docs/GS2026-2_Recall_Seguro.pdf` e com as afirmações listadas no pedido de revisão (25/26, 53 ms, 12 fotos, 501/126). A seção 7 lista as frases que precisam ser conferidas no V3.

---

## 1. Correções realizadas

### 1.1 Motor de regras — escopo `categoria_fabricante` (falso negativo)

| | |
|---|---|
| **Problema** | Alerta que abrange uma categoria de um fabricante (ex.: "todos os suplementos da Sanibras fabricados até 12/06/2026") não sinalizava um produto com nome comercial próprio ("Whey Protein 900 g"), porque a identidade era decidida pelo nome do produto. |
| **Contrato** | Formato 1 v2: `escopo` = `produto` \| `categoria_fabricante`; `categoria` obrigatória quando `escopo = categoria_fabricante`. Formato 2 (recebimento): `fabricante`, `cnpj`, `categoria`. O extrator já devolve `escopo: categoria_fabricante, categoria: suplemento` para a Sanibras (`docs/resultados_extracao_execucao.json`). |
| **Correção** (`src/backend/app/motor_regras.py`) | Nova função `_identidade_categoria_fabricante`: confirma **fabricante** (CNPJ; sem CNPJ em um dos lados, razão social normalizada) **e categoria**. O nome comercial não é usado. Confirmada a identidade, a regra de lote/data é aplicada pelo mesmo código de antes, e a evidência ganha a chave `identidade` com as comparações de CNPJ e categoria. |
| **Segurança** | Fabricante ou categoria ausentes → `verificacao_pendente` com o campo faltante. CNPJ ou categoria diferentes → `sem_match` (evita match abrangente demais). O comportamento só muda quando o alerta declara `escopo = categoria_fabricante`; alertas `produto` seguem a regra anterior. |
| **Teste** | `test_cenario2b_sanibras_produto_com_nome_comercial`: `xfail` removido, agora passa. +6 testes unitários em `test_motor_regras.py`. Os 6 testes novos **falham no código original** e passam no corrigido (verificado). |

### 1.2 Endpoint do cidadão — recall por categoria não pode virar `sem_recall`

| | |
|---|---|
| **Problema** | `POST /cidadao/verificar` só considerava alertas cujo **nome do produto** fosse igual ao lido na embalagem. Uma embalagem "Whey Protein 900 g / Sanibras" recebia **`sem_recall`** mesmo havendo recall de todos os suplementos Sanibras. A leitura da embalagem não traz CNPJ nem categoria, então não há como confirmar a identidade. |
| **Correção** (`src/backend/app/main.py`) | Alerta `categoria_fabricante` com marca compatível → `verificacao_pendente` com pendências `fabricante` e `categoria`. Um match conclusivo de outro alerta (`em_recall`) continua tendo prioridade. |
| **Teste** | `tests/test_cidadao_regras.py` (7 testes, leitura substituída por monkeypatch, sem depender do OCR). O caso Sanibras falha no código original e passa no corrigido. |

### 1.3 Arquivos modificados ou criados nesta etapa

| Arquivo | Tipo |
|---|---|
| `src/backend/app/motor_regras.py` | correção |
| `src/backend/app/main.py` | correção |
| `src/backend/tests/test_cenarios_demo.py` | `xfail` removido; cenário 2b ampliado (4 recebimentos) |
| `src/backend/tests/test_motor_regras.py` | +6 testes `categoria_fabricante` |
| `src/backend/tests/test_cidadao_regras.py` | novo (7 testes de decisão do cidadão) |
| `src/backend/tests/test_cidadao_verificar.py` | novo (4 testes ponta a ponta com OCR real) |
| `docs/auditoria_final.md`, `docs/evidencias_testes.md`, `docs/arquitetura.md`, `docs/revisao_entrega_checklist.md`, READMEs | documentação |
| `docs/img/evidencias/*`, `docs/img/destaques/kpis.png`, `docs/img/graficos/motor_escala.png`, `docs/GS2026-2_Recall_Seguro.pdf` | evidências e métricas atualizadas |

Nenhuma tecnologia foi trocada e nenhuma funcionalidade nova foi adicionada além das correções.

---

## 2. Resultados dos testes

| Suíte | Ambiente | Comando | Passou | Falhou | Pulado | xfail / xpass |
|---|---|---|---|---|---|---|
| Backend (34) | com EasyOCR (Python 3.13, torch 2.15, easyocr 1.7.2) | `cd src/backend && python -m pytest -v` | **34** | 0 | 0 | 0 / 0 |
| Backend (34) | sem EasyOCR (computador do grupo, Python 3.10) | idem | **30** | 0 | 1 módulo (4 testes de OCR real) | 0 / 0 |
| IA (194) | sem EasyOCR | `cd src/ia && python -m pytest` | **187** | **1** | 6 | 0 / 0 |
| IA — integração OCR | com EasyOCR | `python -m pytest tests/test_embalagem.py` | 36 | **2** | 0 | 0 / 0 |

**Falhas conhecidas (não são regressão desta auditoria):**

1. `tests/test_avaliar_ocr.py::test_leitor_original_vem_do_commit_anterior_a_regra` — executa `git show 07fcf16^:...`. O commit `07fcf16` está no histórico do repositório anterior (`JV-004/GS-2`) e **não existe no repositório atual**, que foi criado sem esse histórico. O teste vai falhar em qualquer clone do repositório atual. O teste não foi removido nem pulado.
2. `tests/test_embalagem.py::test_imagens_simuladas_da_demo[vaidosa_153 e vaidosa_154]` — esses testes **redesenham** as imagens da demo em memória com PIL; no ambiente de verificação a fonte disponível é outra e o OCR não lê a data de fabricação. As imagens PNG **versionadas** em `data/demo/` são lidas corretamente (lote, fabricação 2026-06-10, validade 2026-08-01) pelo endpoint — ver seção 3. Dependência de ambiente (fonte), registrada como limitação.

---

## 3. Fluxo do cidadão (`POST /cidadao/verificar`)

Backend FastAPI iniciado localmente; alerta oficial da Vaidosa carregado; imagens enviadas como `multipart/form-data`.

| Imagem | Tipo | Esperado | Obtido | Correção semântica |
|---|---|---|---|---|
| `demo_vaidosa_153.png` | simulada | `em_recall` | `em_recall` | ✅ EAN 2000000001531, lote 153 ∈ {148,153,166,167}, fonte gov.br, confiança 0,99 |
| `demo_vaidosa_154.png` | simulada | `sem_recall` | `sem_recall` | ✅ lote 154 ∉ lista; produto identificado |
| `demo_ilegivel.png` | simulada | `verificacao_pendente` | `verificacao_pendente` | ✅ pendência `lote` |
| `foto11.jpg` | real | `verificacao_pendente` | `verificacao_pendente` | ✅ lote H26H0115 lido; EAN real fora do catálogo da POC → `produto` |
| `foto09.jpg` | real | `verificacao_pendente` | `verificacao_pendente` | ✅ lote lido; sem EAN → `produto` |
| `foto10.jpg` | real | `verificacao_pendente` | `verificacao_pendente` | ✅ controle negativo |
| `foto03.jpg` | real | `verificacao_pendente` | `verificacao_pendente` | ✅ lote fora do quadro |
| imagem vazia | — | HTTP 400 | HTTP 400 | ✅ |

- **Nenhuma foto real gerou resposta conclusiva** (o catálogo EAN → produto da POC só contém o EAN fictício da demo). Resultado inconclusivo, documentado como limitação; é o comportamento seguro.
- Nenhum arquivo de imagem foi gravado no servidor após a consulta (verificado no sistema de arquivos).
- **Interface `src/app-cidadao/`: não operacional.** O `App.jsx` é cópia do painel da rede (sem câmera/upload). O fluxo foi validado pela API e pelo Swagger (`/docs`).

---

## 4. Arquitetura: implementado × proposto

| # | Componente | Classificação | Evidência no código |
|---|---|---|---|
| 2 | Extrator LLM (Gemini, schema, few-shot, temp. 0) | **Implementado e validado** | `src/ia/extrator.py`; avaliação em 15 recolhimentos reservados |
| 3 | Validador Pydantic (pendências recalculadas) | **Implementado e validado** | `src/ia/schemas.py`; 36/36 registros do gabarito validam |
| 4 | Motor de regras (`lista`, `sufixo`, `data_corte`, `todos`, `categoria_fabricante`) | **Implementado e validado** | `motor_regras.py`; 18 testes unitários + 5 cenários |
| 6 | Aprovação humana (decisão imutável, 409) | **Implementado e validado** | `POST /matches/{id}/decisao`; cenário 1 |
| 8 | Painel da rede (React + Vite) | **Implementado e validado** (manual) | `src/painel`; capturas de 19/11. Selo do alerta não distingue `verificacao_pendente` |
| 9 | Leitor da embalagem (OpenCV + EasyOCR + pyzbar) | **Implementado, mas experimental** | 0 erros confiantes, mas 0/12 respostas conclusivas em fotos reais |
| — | API do cidadão `POST /cidadao/verificar` | **Implementado e validado** (com imagens simuladas) | `test_cidadao_verificar.py`, `test_cidadao_regras.py` |
| 1 | Coletor de alertas (agendado, URL + hash) | **Parcialmente implementado** | `ia/avaliacao/baixar_textos.py` baixa os 20 textos de avaliação; `POST /alertas/coletar` recebe texto já coletado. Sem agendamento (APScheduler/cron) |
| — | Contrato v2 do match | **Parcialmente implementado** | `evidencia` é objeto (não lista); match sem `recebimento_id`; pendências do motor não viram match `verificacao_pendente` |
| — | Vigência (`alertas_nao_vigentes.json`) | **Parcialmente implementado** | Arquivo de dados existe; **nenhum código o lê** |
| 10 | App do cidadão (interface) | **Proposto como evolução** | Pasta existe, mas replica o painel |
| 5 | Base de recebimentos (Faker + SQLite) | **Proposto como evolução** | Recebimentos simulados só nos testes; sem SQLite nem Faker |
| 7 | Log de auditoria append-only | **Proposto como evolução** | Inexistente; a decisão fica no próprio match, em memória |
| — | Persistência | **Proposto como evolução** | `repositorio.py` usa listas em memória |
| — | Deploy (Vercel/Render) | **Proposto como evolução** | Sem configuração de deploy; CORS só `localhost` |

**Mudanças de arquitetura nesta auditoria:** nenhuma em tecnologias, componentes ou fluxos. Mudou apenas a lógica de identidade do motor e a decisão do endpoint do cidadão para alertas `categoria_fabricante`.

---

## 5. Auditoria das métricas

| Métrica documentada | Origem dos dados | Script / experimento | Natureza | Revalidação em 19/11 | Divergência |
|---|---|---|---|---|---|
| **25/26 regras de lote corretas** | 15 recolhimentos reservados do golden set (26 registros), textos oficiais em `data/textos_avaliacao/` | `python -m ia.avaliacao.avaliar_extracao` (chama o Gemini); `--so-relatorio` recalcula a partir de `docs/resultados_extracao_execucao.json` | **Dados reais**; saída do LLM gravada em 17/11/2026 (`gemini-3.5-flash-lite`, temp. 0) | ✅ **Recálculo offline reproduziu o relatório idêntico** (`.md` igual; `.csv` igual exceto fim de linha). A chamada ao LLM **não** foi refeita (sem chave de API nesta auditoria) | Nenhuma. Ressalva: amostra pequena (26 registros, 23 do tipo `lista`; `todos` 0/1; `sufixo` sem caso real) |
| **1.000 recebimentos em ~53 ms** | Recebimentos **simulados** (seed 7, 20 lojas, 8 valores de lote) | `test_escala_1000_recebimentos_sem_falso_negativo` (contagens) + medição de tempo | Dados simulados; tempo depende do hardware | ⚠️ **Tempo não reproduzido.** 10 execuções no mesmo computador: API (TestClient) **mediana 102 ms** (87–136 ms); só o motor, mediana 27 ms (21–74 ms) | **Sim.** "53 ms" foi uma única execução. Usar "≈ 0,1 s (mediana de 10 execuções, 87–136 ms) em 2 vCPUs" |
| **501 matches e 126 pendentes** | Mesma base simulada | mesmo teste (asserção automática) | Simulado | ✅ **Reproduzido**: 501/501, 126/126, 20 lojas (determinístico) | Nenhuma |
| **OCR em 12 fotos reais** | 12 fotos próprias (18/11/2026) + `gabarito_fotos.csv` rotulado manualmente | `python -m ia.avaliacao.avaliar_ocr` | Dados reais; gabarito manual | ✅ **Agregados reproduzidos** (regra alinhada): erro confiante 0/12, acerto 0/12, EAN 6/6, lote 4/7, validade 1/5, fabricação 0/1. Confiança por foto variou ±0,03 (ex.: foto09 0,79 → 0,82) por versão de biblioteca | Agregados: nenhuma. A coluna "regra original" **não é reproduzível** no repositório atual (depende do commit `07fcf16` do repositório anterior) |
| **0 falsos "sem recall"** | Extração, motor e OCR | relatórios acima + testes | — | ✅ após as correções 1.1 e 1.2. **Antes desta auditoria havia 2 caminhos para falso negativo** (motor e endpoint do cidadão no caso `categoria_fabricante`) | Afirmação só vale para o código corrigido |
| **Tempo manual × automatizado** | — | não executado | — | ❌ fluxo manual nunca cronometrado | Não apresentar redução percentual |
| **206 testes + 5 e2e** | — | pytest | — | Agora: **228 testes** (194 IA + 34 backend) | Atualizar contagem |

---

## 6. Limitações conhecidas

- Alerta `categoria_fabricante` depende de o extrator preencher `escopo`; se vier `produto` por engano, o nome comercial volta a ser exigido. O registro `sanibras` do golden set ainda não tem `escopo`/`categoria` (pendência da PO).
- Categoria é comparada por texto normalizado exato (`suplemento` ≠ `suplementos`): exige vocabulário controlado na base de recebimentos.
- Catálogo EAN → produto da API contém só o EAN fictício da demo; fotos reais ficam pendentes por desenho.
- Persistência em memória; sem coletor agendado, sem SQLite, sem log de auditoria, sem leitura de `alertas_nao_vigentes.json`.
- Interface do cidadão não implementada.
- Métricas de extração e OCR com amostras pequenas (26 registros; 12 fotos de um único celular).

## 7. Correções necessárias no relatório acadêmico (V3)

Conferir no V3 e ajustar toda ocorrência de:

1. **"53 ms"** → "≈ 0,1 s (mediana de 10 execuções, 87–136 ms; 1.000 recebimentos simulados, 20 lojas; 2 vCPUs)". Inclui KPI do resumo, tabela de cenários, tabela de ODS e título do gráfico do motor (gráfico atualizado em `docs/img/graficos/motor_escala.png`).
2. **"206 testes + 5 de ponta a ponta"** → "228 testes automatizados (194 IA + 34 backend)", com o registro das 3 falhas conhecidas de ambiente (seção 2).
3. **Caso Sanibras / `categoria_fabricante`**: qualquer menção a lacuna, `xfail` ou falso negativo aberto → "corrigido em 19/11; identidade por fabricante + categoria; pendente quando falta dado".
4. **Fluxo do cidadão**: "endpoint implementado, sem teste" → "validado de ponta a ponta com 3 imagens simuladas (`em_recall`, `sem_recall`, `verificacao_pendente`); 4 fotos reais → `verificacao_pendente`". **Não** afirmar que a interface do cidadão funciona.
5. **Arquitetura**: coletor agendado, base SQLite/Faker, log de auditoria, vigência e deploy **não podem aparecer como operacionais** — usar a classificação da seção 4.
6. **OCR**: deixar explícito que nenhuma foto real gerou resposta conclusiva e que a comparação "regra original × alinhada" é um resultado histórico não reproduzível no repositório atual.
7. **Tempo manual × automatizado**: manter como "não medido".
8. **"0 falsos sem recall"**: acrescentar "após a correção de 19/11 do escopo `categoria_fabricante`".

## 8. Como reproduzir

```bash
# backend (motor, cenários, cidadão). Com EasyOCR instalado roda os 34 testes.
cd 2TIAO/GLOBAL-SOLUTION-2/src/backend && python -m pytest -v

# IA
cd 2TIAO/GLOBAL-SOLUTION-2/src/ia && python -m pytest

# métricas de extração, sem chamar o LLM (recalcula do JSON gravado)
cd 2TIAO/GLOBAL-SOLUTION-2/src && python -m ia.avaliacao.avaliar_extracao --so-relatorio

# avaliação do OCR nas 12 fotos (exige EasyOCR; a parte "regra original" exige o histórico git antigo)
cd 2TIAO/GLOBAL-SOLUTION-2/src && python -m ia.avaliacao.avaliar_ocr

# API + Swagger para testar o cidadão manualmente
cd 2TIAO/GLOBAL-SOLUTION-2/src && uvicorn backend.app.main:app --reload
# http://127.0.0.1:8000/docs → POST /cidadao/verificar → imagem = data/demo/demo_vaidosa_153.png
# (antes, carregar o alerta: POST /motor/processar com o registro "vaidosa" do golden set e recebimentos [])
```
