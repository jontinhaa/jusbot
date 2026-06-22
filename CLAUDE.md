# CLAUDE.md — JusBot

> **Arquivo de contexto persistente do projeto.** Este arquivo é lido automaticamente pelo Claude Code e serve como briefing para qualquer sessão de IA trabalhando neste projeto. Mantenha-o sempre atualizado.

---

## 📌 IDENTIDADE DO PROJETO

**Nome do projeto:** JusBot
**Título acadêmico:** JusBot: Um Sistema de Acesso à Justiça Orientado por Inteligência Artificial para Democratização dos Direitos do Consumidor e do Trabalho no Brasil
**Tipo:** Trabalho de Conclusão de Curso (TCC)
**Curso:** Engenharia de Software
**Autor:** Jhonatan
**Coautor:** Diogo Caldeira
**Prazo de entrega:** Final de julho de 2026 (~13 semanas a partir de abril/2026)
**Data de início:** Abril de 2026

---

## 👤 SOBRE O USUÁRIO E COMO TRABALHAR COM CLAUDE

**Perfil:** Jhonatan é engenheiro senior na prática (trabalha em Power BI, UX/UI, automação na Norsk Hydro), direto ao ponto, com baixa tolerância para excesso de formalidade ou rodeios.

**Como ele gosta de ser tratado:**

- **Direto, sem rodeios.** Não enrole, não suavize demais com cortesia corporativa.
- **Honesto.** Se ele estiver indo pra direção errada, diga. Não seja "sim patrão" demais.
- **Senior mindset.** Questione decisões dele, peça pra ver diffs, cobre rigor técnico como dois engenheiros no mesmo time.
- **Texto denso.** Corte tabelas/bullets/emojis quando virarem ruído; estrutura visual só agrega quando precisa.
- **Tom humano e leve.** Português BR natural, sem manual técnico de máquina.

**O que NUNCA fazer:**

- Falar como bot corporativo ou robô
- Sugerir "caminho fácil" quando o difícil é o certo
- Dar resposta "padrão IA" com 10 opções quando 2 resolvem
- Listar emojis demais ou seções desnecessárias
- Bajular ("ótima pergunta!", "excelente!")

**Contexto pessoal:** Localizado em Paragominas (PA), trabalha na indústria, faz este TCC enquanto trabalha — capacidade é limitada mas inteligência e pragmatismo são altos.

---

## 🎯 OBJETIVO GERAL

Desenvolver um sistema inteligente que utiliza Recuperação Aumentada por Geração (RAG), Grandes Modelos de Linguagem (LLM) e geração automatizada de documentos jurídicos para auxiliar cidadãos brasileiros vulneráveis a exercer seus direitos nas áreas de Direito do Consumidor e Direito Trabalhista, sem necessidade de advogado.

## 🎯 OBJETIVOS ESPECÍFICOS

1. Construir um corpus jurídico brasileiro estruturado cobrindo CDC, CLT e legislação correlata
2. Implementar arquitetura RAG adaptada para raciocínio jurídico em português brasileiro
3. Desenvolver pipeline de geração de documentos jurídicos válidos (PROCON, JEC, notificação extrajudicial)
4. Avaliar empiricamente a qualidade do sistema com dataset de 50 casos reais
5. Validar usabilidade com usuários reais do público-alvo via SUS (System Usability Scale)

---

## 🧠 CONTEXTO DO PROBLEMA

**Dados que fundamentam o trabalho (Pesquisa Nacional da Defensoria Pública 2022):**

- ~53 milhões de brasileiros sem acesso à assistência jurídica gratuita
- ~25% da população à margem do sistema de Justiça
- 50% das comarcas do Brasil sem cobertura da Defensoria Pública
- Proporção de 1 defensor público para cada 33.796 habitantes

**Público-alvo:** Trabalhadores, consumidores e cidadãos vulneráveis economicamente (renda familiar até 3 salários mínimos) que tiveram direitos violados e não têm como pagar advogado nem acesso prático à Defensoria.

**Lacuna identificada:** Nenhuma solução existente combina: (a) linguagem acessível, (b) análise jurídica real, (c) geração de documentos válidos, (d) foco no cidadão comum brasileiro.

---

## 🏗️ ARQUITETURA DO SISTEMA

O sistema é dividido em 5 camadas com responsabilidades bem definidas:

### Camada 1 — Ingestão e Indexação do Corpus Jurídico

- Coleta: Planalto.gov.br, LexML Brasil, APIs públicas
- Processamento: parsing de XML/PDF, limpeza, normalização
- Chunking hierárquico jurídico: Título > Capítulo > Artigo > Parágrafo > Inciso
- Geração de embeddings com `multilingual-e5-large`
- Indexação no PostgreSQL + pgvector

