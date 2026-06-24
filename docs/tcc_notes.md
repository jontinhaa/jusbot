# Notas de estudo — TCC JusBot

> **Propósito:** material de consulta para escrever os capítulos de metodologia/resultados e para preparar a defesa. Cada item traz a **decisão**, o **porquê** e, quando aplicável, o **argumento de banca**. Não é texto final do TCC — é o brain dump técnico de onde o texto vai sair.
>
> **Projeto:** JusBot — sistema RAG (Retrieval-Augmented Generation) para acesso à justiça em direito do consumidor e trabalhista.
> **Autores:** Jhonatan + Diogo Caldeira. **Orientação:** Prof. Lennon (principal), Prof. Tarcísio Lemos (coorientador, banco de dados).
> **Stack:** Python/FastAPI, claude-sonnet-4-6, PostgreSQL 16 + pgvector, multilingual-e5-large, Alembic, Docker Compose, Poetry. **Repo:** github.com/jontinhaa/jusbot
> **Atualizado:** junho/2026 (fim da Semana 4).

---

## 1. Visão geral da arquitetura (o mapa do sistema)

O JusBot é um pipeline RAG em camadas. Saber explicar cada camada e por que existe é a base da apresentação.

1. **Aquisição** — baixar o HTML das leis do Planalto e guardar cru no repositório (`data/corpus_raw/`). _Concluído._
2. **Parsing** — transformar o HTML em registros estruturados (`documents`, `chunks`). _Concluído (Semana 3)._
3. **Embedding** — converter cada chunk de texto em um vetor de 1024 dimensões que captura seu significado. _Concluído (Semana 4)._
4. **Retrieval** — dada uma pergunta, recuperar os chunks mais relevantes por similaridade semântica (pgvector/HNSW) combinada com busca lexical (pg*trgm). \_Semana 5.*
5. **Generation** — montar um prompt com os chunks recuperados e pedir ao Claude 3.5 Sonnet uma resposta em linguagem natural, ancorada na lei. _Semana 6+._
6. **Interface** — meio pelo qual o usuário pergunta (CLI/web). _A definir._

**Por que RAG, em uma frase de defesa:** RAG ancora as respostas do LLM em documentos autoritativos recuperados em tempo de consulta, mitigando a alucinação — o que é essencial num sistema jurídico, onde inventar lei é inaceitável. O LLM faz o papel de "explicador" do conteúdo recuperado; ele não é a fonte da verdade, a lei é.

---

## 2. Decisões de modelagem do banco (defensáveis individualmente)

### 2.1. `parent_chunk_id` em vez de `texto_pai` (ADR-007)

- **Decisão:** hierarquia representada por FK auto-referencial (`parent_chunk_id`), não por cópia do texto do pai em cada filho. Contexto do pai reconstruído via JOIN/CTE recursiva no momento da exibição.
- **Por quê:** elimina duplicação, respeita a 3ª forma normal, remove risco de inconsistência. O JOIN sobre ~3.700 linhas, executado só na montagem da resposta, é barato.
- **Divergência defendida:** o coorientador sugeriu uma _view materializada_ para pré-computar o texto do pai. Recusada com argumento: a view reintroduz a duplicação em outro lugar e exige `REFRESH` manual; é otimização prematura para o volume. Aceita pelo orientador.

### 2.2. Taxonomia ancorada na LC 95/1998 (ADR-010) — **argumento mais forte**

- **Decisão:** os tipos de chunk (`artigo, paragrafo, inciso, alinea, item`) seguem o art. 10 da Lei Complementar 95/1998, que rege a redação das leis brasileiras.
- **Por quê:** a articulação interna definida em lei é artigo → parágrafos/incisos → alíneas → itens. O parágrafo único do art. 10 (LC 107/2001) define "dispositivo" como exatamente esses cinco elementos.
- **Argumento de banca:** a tabela `chunks` **é juridicamente uma tabela de dispositivos**, e a taxonomia coincide _termo a termo_ com a enumeração legal. Não foi inventada — foi derivada da norma. Citar a LC 95/1998 na metodologia.
- **Modelagem do caput:** o caput **não é um tipo**; quando `tipo='artigo'`, o campo `texto` guarda o caput. Parágrafos/incisos/alíneas são chunks próprios pendurados via `parent_chunk_id`. Evita reduplicação.

