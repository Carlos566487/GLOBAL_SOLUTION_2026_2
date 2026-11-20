# Revisão da entrega × checklist da Global Solution 2026.2

Revisão feita em **19/11/2026** comparando o repositório com o edital *GlobalSolution_2026_2* e com o documento *Arquitetura e papéis*. Legenda: ✅ atendido · 🟡 parcial · 🔴 pendente.

## 1. Requisitos obrigatórios do edital

| Requisito | Estado | Evidência / o que falta |
|---|---|---|
| Problema real CitizenTech + público-alvo + justificativa | ✅ | README §1; `data/Nota_de_Produto_e_Matriz_de_Riscos.md`; 27 recolhimentos levantados |
| Componente funcional com tecnologia do curso | ✅ | Extrator LLM, validador, motor, API e painel funcionando |
| Resultado objetivo (tabela, gráfico, indicador, tela) | ✅ | Painel com indicadores; gráficos em `docs/img/`; relatórios de extração e OCR |
| Ao menos uma abordagem atual de IA / automação / IoT | ✅ | IA Generativa (Gemini + schema) e visão computacional (EasyOCR + pyzbar) |
| Evidência de testes + limitações | ✅ | `docs/evidencias_testes.md`; 228 testes (194 IA + 34 backend); limitações no README §10 |
| Vídeo até 5 min (YouTube não listado) | ✅ | Publicado: https://youtu.be/_yUmZ12cpyI (4:50). Link no README e no PDF |
| ODS + forma de medir impacto | ✅ | ODS 3, tabela de indicadores no README §6 |
| PDF único (Intro, Desenvolvimento, Resultados, Conclusões) | 🟡 | `docs/GS2026-2_Recall_Seguro.pdf` gerado; nomes, RMs e link do vídeo preenchidos; **falta a turma** na capa |
| GitHub privado compartilhado com `fiap-tutoria` | 🔴 | Repositório `Carlos566487/GLOBAL_SOLUTION_2026_2` está **público**: mudar para privado (*Settings → General → Danger Zone → Change visibility*) e convidar `fiap-tutoria` (*Settings → Collaborators*) |
| README com proposta, tecnologias, integrantes e execução | 🟡 | README reescrito com integrantes, RMs e professores; **falta a turma** |
| Código em texto legível (sem .zip, prints, venv) | ✅ | `.gitignore` bloqueia `.zip`, `.venv`, `.env`, `node_modules` |
| Integração de múltiplas disciplinas (pódio) | ✅ | README §11 |

## 2. Componentes da arquitetura

| # | Componente | Estado | Observação |
|---|---|---|---|
| 1 | Coletor de alertas (agendado, URL + hash) | 🟡 | Só o script de avaliação `baixar_textos.py`; `POST /alertas/coletar` recebe texto já coletado |
| 2 | Extrator LLM | ✅ | Avaliado em 15 recolhimentos reservados |
| 3 | Validador Pydantic | ✅ | 36/36 registros do gabarito validam |
| 4 | Motor de regras | 🟡 | 4 tipos de regra ✅; escopo `categoria_fabricante` ✅ (corrigido em 19/11); evidência ainda no formato v1 (objeto, não lista); match sem `recebimento_id` |
| 5 | Base de recebimentos (Faker + SQLite) | 🔴 | `data/recebimentos/` só tem README; recebimentos simulados existem apenas nos testes |
| 6 | Aprovação humana | ✅ | Endpoint + botões no painel; decisão imutável (409) |
| 7 | Log de auditoria append-only | 🔴 | Não implementado; a decisão fica no próprio match, em memória |
| 8 | Painel da rede | ✅ | Selo do alerta não diferencia `verificacao_pendente` (alerta `bento` aparece como "Recall Ativo") |
| 9 | Leitor da embalagem | ✅ | 12 fotos reais avaliadas |
| 10 | App do cidadão | 🔴 | `src/app-cidadao/src/App.jsx` é cópia do painel; falta tela de câmera/upload chamando `POST /cidadao/verificar` |
| — | Persistência | 🔴 | `repositorio.py` guarda em listas em memória; reiniciar a API apaga tudo |

## 3. Métricas previstas na Nota de Produto

| Métrica | Estado |
|---|---|
| Acerto da extração por tipo de regra, recolhimento e registro | ✅ `resultados_extracao.md` |
| Falsos positivos / negativos do cruzamento | ✅ cenários 1–3, 2b e escala (0 FP, 0 FN); o FN do escopo `categoria_fabricante` foi corrigido |
| Tempo manual × automatizado | 🟡 automatizado medido (≈ 0,1 s / 1.000; mediana de 10 execuções); manual não cronometrado |
| Leitura da embalagem em 10–15 fotos | ✅ 12 fotos |

## 4. Prioridade sugerida até o prazo (20/11)

1. **Preencher** turma e link do vídeo (README e capa do PDF) e regerar o PDF (`python docs/pdf_fonte/gerar_pdf.py`).
2. ~~Gravar e publicar o vídeo~~ (feito: https://youtu.be/_yUmZ12cpyI).
3. Confirmar o convite aceito pela `fiap-tutoria`.
4. ~~Escopo `categoria_fabricante` no motor~~ (feito em 19/11). Se houver tempo: tela mínima do app do cidadão (upload → `POST /cidadao/verificar`, já validado pela API).
5. **Congelar o repositório** após o envio.

## 5. Pendências herdadas (registradas pelo Engenheiro de IA)

- Motor: identidade pelo CNPJ quando houver; divergência só de marca → revisão humana (caso Neovite) — ✅ já implementado (`marca_divergente_cnpj_compativel`).
- Tech Lead: catálogo EAN → produto a partir da base de recebimentos; coletor lendo `data/alertas_brutos/`; OCR de PDFs escaneados (caso Nestlé).
- PO: `escopo`/`categoria` no registro `sanibras` do gabarito; rotular os 7 recolhimentos fora do gabarito para o prompt v2.