### Camada 2 — Conversação e Extração de Contexto

- Gerenciamento de estado com LangChain memory
- NER jurídico (entidades: partes, valores, datas, tipos de contrato)
- Classificação do domínio jurídico (consumidor/trabalhista/outros)
- Geração de perguntas de follow-up para gaps

### Camada 3 — Recuperação e Raciocínio (RAG)

- Query expansion com sinônimos jurídicos
- Busca híbrida: semântica (embeddings) + lexical (BM25)
- Re-ranking por relevância contextual
- Chain-of-thought prompting para raciocínio jurídico
- Citação obrigatória de artigos (anti-alucinação)
- Detecção automática de prazo prescricional

### Camada 4 — Geração de Documentos

- Templates em Jinja2 com campos obrigatórios validados
- LLM como preenchedor inteligente adaptando ao caso
- Validação estrutural (peças com todos os requisitos legais)
- Export em DOCX (python-docx) e PDF (WeasyPrint)

### Camada 5 — Interface e Entrega

- Web app responsivo (PWA) mobile-first
- Chat interface com indicadores de progresso
- Visualização dos direitos identificados
- Download dos documentos gerados
- Disclaimer legal visível

---

## 💻 STACK TECNOLÓGICO DEFINIDO

### Linguagem principal

- **Python 3.11+** (backend, IA, pipelines)
- **TypeScript** (frontend)

### IA e RAG

- **LLM:** claude-sonnet-4-6 via API Anthropic (claude-3-5-sonnet retirado fev/2026)
- **LangChain:** orquestração do pipeline RAG
- **PostgreSQL + pgvector:** banco vetorial persistente
- **sentence-transformers:** embeddings (`intfloat/multilingual-e5-large`)
- **rank-bm25:** busca lexical híbrida

### Backend

- **FastAPI:** API REST
- **PostgreSQL:** dados estruturados (usuários, sessões, docs gerados)
- **SQLAlchemy:** ORM
- **Pydantic:** validação de schemas

### Frontend

- **React 18 + TypeScript**
- **Vite** (build tool)
- **TailwindCSS** (estilização)
- **React PDF** (visualização de documentos)

### Geração de Documentos

- **python-docx** (DOCX)
- **WeasyPrint** (HTML → PDF)
- **Jinja2** (templates)

### Fontes de Dados Jurídicos

- **Planalto.gov.br:** legislação federal
- **LexML Brasil:** API estruturada de legislação
- **Scrapy:** jurisprudências quando necessário

### Decisões técnicas importantes já tomadas

| Decisão           | Escolha                                   | Justificativa                                        |
| ----------------- | ----------------------------------------- | ---------------------------------------------------- |
| LLM               | claude-sonnet-4-6                         | Melhor raciocínio em PT-BR, bom custo/benefício; 3.5 Sonnet retirado fev/2026 |
| Banco vetorial    | PostgreSQL + pgvector                     | Persistência estruturada, LGPD-compliant, escalável  |
| Chunking jurídico | Hierárquico (Título > Artigo > Parágrafo) | Preserva contexto legal, melhora raciocínio jurídico |
| Linguagem backend | Python                                    | Ecossistema de IA maduro, LangChain nativo           |
| Arquitetura       | Monolito modular                          | Complexidade adequada para TCC                       |
| Segurança         | LGPD como infraestrutura                  | Criptografia, mascaramento, auditoria desde o design |
| Deploy            | Local + Docker                            | Demonstração ao vivo sem dependência de cloud        |

### O que NÃO vamos usar (decisões conscientes)

- ❌ Celery/Redis (não precisa para escopo de TCC)
- ❌ Kubernetes (complexidade desnecessária)
- ❌ Microsserviços (inflaciona escopo sem ganho acadêmico)
- ❌ Fine-tuning de LLM (RAG é suficiente e mais defensável na banca)

---

## 📦 ESCOPO DO MVP

### ✅ DENTRO do escopo

**Domínios jurídicos cobertos:**

- Direito do Consumidor (CDC completo)
- Direito Trabalhista — subset de alto impacto:
  - Demissão sem justa causa
  - FGTS e verbas rescisórias
  - Horas extras
  - Aviso prévio
  - Férias e 13º

**Documentos gerados (3 tipos):**

1. Reclamação no PROCON
2. Petição inicial para Juizado Especial Cível (JEC)
3. Notificação extrajudicial

**Corpus jurídico:**