### 2.3. `VARCHAR + CHECK` em vez de `ENUM` (ADR-008)

- **Decisão:** campos categóricos (`tipo_norma`, `area_juridica`) usam `VARCHAR` com constraint `CHECK`, não `ENUM`.
- **Por quê:** ENUM no PostgreSQL é rígido de alterar (adicionar valor é restrito; remover/renomear exige recriar o tipo). O projeto prevê expansão (`lei-complementar`, `medida-provisoria`). CHECK dá a mesma integridade com expansão por migration de uma linha.

### 2.4. JSONB para hierarquia, LTREE adiado (ADR-009)

- **Decisão:** `caminho_hierarquico` é JSONB; LTREE registrado como trabalho futuro.
- **Por quê:** a busca do sistema é vetorial (HNSW), não navegação hierárquica em SQL. A hierarquia serve a filtro auxiliar e exibição do endereço do chunk — nenhum desses usa os operadores de árvore do LTREE. As poucas consultas de descendência concebíveis já são cobertas pela CTE recursiva sobre `parent_chunk_id`. LTREE seria mais uma extensão no setup (risco de reprodutibilidade) sem uso real.

### 2.5. `hash_html_bruto` (SHA-256) — pilar de reprodutibilidade

- **Decisão:** cada documento guarda o SHA-256 do HTML bruto ingerido.
- **Por quê:** rigor metodológico — permite verificar que o pipeline rodando sobre o mesmo input produz o mesmo output (importante na avaliação empírica).
- **Uso real (não foi só teoria):** detectou o encoding corrompido do CDC e validou que o script de re-download não alterava a Lei 4.090 (usada como "canário"/teste de regressão).

### 2.6. `embedding` nullable + índice HNSW parcial

- **Decisão:** `embedding` aceita NULL; índice HNSW criado com `WHERE embedding IS NOT NULL`.
- **Por quê:** pipeline em duas fases (texto primeiro, vetores depois) permite trocar o modelo de embedding sem reingerir texto. O índice parcial ignora chunks ainda sem vetor.

### 2.7. `tamanho_chunk` como coluna GENERATED

- **Decisão:** `GENERATED ALWAYS AS (length(texto)) STORED` — calculada pelo banco, não pelo parser.
- **Por quê:** dá a coluna útil para estatística/debugging sem risco de desnormalização — nunca pode divergir do `texto`.

### Princípio transversal (vale citar como filosofia de projeto)

Várias decisões seguem o mesmo princípio: **não introduzir estrutura ou rigidez que o escopo atual não pede** (sem view materializada, sem ENUM, sem LTREE, sem particionamento). Engenharia adequada ao volume e ao propósito, não ao "e se um dia escalar".

---

## 3. Metodologia do parser (Semana 3)

### 3.1. Estratégia incremental — "menor primeiro"

- Começou pela **Lei 4.090** (10 dispositivos, estrutura plana) para provar o pipeline ponta a ponta; só depois escalou para CDC, FGTS e CLT (a mais complexa) por último.
- **Por quê:** cada documento validado revelou uma classe nova de problema _antes_ de contaminar os outros. É o princípio de "smallest reasonable change" aplicado a ingestão de corpus.

### 3.2. Validação por aritmética fechada (por documento)

- Para cada documento: **total no HTML = vigentes + descartados + resíduo zero**, contado por tipo.
- **Argumento de banca:** é a resposta para "como você garantiu que nenhum dispositivo se perdeu na ingestão?". Não é "confia no número", é uma equação que fecha.
- Exemplo CLT: 837 artigos vigentes + 178 revogados = 1.015 = total de tags `Art.` no HTML bruto. Zero resíduo.

### 3.3. Detectores plugáveis por padrão de marcação

