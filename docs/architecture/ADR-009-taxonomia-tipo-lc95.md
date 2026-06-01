# ADR-009 — Taxonomia de `chunks.tipo` ancorada na LC 95/1998

**Status:** Aceito
**Data:** maio/2026
**Decisores:** Jhonatan, Diogo · revisão Prof. Tarcísio Lemos
**Relacionado:** ADR-005, ADR-006

## Contexto

O campo `chunks.tipo` classifica cada unidade jurídica. O v1 listava `artigo`, `paragrafo`, `inciso`, `alinea`. Diferente de `tipo_norma`/`area_juridica` (preenchidos manualmente, domínio sob controle), `tipo` é preenchido pelo **parser** lendo o HTML do Planalto — um domínio que o autor não controla. Um `CHECK` apertado demais aqui faz a ingestão falhar quando o parser encontra uma estrutura não prevista.

É preciso um `CHECK` que seja simultaneamente **completo** (não rejeite estrutura legítima) e **justo** (rejeite lixo/typos). A solução é ancorar a lista no conjunto fechado e autoritativo de unidades de articulação definido em lei.

## Decisão

Definir a taxonomia de `tipo` segundo o **art. 10 da Lei Complementar nº 95/1998**, que rege a redação das leis brasileiras. A articulação interna prevista é: artigo → parágrafos → incisos → alíneas → itens.

```sql
tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('artigo','paragrafo','inciso','alinea','item'))
```

Em relação ao v1, **adiciona-se `item`** (subdivisão de alínea; rara, mas presente na CLT e no CDC, e exatamente o tipo de estrutura que quebraria a ingestão se ausente).

**`caput` não é um tipo.** O caput é o texto de abertura do artigo, não uma unidade à parte na LC 95. Convenção: quando `tipo='artigo'`, o campo `texto` guarda o **caput**. Modelar o caput como chunk separado deixaria o chunk-artigo sem texto próprio (nó-contêiner vazio, inútil para embedding) e reintroduziria duplicação (ADR-006). Os parágrafos/incisos penduram-se no artigo via `parent_chunk_id`.

**`parágrafo único`** não é tipo novo: é `tipo='paragrafo'` com `numero='único'`.

**Texto do artigo = apenas o caput**, não o artigo inteiro concatenado. Quando há parágrafos, eles são chunks próprios; o chunk-artigo carrega só o caput (evita reduplicar texto).

## Consequências

**Positivas:** taxonomia fechada e fundamentada em norma (não em palpite) — argumento metodológico forte para a banca, alinhado com o rigor do `hash_html_bruto`; cobre toda a articulação legal possível, reduzindo falhas de ingestão; o caso clássico "Art. 5º São direitos do consumidor: I – ...; II – ..." é resolvido (caput no chunk-artigo, incisos como filhos, contexto reconstruído via `parent_chunk_id`).

**Correspondência exata com a definição legal de "dispositivo":** o parágrafo único do art. 10 da LC 95/1998 (acrescido pela LC 107/2001) define que o termo *dispositivo* refere-se a "artigos, parágrafos, incisos, alíneas ou itens" — precisamente os cinco valores do `CHECK`. A tabela `chunks` é, portanto, juridicamente uma tabela de *dispositivos*, e sua taxonomia coincide termo a termo com a enumeração legal. Esta correspondência deve ser citada na metodologia do TCC.

**Negativas / trade-offs:** se uma norma usar estrutura fora da LC 95 (ex.: redações muito antigas com "número" não padronizado), o parser precisará normalizar antes do INSERT, ou o `CHECK` falhará — comportamento desejado, pois sinaliza um caso a tratar explicitamente em vez de silenciosamente.

**Referência:** Lei Complementar nº 95, de 26/02/1998, art. 10 — conferir o texto vigente no Planalto e citar na metodologia do TCC.