- CDC (Lei 8.078/1990)
- CLT (arts. relevantes para escopo trabalhista)
- Lei do Inquilinato (Lei 8.245/1991) — subset
- Jurisprudências selecionadas do STJ via LexML

**Funcionalidades:**

- Interface de chat funcional
- Análise de direitos violados
- Geração e download de documentos
- Identificação de prazo prescricional

**Avaliação:**

- Dataset de 50 casos reais anonimizados
- SUS (System Usability Scale) com 8–10 usuários
- Validação jurídica por professor de Direito

### ❌ FORA do escopo (Trabalhos Futuros)

- Direito de família, penal, tributário, empresarial
- Integração com e-protocolo real do judiciário
- App mobile nativo (iOS/Android)
- Geolocalização de órgãos (PROCON, JEC, Defensoria)
- Legislação estadual/municipal completa
- Scrapers de jurisprudência automatizados em produção
- Modo de acessibilidade completo (WCAG AAA)
- Internacionalização

---

## 📅 CRONOGRAMA (13 SEMANAS)

**Capacidade do autor:** 20h/semana padrão, 30h/semana nas últimas 3 semanas (~290h totais)

| Semana | Datas aprox. | Foco                                                   | Entregas                                               |
| ------ | ------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| 1      | Abr/mai      | Revisão bibliográfica + papers                         | Lista de referências + fichamentos                     |
| 2      | Mai          | Setup do ambiente + estrutura do repo                  | Projeto rodando, stack instalada                       |
| 3–4    | Mai/jun      | Ingestão + Chunking hierárquico + Indexação PostgreSQL | CDC + CLT coletados, chunked, indexados e consultáveis |
| 5      | Jun          | Motor RAG v1 (retrieval básico)                        | Consultas simples respondendo                          |
| 6      | Jun          | Motor RAG v2 (híbrido + re-ranking)                    | Qualidade melhorada                                    |
| 7      | Jun          | Gerenciamento conversacional                           | Fluxo de chat completo                                 |
| 8      | Jul          | Geração dos 3 documentos                               | Templates + preenchimento                              |
| 9      | Jul          | Frontend integrado                                     | Sistema end-to-end                                     |
| 10     | Jul          | Testes + refinamento + Validação LGPD                  | Sistema estável, compliant                             |
| 11     | Jul          | Avaliação empírica + SUS                               | Métricas coletadas                                     |
| 12     | Jul          | Análise + escrita (caps 3, 4, 5)                       | TCC ~70% escrito                                       |
| 13     | Fim de Jul   | Caps 1, 2, 6 + apresentação                            | Entrega final                                          |

---

## 📚 ESTRUTURA DO DOCUMENTO DE TCC

- **Cap. 1** — Introdução: problema, motivação, objetivos, justificativa
- **Cap. 2** — Revisão Bibliográfica: RAG, LLMs, Legal AI, acesso à justiça no Brasil
- **Cap. 3** — Metodologia e Arquitetura: decisões de design justificadas
- **Cap. 4** — Implementação: corpus, pipeline RAG, geração documental
- **Cap. 5** — Avaliação e Resultados: métricas, experimentos, análise
- **Cap. 6** — Discussão e Trabalhos Futuros
- **Cap. 7** — Conclusão

---

## 🔬 CONTRIBUIÇÕES ORIGINAIS

Respostas para a pergunta da banca "o que esse trabalho traz de novo?":

1. **Primeiro corpus jurídico brasileiro estruturado para RAG** — não existe público, indexado vetorialmente, cobrindo CDC + CLT em formato pronto para uso em sistemas RAG.

2. **Arquitetura RAG adaptada para raciocínio jurídico em PT-BR** — documentação empírica de qual estratégia de chunking, busca e prompting funciona melhor para corpus jurídico brasileiro.

3. **Pipeline de geração de documentos jurídicos válidos** — arquitetura que combina templates estáticos + preenchimento inteligente por LLM + validação estrutural, garantindo documentos válidos mesmo em edge cases.

4. **Avaliação empírica em Legal AI para contexto brasileiro** — dataset de avaliação e métricas específicas para tarefas jurídicas em português.

---

## ⚠️ CONSIDERAÇÕES ÉTICAS E LEGAIS

**O sistema NÃO substitui advogado.** É ferramenta de primeiro acesso, análoga ao que o Google faz com informação de saúde.

**Disclaimer obrigatório na interface:** "Este sistema fornece informações jurídicas educativas. Para casos complexos, consulte um advogado ou a Defensoria Pública."

**Conformidade com LGPD — Camada de Infraestrutura Real:**