- **Descoberta empírica:** o Planalto não tem padrão único de HTML. CDC marca revogação em `<font>` solto; Lei 4.090 em `<a>`. A lógica de classificação foi consolidada em **uma função única compartilhada** (`_classify_tipo()`) entre o fluxo de dispositivos vigentes e o de descartados, evitando "parallel hierarchies" (dois caminhos que divergem).

### 3.4. Critério explícito para dispositivos vazios

- Regra `_ali_corpo_util()`: alínea com zero caracteres alfanuméricos antes do primeiro `;` é artefato de HTML, não dispositivo real — descartada sem entrar no metadata. Critério defensável, não arbitrário.

---

## 4. Bugs encontrados e corrigidos (evidência de rigor)

Cada um aconteceu de verdade, foi diagnosticado e corrigido. Listá-los demonstra processo de engenharia sério, não acaso.

1. **Encoding cp1252 corrompido** no download do CDC — 3.440 bytes não-ASCII (`§`, `°`, acentos) substituídos por `?` literal. Detectado por inspeção de byte. Corrigido re-baixando do servidor preservando os bytes originais; parser lê com `from_encoding='cp1252'`. _Fortalece o argumento de reprodutibilidade: input bruto fiel é pré-condição._
2. **psycopg3 gravando JSON `null` literal** em colunas JSONB em vez de SQL `NULL`. Diferença sutil que quebra `WHERE ... IS NULL` e índices parciais. Corrigido com `sa.null()` explícito.
3. **Healthcheck do Docker** usando `pg_isready -U $USER` sem `-d`, gerando milhares de `FATAL: database "jusbot" does not exist` (ruído cosmético, mas mascara erros reais). Corrigido com `-d $POSTGRES_DB`.
4. **`<p>` aninhados do FrontPage** roubando o `<a>` de revogação do contexto errado — 32 artigos afetados na CLT.
5. **Marcador `(Revogado). (Vigência)`** na CLT (Art. 235-H) não casava com a regex `\)$`.
6. **`Art . 597.`** (espaço antes do ponto, defeito de geração FrontPage) na CLT.
7. **Classificador duplicado** ("parallel hierarchies") — 4 alíneas no FGTS classificadas como "desconhecido" porque o segundo classificador não consultava o detector de alínea. Corrigido pela unificação em `_classify_tipo()`.

---

## 5. Premissas declaradas (escolhas, não falhas)

Apresentar como decisões conscientes de escopo fortalece a maturidade do trabalho.

- **Versionamento por substituição:** o MVP congela o corpus; lei alterada é reingerida sobrescrevendo, sem histórico de versões. As colunas `data_vigencia`/`data_revogacao` preparam versionamento futuro. _Limitação assumida, declarar na metodologia._
- **Direito vigente, não histórico:** texto revogado/vetado é descartado da ingestão (não vira chunk buscável), mas o número do dispositivo descartado é registrado em `documents.metadata` para rastreabilidade ("por que o Art. X não aparece? Porque foi revogado pela Lei Y").
- **Adiados para trabalhos futuros:** tabela `fontes` normalizada, versionamento temporal por chunk, LTREE, embedding contextualizado (ver §7).

---

## 6. Embeddings — Semana 4 (concluída e validada)

### 6.1. Decisões

- **Modelo:** `intfloat/multilingual-e5-large`, rodando **local** via `sentence-transformers`. Escolha por reprodutibilidade (qualquer um que clone o repo gera os mesmos vetores), custo zero e volume pequeno (roda em CPU sem problema).
- **Prefixo `passage:` / `query:` (crítico):** o e5 foi treinado esperando `passage:` antes de documentos e `query:` antes de perguntas. Sem o prefixo, a busca degrada silenciosamente. Os chunks foram embeddados com `passage:`; as perguntas usam `query:`. _Pergunta provável de banca — saber explicar._
- **`normalize_embeddings=True`:** gera vetores unitários (norma 1), o que casa com `vector_cosine_ops` do índice HNSW e estabiliza a similaridade de cosseno.
- **Pipeline idempotente:** processa só chunks com `embedding IS NULL`. _Provou seu valor: duas quedas de energia durante a geração, nada perdido nem reprocessado em duplicata._
- **Função `build_embedding_text()` isolada:** único ponto que monta o texto a embeddar. Permite testar enriquecimento (ver §7) com um diff de 3 linhas.

