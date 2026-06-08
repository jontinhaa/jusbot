# Corpus Snapshot — Fim do Bloco 3 (Semana 3)

**Data:** 2026-06-08  
**Commit de referência:** branch `main`, após `670ee0d`  
**Estado:** ingestão completa, integridade **PASS**

Este documento é o estado-base do corpus. Qualquer mudança futura nos HTMLs ou no parser deve ser comparada contra estes números.

---

## Totais agregados

| métrica | valor |
|---|---|
| documentos ingeridos | 5 |
| chunks vigentes | **3.767** |
| dispositivos descartados (metadata) | 292 |
| tipos inválidos em chunks | 0 |
| `desconhecido` em metadata | 0 |
| JSON null em JSONB (bug psycopg3) | 0 |
| `caminho_hierarquico` NULL | 0 |
| **integridade** | **PASS** |

Distribuição dos chunks vigentes por tipo:

| tipo | n | % |
|---|---|---|
| artigo | 1.060 | 28,1% |
| parágrafo | 1.393 | 37,0% |
| inciso | 743 | 19,7% |
| alínea | 571 | 15,2% |
| item | 0 | 0,0% |

---

## Por documento

### Decreto-Lei nº 5.452/1943 — CLT

| campo | valor |
|---|---|
| `codigo` | `decreto-lei-5452-1943` |
| `tipo_norma` | `decreto-lei` |
| `area_juridica` | `trabalho` |
| `hash_html_bruto` | `e64f7f92e6acd09da3d226a7e663fc4d5ded970c142137c42cf79860b47dd712` |
| `data_ingestao` | 2026-06-08 |

Aritmética por tipo (vigentes + descartados = total no HTML, resíduo = 0):

| tipo | HTML | vigentes | descartados | resíduo |
|---|---|---|---|---|
| artigo | 1.016 | 837 | 179 | 0 |
| parágrafo | 1.056 | 1.022 | 34 | 0 |
| inciso | 381 | 375 | 6 | 0 |
| alínea | 475 | 475 | 0 | 0 |
| **total** | — | **2.709** | **219** | — |

Notas do parser:
- 179 artigos revogados (CLT tem seções inteiras extintas pós-CF/88)
- Bug A corrigido: FrontPage aninhava `<p>` dentro de `<p>`, links de revogação eram capturados no contexto errado
- Bug B corrigido: `_MARCADOR` exigia `)` terminal; Art. 235-H tem `(Revogado). (Vigência)` após o primeiro `)`
- `Art . 597.` (espaço antes do ponto) corrigido em `_ART` regex

---

### Lei nº 4.090/1962 — Gratificação de Natal (13° salário)

| campo | valor |
|---|---|
| `codigo` | `lei-4090-1962` |
| `tipo_norma` | `lei` |
| `area_juridica` | `trabalho` |
| `hash_html_bruto` | `6712cb8af173d377ae28d78ce772d3a6a2151b8d4ac50881c63821f5f16e2617` |
| `data_ingestao` | 2026-06-05 |

| tipo | vigentes | descartados | resíduo |
|---|---|---|---|
| artigo | 4 | 0 | 0 |
| parágrafo | 3 | 0 | 0 |
| inciso | 2 | 0 | 0 |
| **total** | **9** | **0** | — |

---

### Lei nº 4.749/1965 — Adiantamento do 13° salário

| campo | valor |
|---|---|
| `codigo` | `lei-4749-1965` |
| `tipo_norma` | `lei` |
| `area_juridica` | `trabalho` |
| `hash_html_bruto` | `334012c912a254099e8d192a08bd910081711030cbe687a97627e9440ab3cf34` |
| `data_ingestao` | 2026-06-08 |

| tipo | HTML | vigentes | descartados | resíduo |
|---|---|---|---|---|
| artigo | 8 | 8 | 0 | 0 |
| parágrafo | 3 | 2 | 1 | 0 |
| **total** | — | **10** | **1** | — |

