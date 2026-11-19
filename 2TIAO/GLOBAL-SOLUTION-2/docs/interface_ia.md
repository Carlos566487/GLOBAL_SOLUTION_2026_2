# Interface da IA para os outros papéis

Duas funções em `src/ia/`. Esta página documenta como usar; a integração é feita por quem chama (Tech Lead e Full-Stack, a partir de 18/11).

```python
# com src/ no PYTHONPATH
from ia.extrator import extrair_alertas, extrair_alertas_detalhado
from ia.embalagem import ler_embalagem
```

Instalação e `.env`: ver `src/ia/README.md`.

---

## 1. `extrair_alertas` — pipeline de alertas (Tech Lead / Full-Stack)

```python
extrair_alertas(texto: str, fonte_url: str, fonte_hash: str | None = None) -> list[AlertaExtraido]
```

| Entrada | Regra |
|---|---|
| `texto` | Texto bruto do alerta oficial (notícia, RE ou texto extraído de PDF), como o coletor salvou. |
| `fonte_url` | URL da fonte. Só `*.gov.br` e `*.datalegis.net`. |
| `fonte_hash` | `sha256:` + 64 hex minúsculos do texto bruto, ou `None`. |

**Saída:** lista de `AlertaExtraido` (formato 1 do contrato v2). Use `a.model_dump(mode="json")` para obter o JSON.

**Garantias:**
- **Nunca levanta exceção.**
- **Fonte não oficial → lista vazia.** Nenhum alerta é criado, nem pendente.
- Um texto pode gerar vários alertas (um por produto/apresentação), todos com a mesma `fonte_url` e o mesmo `fonte_hash`.
- `alerta_id` é gerado pela IA: `<marca ou fabricante>-<produto>-<6 hex do sha256 da URL>`. É determinístico e único dentro da chamada.
- `status_extracao` e `campos_pendentes` são recalculados pelo validador. **Alerta com `campos_pendentes` não vazio não pode entrar no motor**: vai ao painel como `verificacao_pendente`.
- O LLM só extrai; nenhuma decisão de match sai daqui.

### Motivos de falha (`extracao:<motivo>` em `campos_pendentes`)

Quando a extração não pode ser concluída, volta **um** alerta pendente com `regra_lote.tipo = null` e o motivo abaixo:

| Motivo | Quando acontece | O que fazer |
|---|---|---|
| `texto_vazio` | Texto vazio ou só espaços | Conferir o coletor |
| `fonte_hash_invalido` | `fonte_hash` fora do formato `sha256:<64 hex>` | Corrigir o hash; o alerta sai com `fonte_hash = null` |
| `json_invalido` | Resposta do LLM ilegível ou sem a chave `alertas` | Revisão humana; reprocessar mais tarde |
| `item_invalido` | Um item da resposta fora do schema (os outros itens seguem normais) | Revisão humana do item; o que era legível é preservado |
| `nenhum_alerta_extraido` | O LLM não encontrou produto no texto | Revisão humana: um texto de recolhimento sem produto é suspeito |
| `orcamento_esgotado` | Nenhuma resposta em 90 s (tentativas + fallbacks) | Reprocessar mais tarde |
| `modelos_esgotados` | Todos os modelos falharam (429/500/503/504/timeout) | Reprocessar mais tarde |
| `erro_llm:<Tipo>` | Outro erro na chamada (ex.: `erro_llm:RuntimeError` sem `GEMINI_API_KEY`) | Conferir configuração |
| `erro_interno` | Falha inesperada no extrator | Avisar o Engenheiro de IA |

Os demais itens possíveis em `campos_pendentes` são campos do contrato: `produto`, `marca`, `cnpj`, `categoria`, `regra_lote.tipo`, `regra_lote.lotes`, `regra_lote.sufixo`, `regra_lote.fabricado_ate`, `revisao_manual`.

### Versão detalhada (para auditoria)

```python
r = extrair_alertas_detalhado(texto, fonte_url, fonte_hash)
r.alertas          # a mesma lista
r.modelo           # modelo que efetivamente respondeu (principal ou fallback)
r.versao_modelo    # versão informada pela API
r.prompt           # versão do prompt (ex.: "extracao_v1")
r.motivo_falha     # None, ou o motivo da tabela acima (inclui "fonte_nao_oficial")
r.fonte_recusada   # URL recusada, quando motivo_falha == "fonte_nao_oficial"
r.tentativas       # [{"modelo": ..., "codigo": 200 | 503 | ...}]
r.duracao_s
```

Sugestão para o log de auditoria (formato 7): evento `alerta_extraido`, `entidade_id = alerta_id`, `ator = "extrator:" + r.modelo`, `hash_entrada = fonte_hash`.

### Exemplo

```python
for alerta in extrair_alertas(texto_bruto, url, "sha256:" + hashlib.sha256(texto_bruto.encode()).hexdigest()):
    if alerta.status_extracao == "ok":
        enviar_ao_motor(alerta.model_dump(mode="json"))
    else:
        enviar_ao_painel_como_pendente(alerta.model_dump(mode="json"))
```

---

## 2. `ler_embalagem` — `POST /cidadao/verificar` (Full-Stack)