### 6.2. Validação em 3 níveis

- **Nível 1 (estrutural):** zero `embedding IS NULL`, todos os vetores com dimensão 1024.
- **Nível 2 (sanidade semântica):** par relacionado (Art. 487 × Art. 488 da CLT, ambos sobre aviso prévio) deu cosseno **0.9617**; par não-relacionado (CDC Art. 30 × CLT Art. 66) deu **0.9195**. **Ordem correta** (relacionado > não-relacionado).
  - **Por que a margem é pequena (0.042) e isso é esperado:** o e5 e modelos multilingues comprimem as similaridades num intervalo estreito e alto. O sinal está na _ordem relativa_, não no valor absoluto. Além disso, o par "não-relacionado" eram dois textos jurídicos normativos — compartilham registro e vocabulário formal, logo são naturalmente próximos em forma, apenas distantes em tema. O modelo está medindo similaridade semântica real.
- **Nível 3 (retrieval real):** consulta em linguagem natural de leigo — _"fui demitido sem justa causa, tenho direito a quê?"_ — recuperou os 5 dispositivos mais próximos, **todos da CLT e todos sobre rescisão sem justa causa** (Art. 479, Art. 147, Art. 480, §2º, parágrafo único), **sem contaminação do CDC**.

### 6.3. Resultado empírico citável (capítulo de resultados)

> Uma consulta formulada em linguagem coloquial não-técnica recuperou os cinco dispositivos legais corretos, todos pertencentes à área jurídica pertinente (trabalhista), sem vazamento de outras áreas do corpus. Isso evidencia que (a) a busca semântica capta significado, não palavras-chave; (b) o filtro por área emerge do embedding sem regra explícita; (c) o casamento de prefixos `query:`/`passage:` está correto.

---

## 7. Trade-off em aberto (vira resultado de pesquisa na Semana 11)

**Embedding de texto puro vs. enriquecido com contexto hierárquico.** Hoje o baseline embedda só `passage: {texto}`. A alternativa é enriquecer com o caminho/contexto do pai (ex.: `passage: Art. 58-A §1º {texto}`), o que pode melhorar o recall de chunks órfãos mas pode diluir precisão. Como a montagem do texto está isolada em `build_embedding_text()`, dá para testar as duas versões na avaliação empírica e **reportar qual venceu com métricas formais** — transformando uma dúvida de implementação em contribuição mensurável do TCC.

---

## 8. Composição final do corpus (números para a defesa)

**Totais por documento (estado ao fim do Bloco 3):**

| Documento       | Código                | Chunks vigentes | Descartados |
| --------------- | --------------------- | --------------- | ----------- |
| CLT             | decreto-lei-5452-1943 | 2.709           | 219         |
| FGTS            | lei-8036-1990         | 605             | 33          |
| CDC             | lei-8078-1990         | 434             | 39          |
| Lei 4.749 (13º) | lei-4749-1965         | 10              | 1           |
| Lei 4.090 (13º) | lei-4090-1962         | 9               | 0           |
| **TOTAL**       |                       | **3.767**       | **292**     |

Total de dispositivos processados: 3.767 vigentes + 292 descartados = **4.059**.

**Detalhamento por tipo (documentos validados com tabela completa):**

- **CLT:** 837 artigos, 1.022 parágrafos, 375 incisos, 475 alíneas. (99 artigos "letrados" — 58-A, 75-F etc., resultado da Reforma Trabalhista de 2017 e emendas; o maior número é o Art. 922, fim real da CLT.)
- **FGTS:** 93 artigos, 231 parágrafos, 193 incisos, 88 alíneas, 0 itens (a lei não usa esse nível).

**Integridade verificada:** zero tipo inválido, zero JSON `null` literal, zero "desconhecido" em qualquer lugar, `caminho_hierarquico` populado em 100% dos chunks da CLT, todos os embeddings com 1024 dimensões.