- **Dados pessoais:** armazenamento criptografado (AES-256), logs auditados
- **Retenção:** dados de sessão deletados automaticamente após 24h; documentos gerados sem PII
- **Direitos do titular:** endpoints para consulta, correção e exclusão de dados
- **Consentimento:** aceite explícito pré-entrada no sistema
- **Responsável:** documentação clara de quem é responsável (Universidade/Departamento)
- **Segurança:** validação de entrada, sanitização SQL, rate limiting, HTTPS obrigatório
- **Monitoramento:** logs centralizados de acesso a dados pessoais para auditoria
- **Padrão:** conformidade verificada contra checklist LGPD em Semana 10

**Não configura advocacia não autorizada:** o sistema informa direitos e gera rascunhos de documentos — o usuário é quem protocola, assina e decide.

---

## 🎯 MÉTRICAS DE AVALIAÇÃO

### Métricas técnicas

- **Precisão de identificação do direito violado** (target: ≥80% no dataset de 50 casos)
- **Qualidade do retrieval** (Recall@5 no corpus jurídico)
- **Taxa de citação correta de artigos** (anti-alucinação)
- **Tempo médio de resposta** (target: <15s por interação)
- **Taxa de sucesso na geração do documento** (target: ≥90%)

### Métricas de usabilidade

- **SUS — System Usability Scale** com 8–10 usuários reais (target: ≥68, considerado "acima da média")
- **Taxa de conclusão de tarefa** (usuário consegue gerar documento sem ajuda)
- **Tempo médio para gerar documento**

### Validação qualitativa

- Revisão jurídica dos documentos gerados por professor de Direito
- Feedback qualitativo dos usuários em testes

---

## 🛠️ CONVENÇÕES DE CÓDIGO

### Python

- Formatação: `black` (line-length=100)
- Linting: `ruff`
- Type hints obrigatórios em funções públicas
- Docstrings no formato Google style

### TypeScript/React

- Formatação: `prettier`
- Linting: `eslint` com config React + TS
- Componentes funcionais com hooks
- Props tipadas com interfaces

### Commits

- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Mensagens em português
- Branch principal: `main`
- Branches de trabalho: `feature/<nome>`, `fix/<nome>`

### Organização de arquivos

```
/jusbot
├── CLAUDE.md                    ← ESTE ARQUIVO
├── README.md
├── pyproject.toml
├── /backend
│   ├── /src
│   │   ├── /corpus              ← ingestão e indexação
│   │   ├── /rag                 ← motor RAG
│   │   ├── /conversation        ← gerenciamento conversacional
│   │   ├── /documents           ← geração de documentos
│   │   ├── /api                 ← endpoints FastAPI
│   │   └── /models              ← schemas Pydantic
│   └── /tests
├── /frontend
│   ├── /src
│   │   ├── /components
│   │   ├── /pages
│   │   ├── /hooks
│   │   └── /lib
│   └── package.json
├── /data
│   ├── /corpus_raw              ← legislação crua baixada
│   └── /corpus_processed        ← após chunking hierárquico
├── /templates                   ← templates Jinja2 dos documentos
├── /evaluation
│   ├── /dataset                 ← 50 casos de teste
│   ├── /metrics                 ← scripts de avaliação
│   └── /results
└── /docs
    ├── /tcc                     ← capítulos do TCC
    ├── /architecture            ← diagramas e ADRs
    └── /api                     ← documentação da API
```

---

## 🤝 COMO TRABALHAR COMIGO (CLAUDE)

### Instruções para Claude em qualquer sessão futura

1. **Sempre leia este arquivo antes de sugerir mudanças estruturais** no projeto
2. **Respeite o escopo definido** — não sugira adicionar funcionalidades fora do MVP sem checar com Jhonatan
3. **Mantenha o foco no TCC** — otimizações prematuras ou refatorações grandes não são prioridade
4. **Justifique decisões técnicas** — Jhonatan precisa defender cada escolha na banca
5. **Use português BR** em comentários de código e documentação
6. **Seja direto e honesto** — Jhonatan valoriza feedback sincero sobre decisões ruins
7. **Sugira atualizações a este CLAUDE.md** quando uma decisão importante for tomada

### Divisão de responsabilidades

| Tarefa                                    | Onde fazer                      |
| ----------------------------------------- | ------------------------------- |
| Código, debugging, refatoração            | Claude Code                     |
| Estrutura de capítulos, redação acadêmica | Chat Claude.ai                  |
| Pesquisa bibliográfica                    | Chat Claude.ai (com web search) |
| Decisões arquiteturais grandes            | Chat Claude.ai                  |
| Geração de prompts, templates             | Claude Code                     |
| Revisão de textos escritos                | Chat Claude.ai                  |

