# CLAUDE.md — JusBot

> **Arquivo de contexto persistente do projeto.** Este arquivo é lido automaticamente pelo Claude Code e serve como briefing para qualquer sessão de IA trabalhando neste projeto. Mantenha-o sempre atualizado.

---

## 📌 IDENTIDADE DO PROJETO

**Nome do projeto:** JusBot
**Título acadêmico:** JusBot: Um Sistema de Acesso à Justiça Orientado por IA para Democratização dos Direitos do Consumidor Brasileiro
**Tipo:** Trabalho de Conclusão de Curso (TCC)
**Curso:** Engenharia de Software
**Autor:** Jhonatan
**Prazo de entrega:** Final de julho de 2026 (~13 semanas a partir de abril/2026)
**Data de início:** Abril de 2026

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
- **LLM:** Claude 3.5 Sonnet via API (ou GPT-4o como alternativa)
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

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| LLM | Claude 3.5 Sonnet | Melhor raciocínio em PT-BR, bom custo/benefício |
| Banco vetorial | PostgreSQL + pgvector | Persistência estruturada, LGPD-compliant, escalável |
| Chunking jurídico | Hierárquico (Título > Artigo > Parágrafo) | Preserva contexto legal, melhora raciocínio jurídico |
| Linguagem backend | Python | Ecossistema de IA maduro, LangChain nativo |
| Arquitetura | Monolito modular | Complexidade adequada para TCC |
| Segurança | LGPD como infraestrutura | Criptografia, mascaramento, auditoria desde o design |
| Deploy | Local + Docker | Demonstração ao vivo sem dependência de cloud |

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

| Semana | Datas aprox. | Foco | Entregas |
|--------|--------------|------|----------|
| 1 | Abr/mai | Revisão bibliográfica + papers | Lista de referências + fichamentos |
| 2 | Mai | Setup do ambiente + estrutura do repo | Projeto rodando, stack instalada |
| 3–4 | Mai/jun | Ingestão + Chunking hierárquico + Indexação PostgreSQL | CDC + CLT coletados, chunked, indexados e consultáveis |
| 5 | Jun | Motor RAG v1 (retrieval básico) | Consultas simples respondendo |
| 6 | Jun | Motor RAG v2 (híbrido + re-ranking) | Qualidade melhorada |
| 7 | Jun | Gerenciamento conversacional | Fluxo de chat completo |
| 8 | Jul | Geração dos 3 documentos | Templates + preenchimento |
| 9 | Jul | Frontend integrado | Sistema end-to-end |
| 10 | Jul | Testes + refinamento + Validação LGPD | Sistema estável, compliant |
| 11 | Jul | Avaliação empírica + SUS | Métricas coletadas |
| 12 | Jul | Análise + escrita (caps 3, 4, 5) | TCC ~70% escrito |
| 13 | Fim de Jul | Caps 1, 2, 6 + apresentação | Entrega final |

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

| Tarefa | Onde fazer |
|--------|------------|
| Código, debugging, refatoração | Claude Code |
| Estrutura de capítulos, redação acadêmica | Chat Claude.ai |
| Pesquisa bibliográfica | Chat Claude.ai (com web search) |
| Decisões arquiteturais grandes | Chat Claude.ai |
| Geração de prompts, templates | Claude Code |
| Revisão de textos escritos | Chat Claude.ai |

### O que Claude NÃO substitui

- ❌ Rodar o código e validar que funciona na máquina do Jhonatan
- ❌ Aprovação do orientador
- ❌ Defesa da banca
- ❌ Validação jurídica dos documentos (precisa de advogado real)
- ❌ Testes com usuários reais

---

## 📌 STATUS ATUAL DO PROJETO

**Última atualização:** 8 de maio de 2026
**Fase atual:** Semana 2 Bloco 2 — Ambiente de desenvolvimento pronto (Docker + PostgreSQL + pgvector)
**Próxima ação:** Modelagem SQLAlchemy (Semana 2 Bloco 3) e ingestão do corpus jurídico
**Orientador:** Prof. Tarsício Lemos
**Riscos ativos:** _[a ser preenchido conforme surgirem]_

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

### [ADR-001] — Abril/2026 — Escolha de ChromaDB sobre Weaviate/Pinecone
- **Contexto:** Necessidade de banco vetorial para RAG
- **Decisão:** ChromaDB
- **Justificativa:** Open-source, roda local, simplicidade adequada para TCC, sem custos de infra
- **Consequência:** Perdemos escalabilidade multi-nó, mas ganhamos reprodutibilidade total

### [ADR-002] — Abril/2026 — Foco em CDC + CLT (subset) como escopo do MVP
- **Contexto:** Evitar escopo inflado
- **Decisão:** Cobrir apenas Direito do Consumidor completo + CLT reduzido
- **Justificativa:** Maior impacto social, literatura mais acessível, volume de casos mais alto
- **Consequência:** Outros domínios ficam como Trabalho Futuro

### [ADR-003] — Abril/2026 — Claude 3.5 Sonnet como LLM principal
- **Contexto:** Escolha do LLM para raciocínio jurídico
- **Decisão:** Claude 3.5 Sonnet via API Anthropic
- **Justificativa:** Melhor desempenho em PT-BR para raciocínio complexo, custo aceitável para TCC
- **Consequência:** Dependência de API paga; alternativa (LLaMA 3 local) documentada como fallback

### [ADR-004] — 30 de abril/2026 — Migração ChromaDB → PostgreSQL + pgvector
- **Contexto:** Necessidade de persistência estruturada, conformidade LGPD e escalabilidade
- **Decisão Anterior:** ChromaDB (local, open-source)
- **Decisão Nova:** PostgreSQL com extensão pgvector
- **Justificativa:** (Orientação do Prof. Tarsício Lemos)
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
- **Justificativa:** (Orientação do Prof. Tarsício Lemos)
  - Lei brasileira é estruturada hierarquicamente por artigo, parágrafo, inciso — desrespeitar isto piora raciocínio
  - Permite raciocínio multi-escala (citar apenas o artigo, ou o inciso completo)
  - Evita "cortar no meio" de conceitos legais
  - Facilita validação: cada chunk é uma unidade legal válida
  - Melhora recall em queries jurídicas complexas
- **Consequência:** Parser inicial mais complexo, mas dataset de chunks mais coerente

### [ADR-006] — 8 de maio/2026 — Orquestração com Docker Compose
- **Contexto:** Ambiente de desenvolvimento reprodutível e conformidade com LGPD
- **Decisão:** Docker Compose para PostgreSQL + pgvector local
- **Justificativa:**
  - Reprodutibilidade: mesma stack em dev, teste e demonstração
  - Zero configuração manual de PostgreSQL (tudo em YAML)
  - Volume persistente para dados jurídicos sem perder entre restarts
  - Saúde monitorada via healthcheck
  - Facilita documentação de setup para banca
- **Consequência:** Dependência de Docker (instalado em 99% dos ambientes modernos), simplificação de onboarding

---

## 🔗 REFERÊNCIAS IMPORTANTES

### Papers fundacionais
- Lewis et al. (2020) — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" — *paper original do RAG*
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