---

## 9. Fundamentação teórica (referências para o texto)

Os materiais introdutórios usados para entendimento prático **não** são fontes acadêmicas — para o TCC, usar papers:

- **Lewis et al. (2020)** — paper original de RAG ("Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks").
- **Pipitone & Houir Alami (2024)** — LegalBench-RAG (RAG jurídico; já citado no croqui do banco, justifica a busca híbrida).
- **Justificativa da busca híbrida (pgvector + pg_trgm):** termos jurídicos específicos (`art. 477`, `aviso prévio`) podem não ser bem capturados só por similaridade semântica; o componente lexical melhora o recall. Alinhado com a literatura de RAG jurídico.

_Quando for escrever a fundamentação teórica, buscar os papers formais com o orientador._

---

## 10. Perguntas prováveis de banca + respostas

**P: Por que PostgreSQL + pgvector e não um banco vetorial dedicado (Pinecone, ChromaDB)?**
R: Decisão registrada em ADR (migração de ChromaDB → pgvector). Um único banco relacional armazena metadados, texto, hierarquia e vetores, com transações ACID, sem sincronizar dois sistemas. Para o volume (~3.800 chunks), pgvector com HNSW atende com folga. Reduz complexidade de infraestrutura e melhora reprodutibilidade.

**P: Como você garante que o sistema não inventa leis?**
R: É a essência do RAG. O LLM não responde de memória — ele responde a partir dos chunks recuperados do corpus, que são texto de lei real ingerido do Planalto. A geração é ancorada no retrieval. Além disso, só ingerimos direito vigente (revogado é descartado).

**P: Por que `passage:` antes do texto dos chunks?**
R: É a convenção de uso do modelo multilingual-e5-large, que foi treinado com prefixos distintos para documentos (`passage:`) e perguntas (`query:`). Omitir o prefixo desalinha os espaços vetoriais e degrada a busca. Validamos empiricamente que o casamento funciona (Nível 3 da validação).

**P: Por que o teste de similaridade deu valores tão altos (0.92) até para textos não-relacionados?**
R: Característica conhecida de modelos de embedding modernos, que concentram as similaridades num intervalo estreito. O critério de qualidade é a ordem relativa (relacionado > não-relacionado), não o valor absoluto. Ademais, os dois textos "não-relacionados" eram ambos dispositivos legais — compartilham forma e registro, sendo distantes apenas em tema.

**P: Como você garante que a ingestão não perdeu dispositivos?**
R: Validação por aritmética fechada por documento: total de dispositivos no HTML = vigentes + descartados, com resíduo zero, contado por tipo. E o `hash_html_bruto` garante que o input é reproduzível.

**P: O sistema funciona para leis alteradas após a ingestão?**
R: Não no MVP — o corpus é congelado e a atualização é por reingestão (substituição). É limitação assumida e declarada; as colunas `data_vigencia`/`data_revogacao` preparam o versionamento como trabalho futuro. O `hash_html_bruto` permite _detectar_ que uma lei mudou.

**P: Por que escolheu o multilingual-e5-large e não um modelo só de português ou um modelo maior?**
R: É multilingue com bom desempenho em português, aberto (reprodutível e gratuito), e gera vetores de 1024 dimensões adequados ao volume. Rodar local evita dependência de API e custo. O pipeline é desenhado para trocar de modelo sem reingerir texto (embedding nullable), então a escolha é reversível.

**P: Qual a maior dificuldade técnica que você enfrentou?**
R: A heterogeneidade do HTML do Planalto — encoding corrompido, marcações inconsistentes de revogação, defeitos de geração FrontPage. Resolvida com estratégia incremental (validar lei por lei), detectores unificados e validação aritmética. (Citar a lista de bugs do §4 como evidência.)

---

## 11. Cronograma (referência)

