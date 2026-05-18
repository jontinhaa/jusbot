# Notas de inspeção do corpus bruto

> Arquivo de campo — insumo direto para o Bloco 3 (parser).
> Inclui CDC, CLT, Lei 4.090, Lei 4.749 e Lei 8.036.

---

## Padrão base do Planalto (válido para todos os 5 arquivos)

### Encoding
- **Windows-1252 (ISO-8859-1)**, não UTF-8. Confirmado nos 5 arquivos.
- O VS Code abre como UTF-8 por padrão e mostra `�` no lugar de acentos — isso é o caractere `U+FFFD REPLACEMENT CHARACTER`, sinal de leitura errada.
- Para abrir corretamente: clicar em "UTF-8" no canto inferior direito → "Reopen with Encoding" → "Windows 1252".
- **Parser:** abrir com `encoding="windows-1252"` ou usar `BeautifulSoup` com `UnicodeDammit`.

### Tag base
- Todos os artigos, parágrafos e incisos usam `<p>` com `<font face="Arial">` dentro.
- A tag HTML **não distingue** o tipo — só o conteúdo de texto.

| Tipo | Padrão de texto |
|------|----------------|
| Artigo | Começa com `Art. N` (com ou sem letra: `Art. 58-A`) |
| Parágrafo | Começa com `§ N` ou `Parágrafo único` |
| Inciso | Algarismo romano + ` - ` (ex: `I - `, `II - `) |
| Alínea | Letra minúscula + `)` (ex: `a)`, `b)`) — visto na Lei 8.036 |

- Regex de artigo: **`Art\.\s*\d+(-[A-Z])?`** (não só dígitos).

### Indentação (varia entre arquivos)
- **Estilo CDC:** ~7 `&nbsp;` antes do texto, dentro do `<p>`.
- **Estilo CLT:** `style="text-indent: 35px"` no `<p>`, sem `&nbsp;`.
- **Lei 8.036:** mistura os dois.
- Parser precisa **lidar com ambos**.

### Tag decorativa
- `<font face="Arial">` e `<small>` são puramente visuais — parser ignora e extrai texto interno.

### Marcação de alterações posteriores ("Redação dada")
- Aparece como link âncora no fim do parágrafo:
  ```html
  <a href="L9008.htm#art7">(Redação dada pela Lei nº 9.008, de 21.3.1995)</a>
  ```
- Detectável buscando `<a href>` dentro de `<p>` com texto "Redação dada" ou "Incluído pela".
- **Decisão:** extrair como metadado `chunk.alterado_por`, não incluir no texto do chunk.

### `<strike>` — TEXTO REVOGADO ⚠️
- Textos riscados (`<strike>...</strike>`) são **versões antigas que foram revogadas**.
- Quantidades por arquivo:
  - CDC: poucas
  - CLT: algumas
  - Lei 4.090 / 4.749: nenhuma
  - **Lei 8.036: 334 ocorrências** (lei muito alterada desde 1990)
- **Decisão fechada:** parser **descarta** todo conteúdo dentro de `<strike>`.
- **Justificativa:** sistema responde sobre direito vigente. Ingerir versões revogadas geraria respostas incorretas. É exatamente a causa de alucinação jurídica apontada em Magesh et al. (2024).

### Lixo a descartar em todos os arquivos
- Cabeçalho: brasão (`Brastra.gif`), tabela "Presidência da República / Casa Civil / Subchefia para Assuntos Jurídicos".
- Tabela de links auxiliares: Vigência, Mensagem de veto, Regulamento, "Vide Decreto/Lei".
- Rodapé: `<script id="f5_cspm">...</script>` (telemetria do F5/CDN governo).
- Tags vazias `<p>&nbsp;</p>`, asteriscos `<font color="#FF0000">*</font>`.
- Tags estruturais: `<html>`, `<head>`, `<body>`, `<meta>`, `<style>`.

### Metadados em `<form>` hidden (rodapé — apenas alguns arquivos)
- A CLT tem um `<form>` com `<input type="hidden">` cheios de metadados estruturados:
  - `DAT_ASSINATURA_ATO`, `COD_IDENT_ATO`, `NOM_CHEFE_GOV`, `NOM_TB_ORGAO`, `DSC_SITUACAO_ATO`, `DSC_OBSERVACAO`.