Notas: parágrafo único vetado no Art. 5°. Estrutura plana sem incisos nem alíneas.

---

### Lei nº 8.036/1990 — FGTS

| campo | valor |
|---|---|
| `codigo` | `lei-8036-1990` |
| `tipo_norma` | `lei` |
| `area_juridica` | `trabalho` |
| `hash_html_bruto` | `a08db01777eaeb414a6dcaf76937ec6bc960878cdf5ce2e54f48ab572b440d0f` |
| `data_ingestao` | 2026-06-08 |

| tipo | HTML | vigentes | descartados | resíduo |
|---|---|---|---|---|
| artigo | 94 | 93 | 1 | 0 |
| parágrafo | 248 | 231 | 17 | 0 |
| inciso | 204 | 193 | 11 | 0 |
| alínea | 92 | 88 | 4 | 0 |
| **total** | — | **605** | **33** | — |

Notas do parser:
- Bug de divergência de classificadores corrigido: alíneas revogadas caíam como `desconhecido` porque o bloco `is_revogado` não testava `_ALI`. Correção: `_classify_tipo()` como função única compartilhada.
- 1 artefato HTML descartado silenciosamente (alínea com corpo `; Produção de efeitos` — separador de inciso que vazou para o `<p>` da alínea, corpo útil < 5 chars antes do primeiro `;`).

---

### Lei nº 8.078/1990 — CDC

| campo | valor |
|---|---|
| `codigo` | `lei-8078-1990` |
| `tipo_norma` | `lei` |
| `area_juridica` | `consumidor` |
| `hash_html_bruto` | `4673ba4977caed523230d5d71b304b980460921892eedcc5724cc669c48efc04` |
| `data_ingestao` | 2026-06-08 |

| tipo | HTML | vigentes | descartados | resíduo |
|---|---|---|---|---|
| artigo | 130 | 118 | 12 | 0 |
| parágrafo | 156 | 135 | 21 | 0 |
| inciso | 179 | 173 | 6 | 0 |
| alínea | 8 | 8 | 0 | 0 |
| **total** | — | **434** | **39** | — |

---

## Bugs corrigidos durante o Bloco 3

| commit | bug | impacto |
|---|---|---|
| `88a0a4e` | bug inicial do parser — CLT sem título | `titulo_oficial` vazio |
| `27a03f6` | psycopg3: `None` → JSON null em JSONB | JSONB com `'null'` literal em vez de SQL NULL |
| commit pré-bloco3 | CLT Bug A: `<p>` aninhado (FrontPage) | 32 artigos revogados inseridos indevidamente |
| commit pré-bloco3 | CLT Bug B: `_MARCADOR` exigia `)` terminal | Art. 235-H inserido em vez de descartado |
| `64536e2` | classificadores divergentes (FGTS alíneas) | 4 alíneas revogadas classificadas como `desconhecido` |
| `64536e2` | `Art . 597.` (CLT, espaço antes do ponto) | 1 artigo revogado classificado como `desconhecido` |

---

## Como reproduzir

```bash
# Ambiente limpo: sobe o banco e roda as migrations
docker-compose up -d
poetry run alembic upgrade head

# Ingere os 5 documentos
poetry run python -m src.corpus.ingest_corpus

# Verifica integridade
poetry run python -c "
from sqlalchemy import create_engine, text as t
import os; from dotenv import load_dotenv; load_dotenv('../.env')
e = create_engine(os.environ['DATABASE_URL'].replace('postgresql://', 'postgresql+psycopg://', 1))
with e.connect() as c:
    print(c.execute(t('SELECT COUNT(*) FROM chunks')).scalar_one(), 'chunks')
    bad = c.execute(t(\"SELECT COUNT(*) FROM chunks WHERE tipo NOT IN ('artigo','paragrafo','inciso','alinea','item')\")).scalar_one()
    print('tipos invalidos:', bad)
"
```
