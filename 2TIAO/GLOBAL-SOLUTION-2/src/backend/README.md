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
| `tests/test_cenarios_demo.py` | 3 cenários de demo + escala (1.000 recebimentos) pela API; 1 `xfail` documenta a lacuna do escopo `categoria_fabricante` |

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

Resultado em 19/11/2026: motor 12 passed; cenários 4 passed + 1 xfailed. Detalhes em [`../../docs/evidencias_testes.md`](../../docs/evidencias_testes.md).