### O que Claude NÃO substitui

- ❌ Rodar o código e validar que funciona na máquina do Jhonatan
- ❌ Aprovação do orientador
- ❌ Defesa da banca
- ❌ Validação jurídica dos documentos (precisa de advogado real)
- ❌ Testes com usuários reais

---

## 📌 STATUS ATUAL DO PROJETO

**Última atualização:** 16 de junho de 2026
**Fase atual:** Semana 5 concluída — motor de retrieval híbrido (vetorial + lexical, fusão RRF) com reconstrução de contexto hierárquico via parent*chunk_id. Validado com 5 consultas de domínios variados.
**Próxima ação:** Semana 6 — camada de geração (Claude 3.5 Sonnet): montar prompt com chunks recuperados e gerar resposta ancorada.
**Coorientador :** Prof. Lennon (IFPA) — Engenharia de Software
**Orientador:** Prof. Tarcísio Lemos (IFPA) — Banco de dados, arquitetura, padrões de projeto
**Riscos ativos:** *[a ser preenchido conforme surgirem]\_

### Setup de Desenvolvimento

Para subir o ambiente local:

```bash
# 1. Copiar variáveis de ambiente
cp .env.example .env

# 2. Subir PostgreSQL + pgvector via Docker
docker-compose up -d

# 3. Verificar status
docker-compose ps    # deve estar "healthy"
docker exec jusbot-postgres psql -U jusbot -d jusbot_dev -c "SELECT extname FROM pg_extension;"
```

Ver `docs/database.md` para instruções completas de conexão, troubleshooting e reset.

---

## 📝 LOG DE DECISÕES (ADR-lite)

Registre aqui qualquer decisão arquitetural ou de escopo tomada durante o projeto.

### [ADR-001] — Abril/2026 — Escolha de ChromaDB sobre Weaviate/Pinecone ⚠️ REVERTIDO pelo ADR-004

- **Contexto:** Necessidade de banco vetorial para RAG
- **Decisão:** ChromaDB
- **Justificativa:** Open-source, roda local, simplicidade adequada para TCC, sem custos de infra
- **Consequência:** Perdemos escalabilidade multi-nó, mas ganhamos reprodutibilidade total
- **Status:** Decisão revertida em 30/abr/2026 — ver ADR-004 (migração para PostgreSQL + pgvector por orientação do Prof. Tarcísio Lemos). Este registro é histórico.

### [ADR-002] — Abril/2026 — Foco em CDC + CLT (subset) como escopo do MVP

- **Contexto:** Evitar escopo inflado
- **Decisão:** Cobrir apenas Direito do Consumidor completo + CLT reduzido
- **Justificativa:** Maior impacto social, literatura mais acessível, volume de casos mais alto
- **Consequência:** Outros domínios ficam como Trabalho Futuro

### [ADR-003] — Abril/2026 → Junho/2026 — LLM principal: claude-3-5-sonnet → claude-sonnet-4-6

- **Decisão original (Abril/2026):** Claude 3.5 Sonnet via API Anthropic
- **Justificativa original:** Melhor desempenho em PT-BR para raciocínio complexo, custo aceitável para TCC
- **Migração (Junho/2026):** claude-3-5-sonnet retirado da API Anthropic em fev/2026 — modelo indisponível, chaves ativas retornam 404. Migrado para **claude-sonnet-4-6**, substituto ativo direto: mesma faixa de custo ($3/$15 por MTok), capacidade superior, suportado na API. Model ID: `claude-sonnet-4-6`.
- **Consequência:** Dependência de API paga mantida; alternativa (LLaMA 3 local) permanece documentada como fallback

### [ADR-004] — 30 de abril/2026 — Migração ChromaDB → PostgreSQL + pgvector

- **Contexto:** Necessidade de persistência estruturada, conformidade LGPD e escalabilidade
- **Decisão Anterior:** ChromaDB (local, open-source)
- **Decisão Nova:** PostgreSQL com extensão pgvector
- **Justificativa:** (Orientação do Prof. Tarcísio Lemos)
  - Integração com dados estruturados (usuários, sessões, documentos)
  - LGPD built-in: criptografia, auditoria, direitos de acesso
  - Escalabilidade sem replicação manual
  - Backup e recovery simplificados
  - Melhor para dissertação: "banco de dados" vs "cache vetorial"
- **Consequência:** +1 serviço (PostgreSQL), migração do design de ingestão, mas ganhamos defesa acadêmica e conformidade legal clara

### [ADR-005] — 30 de abril/2026 — Chunking hierárquico jurídico

