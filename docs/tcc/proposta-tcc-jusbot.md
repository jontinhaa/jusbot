# PROPOSTA DE TRABALHO DE CONCLUSÃO DE CURSO

**Curso:** Engenharia de Software
**Autor:** Jhonatan
**Data:** Abril de 2026

---

## TÍTULO

**JusBot: Um Sistema de Acesso à Justiça Orientado por Inteligência Artificial para Democratização dos Direitos do Consumidor e do Trabalho no Brasil**

---

## LINHAS DE PESQUISA

Engenharia de Software · Inteligência Artificial Aplicada · Processamento de Linguagem Natural · Sistemas de Informação de Impacto Social

---

## RESUMO

O Brasil apresenta um paradoxo preocupante em seu sistema de justiça: é o país com a maior proporção de advogados per capita do mundo e, simultaneamente, mantém cerca de 53 milhões de cidadãos sem acesso à assistência jurídica gratuita (Defensoria Pública da União, 2022). Essa lacuna estrutural resulta na violação sistemática de direitos básicos, especialmente nas áreas de consumo e trabalho, onde a linguagem técnica, a complexidade procedimental e o custo de representação jurídica excluem a população economicamente vulnerável.

Este trabalho propõe o desenvolvimento do **JusBot**, um sistema inteligente baseado em Recuperação Aumentada por Geração (*Retrieval-Augmented Generation* — RAG) e Grandes Modelos de Linguagem (*Large Language Models* — LLM) capaz de: (i) analisar relatos em linguagem natural sobre possíveis violações de direitos; (ii) identificar os dispositivos legais aplicáveis ao caso; (iii) gerar documentos jurídicos válidos (reclamações administrativas e petições iniciais para Juizados Especiais); e (iv) orientar o cidadão no protocolo e acompanhamento da demanda.

A proposta articula contribuições técnicas em arquitetura de sistemas RAG, curadoria de corpus jurídico em português brasileiro e pipeline de geração documental automatizada, com contribuições sociais mensuráveis no acesso à justiça.

**Palavras-chave:** Inteligência Artificial; RAG; LLM; Acesso à Justiça; Engenharia de Software; Legal Tech; Direito do Consumidor.

---

## 1. CONTEXTUALIZAÇÃO E PROBLEMA

A Constituição Federal de 1988, em seu artigo 5º, inciso XXXV, estabelece o princípio da inafastabilidade da jurisdição — a garantia de que nenhum cidadão será privado de acesso ao Poder Judiciário para defesa de seus direitos. Apesar dessa previsão constitucional, a realidade brasileira demonstra uma distância significativa entre o direito formal e sua efetividade prática.

Dados da Pesquisa Nacional da Defensoria Pública (2022) indicam que aproximadamente 25% da população brasileira — cerca de 53 milhões de pessoas — encontra-se à margem do sistema de Justiça, sem acesso à assistência jurídica gratuita. A cobertura territorial da Defensoria Pública atinge apenas 50% das comarcas brasileiras, com uma proporção de um defensor para cada 33.796 habitantes. Essa realidade impacta diretamente grupos como:

- **Trabalhadores demitidos irregularmente**, que desconhecem direitos como multa rescisória, saldo de FGTS e aviso prévio;
- **Consumidores lesados** por práticas abusivas, produtos defeituosos ou cobranças indevidas;
- **Inquilinos** submetidos a despejos extrajudiciais ou condições contratuais ilegais;
- **Cidadãos com dívidas bancárias** sujeitas a juros abusivos e cobranças irregulares.

As barreiras ao acesso à justiça incluem a linguagem jurídica complexa, a morosidade processual, a ausência de orientação prévia e a distribuição desigual de recursos públicos de assistência (CAPPELLETTI; GARTH, 1988; SADEK, 2014).

**A lacuna identificada:** as soluções tecnológicas atualmente disponíveis para o cidadão brasileiro limitam-se a portais informativos genéricos ou chatbots de direcionamento — nenhuma combina análise jurídica contextualizada, geração de documentos processualmente válidos e orientação procedimental em linguagem acessível.

---

## 2. JUSTIFICATIVA

A convergência recente de três fenômenos tecnológicos viabiliza, pela primeira vez, a construção de uma solução escalável para esse problema:

1. **Maturidade dos Modelos de Linguagem de Grande Escala (LLMs)**, que demonstram capacidade de raciocínio em português brasileiro e de compreensão de textos normativos complexos;

