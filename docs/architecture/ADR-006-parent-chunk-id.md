# ADR-006 — Contexto hierárquico via `parent_chunk_id` (sem duplicação de texto)

**Status:** Aceito
**Data:** maio/2026
**Decisores:** Jhonatan, Diogo · revisão Prof. Tarcísio Lemos
**Relacionado:** ADR-005 (chunking hierárquico), ADR-008

## Contexto

No `croqui_banco_v1`, a tabela `chunks` tinha a coluna `texto_pai` (TEXT), que armazenava o texto do chunk ancestral em cada filho — resolvendo o problema de chunks soltos perderem contexto jurídico, mas duplicando conteúdo. O texto de um artigo aparecia repetido em todos os seus parágrafos/incisos filhos.

Isso viola a 3ª forma normal e cria risco de inconsistência: se o texto de um artigo for reprocessado, as cópias nos filhos podem ficar defasadas. Para um artigo com 10 parágrafos, o texto do artigo é gravado 11 vezes.

A revisão (Pergunta 3) propôs três opções: (A) manter `texto_pai`; (B) `parent_chunk_id` + JOIN; (C) sem contexto pai. Recomendou (B), sugerindo adicionalmente uma **view materializada** para pré-computar o `texto_pai`.

## Decisão

Adotar a **opção B**: substituir `texto_pai` por uma FK auto-referencial `parent_chunk_id INTEGER REFERENCES chunks(id) ON DELETE CASCADE`. O texto do pai é obtido em tempo de retrieval via JOIN ou CTE recursiva (`WITH RECURSIVE`), apenas quando o resultado vai ser exibido — não durante a busca vetorial.

**Decidimos não adotar a view materializada** sugerida na revisão. Uma view materializada é uma cópia física do JOIN persistida em disco, que exige `REFRESH` manual a cada alteração de dados — reintroduzindo a duplicação que o `parent_chunk_id` elimina, em outro lugar. Ela se justifica quando o JOIN é caro e executado com altíssima frequência; aqui o JOIN ocorre sobre ~1.800 linhas e somente na montagem da resposta (operação rara e barata). Adicioná-la agora é otimização prematura. Se um profiling futuro demonstrar que o JOIN é gargalo real, a view pode ser introduzida sem alterar o schema base.

## Consequências

**Positivas:** elimina redundância e o risco de inconsistência; permite reconstruir a árvore completa (alínea → inciso → parágrafo → artigo) via CTE recursiva; embedding continua sendo gerado apenas sobre `texto`; mantém aberta a decisão de *quanto* contexto do pai enviar ao LLM (texto completo, resumo ou só o endereço), que passa a ser decisão de aplicação, não de schema.

**Negativas / trade-offs:** reconstruir contexto exige JOIN/recursão em tempo de retrieval (custo baixo para o volume); a profundidade da CLT (até 4 níveis) torna a reconstrução uma CTE recursiva, não um JOIN simples.

**Notas de implementação:** índice em `parent_chunk_id` para busca de filhos; cuidado com a ordem de inserção no parser (o pai precisa existir antes do filho receber a FK) — inserir em ordem topológica (artigo antes de parágrafo) ou fazer duas passadas.