- Verificar caso a caso. Quando existe, é fonte preferencial de metadados.

---

## CDC — Lei 8.078/1990 (Código de Defesa do Consumidor)

**Estrutura:** plana (Artigos → Parágrafos → Incisos). Sem Título/Capítulo.

**Delimitação do texto normativo:**
- **Início:** primeiro `<p>` com texto começando em "Art. 1"
- **Fim:** último `<p>` com texto começando em "Art." (Art. 119)

**Metadados a extrair:**
- Título: "LEI Nº 8.078, DE 11 DE SETEMBRO DE 1990"
- Ementa: "Dispõe sobre a proteção do consumidor e dá outras providências."
- Data de assinatura: "Brasília, 11 de setembro de 1990"
- Nota DOU: "publicado no DOU de 12.9.1990, retificado em 10.1.2007"

---

## CLT — Decreto-Lei 5.452/1943 (Consolidação das Leis do Trabalho)

**Estrutura:** hierárquica — **Título → Capítulo → Seção → Artigo**. Único arquivo com hierarquia profunda.

**Detecção de hierarquia:**
- `<p ALIGN="CENTER">` com texto começando em "TÍTULO", "CAPÍTULO" ou "SEÇÃO".
- Próxima linha: outro `<p ALIGN="CENTER">` com o **nome** da seção.
- Âncoras nomeadas: `<a name="tituloii">`, `<a name="tituloiicapituloi">`, etc.

**ARMADILHA — "Art. 1º" duplicado:**

Os 2 artigos iniciais (Art. 1 e Art. 2) pertencem ao **decreto-lei que aprova a CLT**, não à CLT em si. A CLT real começa depois.

- **Início real da CLT:** primeiro `<p>` após a âncora `<a name="tituloi">`.
- **Decisão fechada:** descartar os 2 artigos do decreto-lei.

**Metadados a extrair:**
- Título: "DECRETO-LEI Nº 5.452, DE 1º DE MAIO DE 1943"
- Ementa: "Aprova a Consolidação das Leis do Trabalho."
- Metadados estruturados em `<form>` hidden no rodapé:
  - `DAT_ASSINATURA_ATO=01/05/1943`
  - `NOM_CHEFE_GOV=GETÚLIO VARGAS`
  - `NOM_TB_ORGAO=MINISTÉRIO DO TRABALHO.`
  - `DSC_OBSERVACAO=[texto longo sobre alterações posteriores]`

**Particularidades:**
- Muitos artigos com letra (Art. 10-A, 58-A, 75-A a 75-F, 223-A a 223-G, etc).
- Indentação por `text-indent:35px`.
- Listas numéricas `<ol>` ocasionais dentro de artigos (1º, 2º, 3º) — fora do padrão "I, II, III". **Decisão pendente:** tratar como inciso ou descartar?

**Chunking (impacto no ADR-005):**
- Cada chunk de artigo carrega o caminho hierárquico completo como metadado: `Lei → Título → Capítulo → Seção → Artigo`.

---

## Lei 4.090/1962 (Institui o 13º salário)

**Estrutura:** plana (igual CDC). **4 artigos apenas.**

**Padrão:** estilo CDC (`<p>` com `&nbsp;` + `<font face="Arial">`).

**Metadados:**
- Título: "LEI Nº 4.090, DE 13 DE JULHO DE 1962"
- Ementa: "Institui a Gratificação de Natal para os Trabalhadores."
- Signatário: JOÃO GOULART (rodapé)
- Nota DOU: "publicado no DOU de 26.7.1962"

**Sem `<strike>`, sem hierarquia, sem armadilhas.** Parser simples roda direto.

---

## Lei 4.749/1965 (Regulamenta o pagamento do 13º)

**Estrutura:** plana. **6 artigos.**

**Padrão:** estilo CDC.

**Metadados:**
- Título: "LEI Nº 4.749, DE 12 DE AGOSTO DE 1965"
- Ementa: "Dispõe sobre o Pagamento da Gratificação Prevista na Lei nº 4.090, de 13 de julho de 1962."

**Sem `<strike>`, sem hierarquia, sem armadilhas.**

---

## Lei 8.036/1990 (FGTS)

**Estrutura:** plana (sem Título/Capítulo). Confirmado por busca.