- **Contexto:** Qualidade de RAG em corpus jurídico
- **Decisão:** Estratégia de chunking em 5 níveis hierárquicos
- **Estrutura:** Título > Capítulo > Artigo > Parágrafo > Inciso
- **Justificativa:** (Orientação do Prof. Tarcísio Lemos)
  - Lei brasileira é estruturada hierarquicamente por artigo, parágrafo, inciso — desrespeitar isto piora raciocínio
  - Permite raciocínio multi-escala (citar apenas o artigo, ou o inciso completo)
  - Evita "cortar no meio" de conceitos legais
  - Facilita validação: cada chunk é uma unidade legal válida
  - Melhora recall em queries jurídicas complexas
- **Consequência:** Parser inicial mais complexo, mas dataset de chunks mais coerente

### [ADR-006] — 8 de maio de 2026 — Orquestração com Docker Compose

- **Contexto:** Necessidade de ambiente de desenvolvimento reprodutível e portável para o projeto, com PostgreSQL + pgvector configurado de forma consistente entre máquinas dos colaboradores e demonstrações para banca.
- **Decisão:** Adotar Docker Compose para orquestrar o PostgreSQL com pgvector localmente.
- **Justificativa:**
  - Reprodutibilidade: mesma stack em qualquer máquina sem instalação manual
  - Isolamento: o banco roda em container, sem afetar outras instalações de PostgreSQL na máquina
  - Onboarding rápido: novo colaborador sobe o ambiente com um único comando
  - Persistência: volume nomeado garante que os dados sobrevivem entre restarts
  - Healthcheck integrado para validação automática do estado do container
- **Consequência:** Requer Docker como pré-requisito de desenvolvimento. Tecnologia padrão da indústria, com documentação extensa e curva de aprendizado baixa.

### [ADR-007] — 28 de maio de 2026 — `parent_chunk_id` substitui `texto_pai` (contexto hierárquico normalizado)

- **Contexto:** No croqui v1, `chunks.texto_pai` duplicava o texto do chunk ancestral em cada filho — resolvia o problema de chunk solto sem contexto, mas violava a 3FN e criava risco de inconsistência. Revisão do Prof. Tarcísio (Pergunta 3) apontou a redundância.
- **Decisão:** Remover `texto_pai`. Adicionar `parent_chunk_id INTEGER REFERENCES chunks(id) ON DELETE CASCADE` (FK auto-referencial). Contexto do pai reconstruído em tempo de retrieval via JOIN / CTE recursiva (`WITH RECURSIVE`), só na exibição — não na busca vetorial. **Sem view materializada** (divergência fundamentada da sugestão do orientador, aceita por ele).
- **Justificativa:**
  - Elimina duplicação e risco de inconsistência (normalização)
  - JOIN sobre ~1.800 linhas, só na montagem da resposta: custo irrelevante
  - View materializada reintroduziria a duplicação em outro lugar + `REFRESH` manual — otimização prematura para o volume
  - Mantém aberta a decisão de quanto contexto do pai enviar ao LLM (vira decisão de aplicação, não de schema)
- **Consequência:** Reconstrução de contexto exige JOIN/recursão; parser precisa inserir o pai antes do filho (ordem topológica). Se profiling futuro mostrar o JOIN como gargalo, a view pode ser adicionada sem mexer no schema base.

### [ADR-008] — 28 de maio de 2026 — `VARCHAR` + `CHECK` em vez de `ENUM` para campos categóricos

- **Contexto:** Revisão sugeriu migrar `documents.tipo_norma` e `documents.area_juridica` para `ENUM`. ENUM no PostgreSQL é rígido de alterar (adicionar valor é restrito; remover/renomear exige recriar o tipo). O projeto prevê expansão futura (`lei-complementar`, `medida-provisoria`, novas áreas).
- **Decisão:** Manter `VARCHAR` com `CHECK`, listando só os valores do corpus atual: `tipo_norma IN ('lei','decreto-lei')` e `area_juridica IN ('consumidor','trabalho')`.
- **Justificativa:**
  - Mesma garantia de integridade do ENUM (rejeita valor fora da lista)
  - Expansão é migration de uma linha (`DROP` + `ADD CONSTRAINT`), versionada no Alembic
  - Economia de espaço do ENUM é irrelevante para o volume
- **Consequência:** Divergência fundamentada da revisão, aceita pelo orientador. A lista de valores válidos vive na constraint (e neste ADR), não num tipo nomeado.

### [ADR-009] — 28 de maio de 2026 — Hierarquia como `JSONB` (LTREE adiado para trabalho futuro)