- **Semana 3:** modelagem do banco (croqui v2, ADR-007 a 010) + parser HTML. ✅
- **Semana 4:** embeddings + índice HNSW + validação de retrieval. ✅
- **Semana 3:** modelagem do banco (croqui v2, ADR-007 a 010) + parser HTML. ✅
- **Semana 4:** embeddings + índice HNSW + validação de retrieval. ✅
- **Semana 5:** motor de retrieval híbrido (RRF) + reconstrução de contexto via parent_chunk_id. ✅
- **Semana 6+:** geração com claude-sonnet-4-6; ajustes.
- **Semana 11:** avaliação empírica (rigor científico; aqui entra o experimento puro vs. enriquecido do §7).

---

## 13. Limitação conhecida do retrieval — Semana 6

**Art. 477 (verbas rescisórias) e Art. 487-491 (aviso prévio) não sobem no retrieval para queries genéricas como "tenho direito a quê?".**

Testado em k=5, k=8 e k=10: nenhum dos dois aparece. Causa: a query é semanticamente vaga e não casa com o vocabulário específico desses artigos ("aviso prévio", "rescisão indireta", "comunicação prévia"). O modelo semântico e a busca lexical convergem para artigos que contêm "sem justa causa" explicitamente, deixando artigos que TRATAM do tema mas não usam a frase fora do top-k.

**Natureza:** limitação do retrieval semântico com queries curtas/genéricas — não é bug, é característica conhecida da busca vetorial sem query expansion.

**Candidata a trabalho futuro:** query expansion com sinônimos jurídicos ("demissão sem justa causa" → expandir com "aviso prévio", "verbas rescisórias", "Art. 477") poderia resolver. Também possível: HyDE (Hypothetical Document Embeddings) — gerar uma resposta hipotética e embeddá-la como query.

**Impacto na Semana 6:** o modelo foi instruído a apontar temas a verificar (sem afirmar direitos fora da base) — solução de curto prazo adequada para o MVP.

## 12. Achados da Semana 5 (motor de retrieval)

### Achado 1 — A busca híbrida recupera o que nenhum método isolado recupera

Na consulta "fui demitido sem justa causa, tenho direito a quê?", o dispositivo do FGTS sobre a multa de 40% na demissão sem justa causa (Lei 8.036, Art. 18, §1º) aparecia em 8º lugar na busca vetorial e em 6º na lexical — fora do top-5 de ambas, isoladamente. A fusão RRF somou as duas contribuições e o promoveu ao top-5 final. Como a multa de 40% é um dos principais direitos do demitido, o resultado mostra que a busca híbrida captura dispositivos relevantes situados na fronteira de ambos os métodos, que cada busca isolada deixaria de fora. É a justificativa empírica, no próprio corpus, para a decisão de busca híbrida (alinhada à literatura de RAG jurídico, LegalBench-RAG). Vai para o capítulo de resultados.

### Achado 2 — Limitação do RRF: erros correlacionados são amplificados, não filtrados

O RRF filtra falsos-positivos que aparecem em apenas uma das listas (ex.: na Etapa 1, o CDC Art. 39 entrou só na busca lexical por coincidência da string "sem justa causa" e foi descartado da fusão). Porém, quando os dois métodos erram de forma correlacionada — atraídos pelas mesmas palavras enganosas —, a fusão reforça o erro em vez de eliminá-lo. Exemplo: na consulta sobre preço diferente no cartão/dinheiro, o Art. 20-E da Lei 8.036 (tarifa bancária do FGTS) chegou a 1º lugar porque "cobrança/tarifa/dinheiro" casou tanto na busca vetorial quanto na lexical, apesar de ser juridicamente irrelevante. Conclusão: a fusão por concordância pressupõe que os métodos errem de forma independente; sob erro correlacionado, a premissa quebra. Mitigações: filtro opcional por área jurídica (já implementado) e a própria camada de geração (o LLM pode descartar contexto irrelevante). Vai para o capítulo de limitações; revisitar na avaliação empírica da Semana 11 com métricas formais.

### Achado 3 — Lacuna de fonte do Planalto justifica empiricamente o versionamento de corpus

