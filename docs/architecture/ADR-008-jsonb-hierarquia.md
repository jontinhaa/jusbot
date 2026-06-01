# ADR-008 — Hierarquia como `JSONB` (LTREE adiado para trabalho futuro)

**Status:** Aceito
**Data:** maio/2026
**Decisores:** Jhonatan, Diogo · revisão Prof. Tarcísio Lemos
**Relacionado:** ADR-005, ADR-006

## Contexto

O caminho estrutural de cada chunk (Título → Capítulo → Seção → Artigo, relevante sobretudo na CLT) precisa ser representado. O v1 adotou `caminho_hierarquico` como `JSONB`, listando LTREE como alternativa em aberto (Pergunta 1).

`JSONB` é um tipo de dado: armazena o **endereço estrutural** do chunk como objeto (`{"capitulo":"I","artigo":"58-A"}`), com flexibilidade de profundidade por linha e suporte a índice GIN. Não representa uma árvore navegável — é um campo de endereço.

`LTREE` é uma extensão dedicada a caminhos de árvore (`capitulo_i.artigo_58a`), com operadores nativos de ancestralidade/descendência (`@>`, `<@`). É mais expressivo para consultas hierárquicas em SQL, ao custo de uma extensão adicional no setup.

## Decisão

Manter `caminho_hierarquico` como `JSONB` para o MVP. Registrar a migração para LTREE como possibilidade de trabalho futuro, caso surjam consultas hierárquicas frequentes em SQL.

**Razão central:** no JusBot, a busca é feita pelo índice vetorial (`pgvector`/HNSW), não por navegação hierárquica em SQL. A hierarquia serve a dois propósitos — filtro auxiliar (por área/documento) e **exibição do endereço** do chunk ao usuário ("Art. 58-A, §1º") — nenhum dos quais usa os operadores de árvore do LTREE. As poucas consultas de descendência concebíveis (ex.: "todos os chunks abaixo do Capítulo V") já são atendidas pela CTE recursiva sobre `parent_chunk_id` (ADR-006). Adicionar a extensão LTREE seria custo de setup e aprendizado sem contrapartida de uso, agravando o risco de reprodutibilidade na avaliação empírica (Semana 11).

## Consequências

**Positivas:** zero dependências extras além de `pgvector` e `pg_trgm`; flexibilidade de profundidade sem colunas vazias; índice GIN cobre busca por chave/valor (`caminho_hierarquico @> '{"artigo":"58-A"}'`).

**Negativas / trade-offs:** consultas de ancestralidade em JSONB são mais verbosas que no LTREE — mitigado por elas serem raras e cobertas pela CTE recursiva.

**Notas de implementação:** se uma consulta por caminho exato (ex.: `capitulo = 'V'`) se tornar frequente, considerar índice funcional `((caminho_hierarquico->>'capitulo'))` antes de cogitar LTREE. Manter o GIN como índice padrão do campo.