```python
ler_embalagem(imagem: bytes, *, catalogo: Mapping[str, tuple[str, str]] | None = None) -> LeituraEmbalagem
```

| Entrada | Regra |
|---|---|
| `imagem` | Bytes da foto (JPEG/PNG), como chegaram no upload. **Não salve em disco nem em log.** |
| `catalogo` | EAN → `(produto, marca)`. Ver abaixo. |

**Saída:** `LeituraEmbalagem` (formato 5): `ean`, `produto`, `marca`, `lote`, `data_fabricacao`, `validade`, `confianca_ocr`.

**Garantias:**
- **Nunca levanta exceção.** Imagem inválida ou falha do OCR → leitura vazia com `confianca_ocr = 0.0`.
- Tudo roda localmente (OpenCV + EasyOCR + pyzbar). A foto **não** vai para o Gemini nem para nenhum serviço externo; existe só em memória durante a chamada.
- O texto bruto do OCR não é devolvido nem logado.
- O lote volta como texto, sem correção de caracteres. A validade nunca é usada como fabricação.

### Catálogo EAN → produto (vem da base de recebimentos do Tech Lead)

O código de barras identifica o produto; o OCR não tenta adivinhar nome e marca. O catálogo deve ser montado a partir da base de produtos/recebimentos:

```python
catalogo = {
    # EAN fictício das imagens simuladas da demo (data/demo/): prefixo GS1 200 = uso interno, nunca produto real.
    # Use no teste de ponta a ponta com o alerta da Vaidosa (lotes 148, 153, 166, 167).
    "2000000001531": ("Ricota Fresca", "Vaidosa"),   # EAN como texto, 8/12/13/14 dígitos
}
leitura = ler_embalagem(foto_bytes, catalogo=catalogo)
```

- Chave: EAN como **texto** (preserva zeros à esquerda), com dígito verificador válido.
- Valor: `(produto, marca)` com a mesma grafia usada na base de recebimentos, para o motor comparar.
- Sem catálogo (ou EAN fora dele), `produto` e `marca` ficam nulos; o produto continua identificado pelo EAN.

### Convenção de lote (igual no `ler_embalagem` e no gabarito das fotos)

1. **Marcador:** `L`, `L:` ou `L.` (também `LOTE`/`LOT` com valor na mesma linha). `L` só conta como marcador seguido de `:`, `.` ou de um dígito (`L029`); `LJA 076...` **não** é marcador.
2. **Valor:** o texto logo após o marcador, sem o marcador, **na mesma linha**, até a primeira **hora** (`HH:MM`), **data** (`DD/MM/AA`, `DD/MM`, `MM/AAAA`, `MMM/AA`) ou o **fim da linha**. Espaços internos são preservados. Também para no rótulo de outro campo como palavra inteira (`VAL`, `FAB`, `VENC`, `EMP`); `VAL200127` dentro do código não corta.
3. **Rótulo sem marcador:** se não houver marcador com valor, mas houver o rótulo `Lote` (ex.: `Validade/Lote:`), o lote é a **primeira linha seguinte com dígito que não é data/hora** nem rótulo de outro campo, **inteira**.

| Texto impresso | Lote |
|---|---|
| `VAL:JAN/29 L029 SF` | `029 SF` (nada de hora/data depois: vai até o fim da linha; `SF` fica, pela regra) |
| `L:23 21:40 M5-2` | `23` |
| `L.H26H0115` | `H26H0115` |
| `VAL: 14/02/27 L: 3260` | `3260` |
| `L: JGU 080926` | `JGU 080926` |
| `Validade/Lote:` → `29/05/2027 08:37` → `LJA 076 4051 2` | `LJA 076 4051 2` |

Limitação: lote no formato de data (ex.: `21/08/2026`, `2026.09.07`) é cortado pela regra 2. Na comparação com o gabarito, o lote é comparado sem espaços + maiúsculas.

### `confianca_ocr` e a decisão de pendência

- `confianca_ocr` = a **menor** confiança do OCR entre as linhas de onde saíram o lote e as datas. Se nenhum desses campos foi lido, vale `0.0`.
- **Não decida só pela confiança.** Use `leitura.pendencias(tipo_regra)` com o tipo de regra do alerta candidato; lista vazia = dados suficientes:

| Motivo devolvido | Quando |
|---|---|
| `confianca_ocr` | `confianca_ocr < 0.8` |
| `produto` | Sem EAN e sem produto + marca |
| `lote` | Regra `lista` ou `sufixo` e lote não lido |
| `data_fabricacao` | Regra `data_corte` e fabricação não lida (a validade não substitui) |

```python
motivos = leitura.pendencias(alerta["regra_lote"]["tipo"])
if motivos:
    resultado = "verificacao_pendente"   # pedir nova foto / revisão; nunca "sem_recall"
```

`sem_recall` só pode sair quando `pendencias(...)` está vazia **e** o motor não encontrou correspondência.

---

## 3. Aviso ao motor

Ver "Aviso ao Full-Stack — identidade no motor" em `docs/dependencias_ia.md`: há alertas com `status_extracao = "ok"` e marca divergente (caso Neovite). A identidade deve ser decidida pelo CNPJ quando o alerta o tiver.