A consulta sobre diferenciação de preço por meio de pagamento não recuperou o dispositivo pertinente (CDC Art. 39-A, incluído pela Lei 13.455/2017) porque ele não existe na fonte ingerida: a versão compilada do Planalto (l8078compilado.htm, baixada em 09/06/2026) não incorporou aquela emenda. Não é falha do parser nem do retrieval — é defasagem seletiva da fonte governamental. O achado evidencia que fontes de texto compilado podem apresentar lacunas na incorporação de emendas, o que reforça a necessidade de (a) validação de atualidade do corpus e (b) versionamento, ambos apontados como trabalhos futuros. A lacuna, portanto, valida a decisão de design já registrada (versionamento por substituição no MVP, com data_vigencia/data_revogacao preparando o futuro). Documentada como limitação de corpus, não corrigida (re-ingerir a mesma fonte não a resolveria, e costurar fonte alternativa enfraqueceria a reprodutibilidade por hash_html_bruto).

### Limites de escopo confirmados (não são falhas)

- **Prazo de saque do FGTS (Q3):** a Lei 8.036 estabelece _quando_ se pode sacar (Art. 20, I — despedida sem justa causa), não _até quando_. O prazo de 30 dias vem da Resolução CCFGTS 460/2004, norma infralegal fora do escopo das 5 leis. O sistema recuperou corretamente as hipóteses de saque que a lei contém — não sabe o que a lei não diz. Comportamento esperado.

---

_Documento vivo — acrescentar marcos, decisões e bugs ao longo das próximas semanas. Na semana de escrita do TCC, consolidar daqui para os capítulos de metodologia e resultados._

## 14. Achados da Semana 6 (camada de geração)

### Marco — pipeline RAG completo ponta a ponta

A Semana 6 fechou a cadeia inteira: pergunta em linguagem natural → retrieval híbrido (k=8, dedup) → geração fiel e ancorada pelo claude-sonnet-4-6. Pela primeira vez a arquitetura inteira operou junta num resultado correto. Caso ilustrativo: a query sobre férias na demissão recuperou o Art. 146, §único da CLT como chunk-filho, e a geração usou tanto o texto do parágrafo quanto o caput do artigo-pai (recuperado via parent_chunk_id / CTE recursiva, ADR-007). A decisão de modelagem de meses atrás alimentou a geração na prática.

### Achado 1 — Migração de modelo forçada por descontinuação (resiliência da arquitetura)

O Claude 3.5 Sonnet, definido originalmente no ADR-003, foi retirado da API pela Anthropic (fev/2026). A migração para o claude-sonnet-4-6 (sucessor ativo, mesma faixa de custo $3/$15) exigiu apenas a troca do identificador do modelo — a arquitetura é agnóstica ao modelo de geração. Evidência de design resiliente, alinhada ao mesmo princípio do embedding nullable (trocar modelo sem reingerir). Para citar na metodologia.

### Achado 2 — Vazamento sutil de conhecimento próprio na abstenção, e sua correção

Na primeira versão, ao se abster sobre temas fora da base, o modelo afirmava que "aviso prévio e seguro-desemprego são direitos comuns na demissão" — afirmação de fato jurídico que não vinha de nenhum dispositivo recuperado, e sim do conhecimento próprio do modelo. É um vazamento sutil: bem-intencionado (útil ao usuário), mas viola a fidelidade estrita. A correção distinguiu, no prompt, entre AFIRMAR um direito (proibido — conhecimento próprio) e APONTAR um tema a verificar (permitido — protege o usuário sem afirmar conteúdo). Ex. correto: "há temas que costumam surgir — como aviso prévio — que não estão na minha base e não posso confirmar nem detalhar; vale verificar com um advogado". Conclusão metodológica: o grounding em domínio jurídico exige controlar não só a invenção óbvia, mas o vazamento disfarçado de cuidado, especialmente em detalhes de cálculo (prazos, frações, percentuais), que um leigo aceita sem questionar.

### Achado 3 — Abstenção correta nos casos-limite (validação do anti-alucinação)

