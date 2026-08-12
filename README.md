# ⚖️ JusBot — Assistente Inteligente de Direitos do Consumidor e Trabalhistas

> Sistema de consulta jurídica baseado em **RAG (Retrieval-Augmented Generation)** que responde dúvidas sobre direitos do consumidor e trabalhistas em linguagem acessível, fundamentando as respostas em legislação real.

📚 **Projeto de Conclusão de Curso (TCC)** — Bacharelado em Engenharia de Software, Universidade do Estado do Pará (UEPA).

🚧 **Status:** Em desenvolvimento ativo

---

## 🎯 O Problema

Grande parte da população não conhece seus direitos básicos como consumidor ou trabalhador — e a linguagem jurídica é uma barreira real. Consultar um advogado para cada dúvida simples é caro e inacessível para muitos.

O **JusBot** propõe uma ponte: um assistente que entende perguntas em linguagem natural ("meu produto quebrou em 10 dias, tenho direito a troca?") e responde de forma clara, **citando a base legal** que fundamenta a resposta — reduzindo o risco de "alucinação" típico de LLMs puros.

## 💡 A Solução

Em vez de depender apenas do conhecimento interno do modelo de linguagem, o JusBot usa **RAG**: antes de responder, o sistema busca trechos relevantes em uma base de documentos jurídicos (CDC, CLT e afins) e fornece esse contexto ao modelo, garantindo respostas ancoradas na legislação.

## 🏗️ Arquitetura

```
Pergunta do usuário
        │
        ▼
[ Embedding da pergunta ]
        │
        ▼
[ Busca semântica no ChromaDB ] ──► trechos relevantes da legislação
        │
        ▼
[ Montagem do prompt com contexto ]
        │
        ▼
[ LLM (Claude) gera a resposta fundamentada ]
        │
        ▼
Resposta + base legal citada
```

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend / API | Python, FastAPI |
| Base vetorial | ChromaDB |
| Modelo de linguagem | Claude (Anthropic) |
| Frontend | React |
| Técnica central | RAG (Retrieval-Augmented Generation) |

## 🗺️ Roadmap

- [x] Definição da arquitetura RAG
- [x] Estrutura inicial do backend (FastAPI)
- [x] Integração com ChromaDB para busca semântica
- [x] Ingestão e indexação completa da base legal (CDC, CLT)
- [x] Refinamento de prompts para citação consistente da fonte
- [x] Integração completa do frontend React com a API
- [x] Avaliação de qualidade das respostas (precisão jurídica)
- [ ] Deploy de versão demonstrável

## 👥 Autoria

Projeto desenvolvido por **Jhonatan Almeida Alves** e **Diogo Caldeira**, como TCC do curso de Engenharia de Software (UEPA — Campus Paragominas).

---

*Este repositório está em evolução contínua como parte do desenvolvimento do TCC. Sugestões e feedback são bem-vindos.*
