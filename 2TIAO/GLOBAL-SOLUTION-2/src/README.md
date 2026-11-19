# Código-fonte

| Pasta | Conteúdo | Tecnologia |
|---|---|---|
| [`ia/`](ia/README.md) | Extrator LLM, validador Pydantic, leitor da embalagem (OCR + EAN), scripts de avaliação e 194 testes | Python, Gemini, Pydantic, OpenCV, EasyOCR, pyzbar |
| [`backend/`](backend/README.md) | API única (painel + cidadão), motor de regras determinístico e testes | FastAPI, pytest |
| [`painel/`](painel/README.md) | Painel da rede: alertas, matches, evidência, aprovação humana, indicadores | React 19 + Vite |
| [`app-cidadao/`](app-cidadao/README.md) | App do cidadão (em desenvolvimento) | React 19 + Vite |

Os comandos Python rodam a partir desta pasta (`src/`), porque os pacotes são importados como `ia.*` e `backend.*`.
