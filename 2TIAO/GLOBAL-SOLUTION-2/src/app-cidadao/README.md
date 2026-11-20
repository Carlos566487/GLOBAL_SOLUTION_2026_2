# App do cidadão (React + Vite)

Objetivo: o cidadão fotografa a embalagem e recebe uma das três respostas, com orientação e fonte oficial:

| Resposta | Significado |
|---|---|
| `em_recall` | Lote/fabricação corresponde a um alerta vigente. "Não consuma o produto…" + link da Anvisa |
| `sem_recall` | Sem correspondência **na base consultada**, com dados suficientes |
| `verificacao_pendente` | Foto sem lote/EAN legível ou confiança do OCR < 0,8: pedir nova foto |

## Estado em 19/11/2026

- O endpoint `POST /cidadao/verificar` (multipart, campo `imagem`) foi **validado de ponta a ponta em 19/11/2026**: `demo_vaidosa_153.png` → `em_recall`, `demo_vaidosa_154.png` → `sem_recall`, `demo_ilegivel.png` → `verificacao_pendente` (`src/backend/tests/test_cidadao_verificar.py`). A foto não é armazenada.
- O `src/App.jsx` desta pasta ainda é uma cópia do painel da rede: falta a tela de captura/upload da foto e de exibição do resultado.
- Imagens de teste prontas: `data/demo/demo_vaidosa_153.png` (→ `em_recall`), `demo_vaidosa_154.png` (→ `sem_recall`), `demo_ilegivel.png` (→ `verificacao_pendente`).

## Como executar

```bash
cd 2TIAO/GLOBAL-SOLUTION-2/src/app-cidadao
npm install
npm run dev
```