Duas consultas testaram a abstenção nos casos difíceis e ambas passaram. (a) Prazo de saque do FGTS: a base contém as hipóteses de saque (Art. 20, I da Lei 8.036) mas não o prazo (que está em resolução infralegal). O sistema entregou as hipóteses e declarou explicitamente não ter o prazo, SEM inventar o valor de "30 dias" que existe na realidade mas não no corpus. (b) Diferenciação de preço cartão/dinheiro: o dispositivo pertinente (CDC Art. 39-A) está ausente do corpus por lacuna de fonte; o sistema se absteve honestamente, sem inventar regra. Evidência de que o anti-alucinação funciona não só nos casos fáceis, mas precisamente onde a tentação de "completar" é maior.

### Achado 4 — Fidelidade ao texto ≠ completude jurídica (limitação fundamental)

A consulta sobre férias proporcionais no PEDIDO de demissão expôs um limite estrutural do RAG sobre corpus puramente legislativo. A resposta foi fiel ao Art. 146, §único da CLT, mas juridicamente incompleta: tratou "pedido de demissão" e "demissão sem justa causa" sob o mesmo enquadramento, quando os dois geram conjuntos de direitos distintos (quem pede demissão não tem multa de 40% do FGTS, saque, aviso prévio indenizado nem seguro-desemprego). O modelo não errou — foi fiel ao dispositivo. O problema é que o texto da lei, isolado, não reflete a distinção que a jurisprudência (ex. Súmula 261 do TST) estabelece. Conclusão: um sistema RAG fiel pode produzir resposta juridicamente incompleta quando a interpretação correta depende de súmulas/jurisprudência ausentes do corpus. O direito é texto + súmulas + jurisprudência; o corpus tem apenas o texto. Limitação inerente à escolha de escopo (corpus legislativo), descoberta empiricamente. Trabalho futuro: incorporar súmulas do TST/STJ ao corpus.

### Limitação a investigar (menor)

A query "comprei produto com defeito, posso devolver?" recuperou dispositivos sobre FATO do produto (Art. 12, responsabilidade por dano) e arrependimento (Art. 49, compra fora da loja), mas possivelmente não o Art. 18 (VÍCIO do produto), que é o dispositivo mais central para troca/devolução de produto defeituoso. A resposta foi fiel ao recuperado, mas pode estar incompleta por limitação de retrieval. Verificar se o Art. 18 do CDC é recuperado para essa query.

## NOVA ORDEM DE SEMANA (BASICAMENTE A ANTIGA SEMANA 7)

1. Pipeline único de geração parametrizado por tipo de documento. O sistema não tem três geradores independentes; tem um pipeline (recuperação ancorada por área → redação assistida por LLM restrita aos fatos → validação estrutural → renderização) que cada tipo de peça parametriza com seu template e seus campos. Você generalizou "gerar documento jurídico" numa operação única. É argumento de arquitetura de software — teu curso.

2. Separação entre o que é determinístico e o que é generativo, por critério de risco jurídico. Esse é o ponto mais forte e mais original. Você dividiu o documento por grau de vinculação jurídica: o que vincula (fundamento legal, requerimento, consequência) é determinístico — vem do RAG, do usuário ou de texto fixo validado por advogado. Só a narrativa factual, que não cria obrigação, é gerada por LLM. Não foi uma divisão técnica arbitrária; foi guiada pelo risco. Isso responde de frente a pergunta de banca "como você garante que a IA não inventa conteúdo jurídico num documento?".

3. Decisão de design contra over-engineering (funções vs. herança). Documentar que você avaliou classe base e recusou, com justificativa de adequação ao escopo, mostra critério. Liga com a filosofia transversal do projeto (recusa de ENUM, de view materializada, de LTREE) — "engenharia adequada ao volume e ao propósito, não ao 'e se um dia escalar'". Já está no teu tcc_notes como princípio; esse é mais um caso dele.

4. Filtro de área como mitigação de uma limitação conhecida, habilitada pelo contexto. Vale registrar que o mesmo filtro (ADR-012) que ficava desligado na busca conversacional foi ligado na geração de documento, porque aqui o usuário declara a área — informação que a busca livre não tem. A limitação de retrieval da Semana 5 virou uma decisão de design consciente no contexto de documento, não um problema em aberto.