2. **Consolidação da arquitetura RAG** (LEWIS et al., 2020), que permite acoplar conhecimento especializado e atualizado a modelos generalistas sem necessidade de re-treinamento;

3. **Disponibilidade pública e estruturada do corpus jurídico brasileiro**, através de portais como LexML e Planalto.gov.br.

Do ponto de vista acadêmico, o trabalho contribui com: (i) um corpus jurídico brasileiro estruturado para sistemas RAG — artefato hoje inexistente na literatura; (ii) avaliação empírica de estratégias de chunking, busca híbrida e *prompt engineering* aplicadas ao domínio jurídico em PT-BR; (iii) arquitetura replicável para sistemas de *Legal AI* de impacto social.

Do ponto de vista social, o sistema proposto endereça diretamente um problema estrutural que afeta aproximadamente um quarto da população brasileira, com potencial de atuar como ferramenta de primeiro acesso à justiça, complementar — não substitutiva — da Defensoria Pública e dos Juizados Especiais.

---

## 3. OBJETIVOS

### 3.1 Objetivo Geral

Desenvolver e avaliar um sistema inteligente de acesso à justiça, baseado em RAG e LLMs, capaz de analisar violações de direitos em linguagem natural, identificar dispositivos legais aplicáveis e gerar documentos jurídicos válidos para o cidadão brasileiro nas áreas de Direito do Consumidor e Direito Trabalhista.

### 3.2 Objetivos Específicos

a) Construir um corpus jurídico brasileiro estruturado cobrindo o Código de Defesa do Consumidor (Lei 8.078/1990), a Consolidação das Leis do Trabalho (subset de alto impacto) e legislação correlata;

b) Implementar uma arquitetura de software em camadas para o sistema, com pipelines de ingestão, indexação vetorial, recuperação híbrida e geração de documentos;

c) Desenvolver estratégias de *prompt engineering* com raciocínio em cadeia (*chain-of-thought*) adaptadas ao domínio jurídico em português brasileiro;

d) Implementar um pipeline de geração automatizada de três tipos de documentos jurídicos: reclamação administrativa ao PROCON, petição inicial para Juizado Especial Cível e notificação extrajudicial;

e) Avaliar empiricamente o sistema sob duas perspectivas:
   - **Técnica:** precisão na identificação de direitos violados e qualidade do retrieval, com dataset de 50 casos reais anonimizados;
   - **Usabilidade:** aplicação do *System Usability Scale* (SUS) com 8 a 10 usuários do público-alvo.

---

## 4. METODOLOGIA

O trabalho adota abordagem metodológica de pesquisa aplicada, com desenvolvimento iterativo e avaliação empírica. A execução é dividida em seis fases:

**Fase 1 — Fundamentação teórica (2 semanas):** Revisão sistemática da literatura em RAG, Legal AI, acesso à justiça no Brasil e avaliação de sistemas conversacionais.

**Fase 2 — Construção do corpus (2 semanas):** Coleta, limpeza, segmentação (*chunking*) semântica e indexação vetorial do corpus jurídico utilizando ChromaDB e embeddings multilíngues.

**Fase 3 — Motor RAG e raciocínio jurídico (3 semanas):** Implementação do pipeline de recuperação híbrida (semântica + lexical), re-ranking, e prompts de raciocínio jurídico com citação obrigatória de artigos para mitigação de alucinações.

**Fase 4 — Geração documental (2 semanas):** Desenvolvimento de templates parametrizados para os três tipos de documentos, com preenchimento inteligente via LLM e validação estrutural.

**Fase 5 — Interface e integração (2 semanas):** Implementação de interface web responsiva (PWA) com foco em acessibilidade e público não-jurídico.

**Fase 6 — Avaliação empírica (2 semanas):** Execução do protocolo de avaliação técnica e de usabilidade; análise estatística dos resultados.

### 4.1 Stack Tecnológico

- **Backend:** Python 3.11+, FastAPI, PostgreSQL, LangChain
- **IA e RAG:** Claude 3.5 Sonnet (API), ChromaDB, sentence-transformers (`multilingual-e5-large`), rank-bm25
- **Frontend:** React 18, TypeScript, TailwindCSS
- **Geração documental:** python-docx, WeasyPrint, Jinja2
- **Fontes de dados:** LexML Brasil, Planalto.gov.br

---

## 5. ESCOPO DELIMITADO

### Dentro do escopo

Direito do Consumidor (integral); Direito Trabalhista (subset: demissão, FGTS, horas extras, aviso prévio, férias e 13º); três tipos de documentos jurídicos; interface web funcional; avaliação com dataset de 50 casos e SUS.