**Padrão:** indentação **mista** (`text-indent:35px` em uns trechos, `&nbsp;` em outros).

**Particularidades:**
- **334 tags `<strike>`** — lei muito alterada. Parser deve descartar todas.
- **17 artigos com letra** — Art. N-A, N-B.
- **Tabelas HTML no corpo** — tabela de valores monetários (faixas de R$, alíquotas %, valores fixos). Aparece perto do fim.
- **Alíneas em letras minúsculas** com parêntese: `a)`, `b)`, `c)` — abaixo de incisos romanos. Não vi esse padrão no CDC.

**Decisão nova pendente — tabelas HTML:**
- (A) descartar `<table>` completamente
- (B) converter pra texto linear
- (C) preservar como chunk separado
- **Recomendação:** A — descartar por ora. Tabela de multas é caso de uso secundário, complica parser, fonte original sempre acessível.

**Metadados:**
- Título: "LEI Nº 8.036, DE 11 DE MAIO DE 1990"
- Ementa: "Dispõe sobre o Fundo de Garantia do Tempo de Serviço, e dá outras providências."

---

## ⚠️ Decisões fechadas (vão para ADRs no Bloco 2)

1. **Fontes do corpus:** todas do Planalto (LexML descartado — não expõe XML estruturado de domínio público).
2. **Encoding:** todos em Windows-1252.
3. **Decreto-lei que aprova a CLT (Art. 1 e Art. 2 originais):** descartar.
4. **`<strike>` (texto revogado):** descartar completamente. Sistema responde sobre direito vigente.
5. **"Redação dada por":** extrair como metadado `chunk.alterado_por`, não incluir no texto.
6. **Tabelas HTML (Lei 8.036):** descartar por ora.
7. **Escopo do MVP:** confirmado — CDC + CLT (subset) + FGTS (Lei 8.036) + 13º (Lei 4.090 + Lei 4.749).

## Decisões ainda em aberto (para o Bloco 2)

1. **Hierarquia da CLT no chunking:** chunk carrega o caminho completo (`Título → Capítulo → Seção → Artigo`) ou só o pai imediato?
2. **Listas `<ol>` na CLT:** trata como inciso ou descarta?
3. **Alíneas (a, b, c) na Lei 8.036:** trata como sub-nível do inciso ou agrupa no artigo-pai?
4. **Schema das tabelas no banco:** `documents`, `chunks`, `chunk_metadata` — modelagem detalhada no Bloco 2.

---

## Tabela-resumo das diferenças

| Característica | CDC | CLT | 4.090 | 4.749 | 8.036 |
|---|---|---|---|---|---|
| Encoding | win-1252 | win-1252 | win-1252 | win-1252 | win-1252 |
| Hierarquia (Título/Capítulo) | Não | **Sim** | Não | Não | Não |
| Artigos com letra (N-A) | Poucos | **Muitos** | Não | Não | **Muitos (17)** |
| `<strike>` (revogações) | Poucos | Alguns | Não | Não | **334** |
| Tabelas HTML no corpo | Não | Rodapé | Não | Não | **Sim (relevante)** |
| Alíneas (a, b, c) | Não | Pontual | Não | Não | **Sim** |
| Indentação predominante | `&nbsp;` | `text-indent` | `&nbsp;` | `&nbsp;` | Mista |
| Metadados em `<form>` hidden | Verificar | **Sim** | Não | Não | Verificar |
| Total de artigos | 119 | ~900 | 4 | 6 | ~30 |

---

## Mapa rápido de artigos relevantes do MVP

### CLT — subset trabalhista
- **Horas extras:** Arts. 58-65 (Capítulo II do Título II), esp. Art. 59
- **Férias:** Arts. 129-153 (Capítulo IV do Título II)
- **Rescisão/Demissão:** Arts. 477-486 (Capítulo V do Título IV)
- **Aviso prévio:** Arts. 487-491 (Capítulo VI do Título IV)

### FGTS
- **Lei 8.036/1990** completa (todos os ~30 artigos vigentes, descartando revogados)

### 13º salário
- **Lei 4.090/1962** — institui (4 artigos)
- **Lei 4.749/1965** — pagamento em duas parcelas (6 artigos)

---

*Atualizado durante inspeção do Bloco 1, Semana 3. Insumo direto para Bloco 3 (parser).*
