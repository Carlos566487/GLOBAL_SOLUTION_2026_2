# Backend — API FastAPI e motor de regras

API única que atende o painel da rede e o app do cidadão. O **motor de regras** (`app/motor_regras.py`) é Python puro, determinístico e **não usa LLM**.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `app/main.py` | Endpoints FastAPI |
| `app/motor_regras.py` | Normalização (lote, CNPJ, texto, datas), identidade do produto e as regras `lista`, `sufixo`, `data_corte`, `todos` |
| `app/repositorio.py` | Armazenamento **em memória** (POC; reiniciar a API apaga os dados) |
| `app/schemas_api.py` | Modelos Pydantic das requisições |
| `tests/test_motor_regras.py` | 12 testes unitários do motor |
| `tests/test_cenarios_demo.py` | 3 cenários de demo, caso Sanibras com nome comercial (escopo `categoria_fabricante`) e escala (1.000 recebimentos) pela API |
| `tests/test_cidadao_verificar.py` | Fluxo do cidadão: `POST /cidadao/verificar` com as 3 imagens da demo (`em_recall`, `sem_recall`, `verificacao_pendente`); pulado sem EasyOCR |

## Endpoints

| Método | Rota | Função |
|---|---|---|
| `GET` | `/health` | Saúde do serviço |
| `POST` | `/alertas/coletar` | `{texto, fonte_url, fonte_hash?}` → extrator LLM + validador |
| `GET` | `/alertas` | Alertas carregados |
| `POST` | `/motor/processar` | `{alerta, recebimentos[]}` → resultados, matches e pendentes |
| `GET` | `/matches?alerta_id=` | Matches com evidência e status |
| `POST` | `/matches/{id}/decisao` | `{decisao: confirmado\|rejeitado, responsavel, motivo?}`; 409 se já decidido |
| `POST` | `/cidadao/verificar` | `multipart` com `imagem` → `em_recall` / `sem_recall` / `verificacao_pendente`; a imagem não é armazenada |

## Como executar

```bash
# a partir de 2TIAO/GLOBAL-SOLUTION-2/src, com o ambiente do README principal ativo
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload        # http://127.0.0.1:8000/docs
```

## Testes

```bash
cd backend
python -m pytest -v
```

Resultado em 19/11/2026 (com EasyOCR instalado): **27 passed** — motor 18, cenários 5, cidadão 4. Sem EasyOCR, o módulo do cidadão é pulado (23 passed, 1 skipped). Detalhes em [`../../docs/evidencias_testes.md`](../../docs/evidencias_testes.md).