- **Contexto:** `chunks.caminho_hierarquico` representa o caminho estrutural (Título→Capítulo→Seção→Artigo). Revisão (Pergunta 1) levantou LTREE como alternativa mais expressiva para consultas de árvore.
- **Decisão:** Manter `JSONB` no MVP. LTREE registrado como possível trabalho futuro.
- **Justificativa:**
  - No JusBot a busca é vetorial (pgvector/HNSW), não navegação hierárquica em SQL
  - Hierarquia serve a filtro auxiliar + exibição do endereço do chunk — nenhum usa operadores de árvore do LTREE
  - Consultas de descendência concebíveis já são cobertas pela CTE recursiva sobre `parent_chunk_id` (ADR-007)
  - LTREE seria +1 extensão no setup (risco de reprodutibilidade na avaliação da Semana 11) sem uso real
- **Consequência:** Consultas de ancestralidade em JSONB são mais verbosas (raras, mitigadas pela CTE). GIN cobre busca por chave/valor. Se consulta por caminho exato virar frequente, considerar índice funcional antes de cogitar LTREE.

### [ADR-010] — 28 de maio de 2026 — Taxonomia de `chunks.tipo` ancorada na LC 95/1998

- **Contexto:** `chunks.tipo` é preenchido pelo parser lendo HTML do Planalto (domínio não controlado). CHECK apertado demais quebra a ingestão; sem CHECK, perde integridade. O v1 listava `artigo, paragrafo, inciso, alinea`.
- **Decisão:** Ancorar a taxonomia no art. 10 da Lei Complementar 95/1998 (rege a redação das leis brasileiras): `tipo IN ('artigo','paragrafo','inciso','alinea','item')`. Adiciona-se `item`. `caput` NÃO é tipo — quando `tipo='artigo'`, o campo `texto` guarda o caput. `parágrafo único` = `tipo='paragrafo'` com `numero='único'`.
- **Justificativa:**
  - Art. 10, II define a articulação: artigos→parágrafos/incisos; parágrafos→incisos; incisos→alíneas; alíneas→itens
  - O parágrafo único do art. 10 define "dispositivo" como "artigos, parágrafos, incisos, alíneas ou itens" — exatamente os 5 valores. A tabela `chunks` é, juridicamente, uma tabela de dispositivos
  - CHECK simultaneamente completo (não rejeita estrutura legítima) e justo (rejeita typos)
  - Argumento metodológico forte para a banca — citar a LC 95/1998 na metodologia
- **Consequência:** Estrutura fora da LC 95 (redações antigas atípicas) força o parser a normalizar antes do INSERT — comportamento desejado (sinaliza caso a tratar). Texto do chunk-artigo = só o caput, não o artigo concatenado.

### [ADR-011] — 09 de junho de 2026 — Pipeline de embeddings com `intfloat/multilingual-e5-large`

- **Contexto:** Escolha do modelo de embedding, prefixo de texto, estratégia de normalização e comportamento sob falha/interrupção para o pipeline de indexação vetorial dos 3.767 chunks.
- **Decisão:**
  - Modelo: `intfloat/multilingual-e5-large` rodando localmente via `sentence-transformers`
  - Prefixo de indexação: `"passage: "` — aplicado pelo `build_embedding_text()` em `src/corpus/embeddings.py` (ponto único de montagem do texto)
  - Prefixo de consulta: `"query: "` — aplicado em tempo de retrieval, nunca na indexação
  - Normalização: `normalize_embeddings=True` — vetores unitários, cosseno = produto interno
  - Idempotência: filtra `WHERE embedding IS NULL` a cada execução; interrupções são recuperáveis sem reprocessar chunks já gravados
  - Batches de 32 (padrão), configurável via `--batch-size`
- **Justificativa:**
  - `multilingual-e5-large` é o modelo com melhor desempenho em PT-BR para tarefas de recuperação semântica no STS benchmark multilingual, sem necessidade de fine-tuning
  - Separação `passage:`/`query:` é requisito explícito do modelo e5 — misturá-los degrada recall
  - Normalização elimina a divisão pelas normas no cosseno (simplifica o índice HNSW com `vector_cosine_ops`)
  - Ponto único (`build_embedding_text`) garante que mudança futura de estratégia (ex: enriquecimento com contexto hierárquico do pai) afeta todos os chunks de uma vez