### Fora do escopo (trabalhos futuros)

Demais áreas do direito (família, penal, tributário); integração com sistemas de e-protocolo do judiciário; aplicativos móveis nativos; legislação estadual e municipal em escala nacional; substituição de assistência jurídica em causas complexas.

---

## 6. CONSIDERAÇÕES ÉTICAS E LEGAIS

O sistema proposto **não configura exercício de advocacia** nos termos da Lei 8.906/1994, atuando como ferramenta informativa e auxiliar, análoga a portais de informação de saúde pública. A interface exibe, de forma permanente e visível, aviso legal esclarecendo a natureza educativa do sistema e a recomendação de consulta a advogado ou Defensoria Pública em casos complexos.

O tratamento de dados pessoais observa os princípios da Lei Geral de Proteção de Dados (Lei 13.709/2018), com minimização de coleta, armazenamento efêmero e consentimento explícito do usuário.

A validação jurídica dos documentos gerados será conduzida em parceria com um profissional da área do Direito (a ser identificado), de modo a garantir a conformidade processual das peças produzidas pelo sistema.

---

## 7. CRONOGRAMA

O trabalho será executado em 13 semanas, com carga média de 20 horas semanais:

| Semana | Atividade Principal |
|--------|---------------------|
| 1 | Revisão bibliográfica e fundamentação |
| 2 | Setup do ambiente e definição arquitetural |
| 3 | Pipeline de ingestão do corpus jurídico |
| 4 | Indexação vetorial e busca |
| 5 | Motor RAG — versão inicial |
| 6 | Motor RAG — busca híbrida e re-ranking |
| 7 | Camada conversacional e gerenciamento de contexto |
| 8 | Geração de documentos jurídicos |
| 9 | Interface web e integração |
| 10 | Testes e refinamento |
| 11 | Avaliação empírica e coleta de métricas |
| 12 | Análise de resultados e escrita (cap. 3, 4, 5) |
| 13 | Redação final e preparação da defesa |

---

## 8. CONTRIBUIÇÕES ESPERADAS

### 8.1 Contribuições técnico-científicas

- Construção e disponibilização de um corpus jurídico brasileiro estruturado para sistemas RAG;
- Documentação empírica de estratégias de chunking, busca e prompting eficazes para raciocínio jurídico em PT-BR;
- Arquitetura replicável para sistemas de *Legal AI* orientados ao cidadão;
- Dataset de avaliação com 50 casos reais anonimizados, utilizável por pesquisas futuras.

### 8.2 Contribuições sociais

- Ferramenta de primeiro acesso à justiça escalável, com custo marginal desprezível por atendimento;
- Potencial de atendimento complementar ao serviço da Defensoria Pública, especialmente em comarcas sem cobertura;
- Redução da assimetria informacional entre cidadãos e instituições jurídicas.

---

## 9. REFERÊNCIAS INICIAIS

BROOKE, J. SUS: A quick and dirty usability scale. In: JORDAN, P. W. et al. (Eds.). **Usability Evaluation in Industry**. London: Taylor & Francis, 1996.

CAPPELLETTI, M.; GARTH, B. **Acesso à Justiça**. Porto Alegre: Sergio Antonio Fabris Editor, 1988.

DEFENSORIA PÚBLICA DA UNIÃO. **Pesquisa Nacional da Defensoria Pública 2022**. Brasília, 2022.

IZACARD, G.; GRAVE, E. Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering. **Proceedings of the 16th Conference of the European Chapter of the Association for Computational Linguistics**, 2021.

KARPUKHIN, V. et al. Dense Passage Retrieval for Open-Domain Question Answering. **Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)**, 2020.

LEWIS, P. et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. **Advances in Neural Information Processing Systems**, v. 33, p. 9459-9474, 2020.

SADEK, M. T. Acesso à justiça: um direito e seus obstáculos. **Revista USP**, n. 101, p. 55-66, 2014.

BRASIL. **Lei nº 8.078, de 11 de setembro de 1990**. Dispõe sobre a proteção do consumidor.

BRASIL. **Decreto-Lei nº 5.452, de 1º de maio de 1943**. Aprova a Consolidação das Leis do Trabalho.

BRASIL. **Lei nº 13.709, de 14 de agosto de 2018**. Lei Geral de Proteção de Dados Pessoais.

---

*Documento elaborado em abril de 2026 como proposta preliminar para o Trabalho de Conclusão do curso de Engenharia de Software.*