- **Validação realizada (Semana 4):**
  - Nível 1: zero NULL, 3.767/3.767 com dim=1024
  - Nível 2: cosseno par relacionado (Art. 487×488 CLT) = 0.9617 > par não-relacionado (CDC Art. 30 × CLT Art. 66) = 0.9195
  - Nível 3: top-5 para "fui demitido sem justa causa, tenho direito a quê?" retornou 5 artigos CLT sobre rescisão sem justa causa — sem vazamento CDC
- **Consequência:** Pipeline robusto a interrupções (idempotência provou valor: 2 quedas de energia durante a indexação, nada perdido); modelo fixo no código (sem configuração externa) — troca de modelo exige reindexação completa dos 3.767 chunks.

### [ADR-012] — 16 de junho de 2026 — Busca híbrida com Reciprocal Rank Fusion (RRF)

- **Contexto:** Escolha da estratégia de fusão entre busca vetorial (pgvector cosseno) e busca lexical (pg_trgm word_similarity) para o motor de retrieval da Semana 5.
- **Decisão:**
  - Fusão por RRF: `score_rrf = Σ 1/(k_const + rank)` sobre todas as listas em que o chunk aparece; `k_const=60` (padrão da literatura, Cormack et al., 2009)
  - Top-K configurável, default 5; pool de sub-buscas = `max(k*2, 10)` por modalidade
  - Filtro por `area_juridica` opcional — desligado por padrão (vetor decide a área)
  - Contexto do pai anexado em `build_context()` via CTE recursiva sobre `parent_chunk_id` — embedding permanece puro; enriquecimento acontece só na saída
  - Saída estruturada em `ContextualChunk` com endereço montado (`_tipo_label` + `_doc_short`)
- **Justificativa:**
  - RRF sobre soma ponderada: não exige calibração de pesos entre modalidades (parâmetro único `k_const`); robusto a diferenças de escala entre scores vetoriais e trgm; comportamento estável mesmo com listas de tamanho desigual
  - `word_similarity(query, texto)` preferido sobre `similarity()` para queries curtas sobre textos longos (artigos jurídicos de 50–300 palavras)
  - Contexto do pai resolvido em retrieval (JOIN), não indexado — evita duplicação de texto no banco (ADR-007)
  - Pool de sub-buscas maior que K evita que a fusão opere sobre conjuntos de candidatos idênticos
- **Validação (Semana 5):** 5 queries cobrindo trabalho e consumidor; Q1/Q2/Q5 com retrieval correto; Q3 (prazo FGTS) e Q4 (cartão/dinheiro) identificadas como falhas de corpus, não de retrieval.
- **Limitação conhecida:** RRF pode amplificar falsos-positivos quando ambas as buscas erram de forma correlacionada — se a busca vetorial e a lexical convergem para o mesmo chunk irrelevante (ex.: Q4 #1, Lei 8.036 Art. 20-E §único com score_rrf=0.032), o score final é alto e o falso positivo entra no top-K. Mitigação futura: re-ranking por LLM (cross-encoder) na Semana 6.
- **Limitação de corpus registrada:** CDC Art. 39-A (Lei 13.455/2017 — diferenciação de preço por meio de pagamento) ausente na fonte `l8078compilado.htm` baixada em 09/06/2026. Registrado em `documents.metadata` (id=17). Não re-ingerido: reprodutibilidade por hash preservada.

---

## 🔗 REFERÊNCIAS IMPORTANTES

### Papers fundacionais

- Lewis et al. (2020) — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" — _paper original do RAG_
- Karpukhin et al. (2020) — "Dense Passage Retrieval for Open-Domain Question Answering"
- Izacard & Grave (2021) — "Leveraging Passage Retrieval with Generative Models"

### Legal AI

- Chalkidis et al. — trabalhos em LegalBench e Legal NLP
- Papers sobre PJe, eSAJ e automação jurídica no Brasil

### Acesso à Justiça (dados brasileiros)

- Pesquisa Nacional da Defensoria Pública 2022 (ANADEP)
- Justiça em Números 2024 (CNJ)
- Relatórios da OAB sobre acesso à justiça

### Usabilidade

- Brooke (1996) — "SUS: A quick and dirty usability scale"

---

## ✅ CHECKLIST PARA CADA SESSÃO DE TRABALHO

Antes de codificar, pergunte-se:

- [ ] Isto está no escopo do MVP?
- [ ] Esta decisão precisa ser documentada em ADR?
- [ ] O CLAUDE.md precisa ser atualizado?
- [ ] Tem teste para isto?
- [ ] A banca saberia defender esta escolha?

---

**Lembrete final:** Este arquivo é a memória persistente do projeto. Toda decisão importante, toda mudança de rumo, toda descoberta relevante — deve ser registrada aqui. É o que diferencia um TCC caótico de um TCC profissional.
