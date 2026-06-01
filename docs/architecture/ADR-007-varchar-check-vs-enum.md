# ADR-007 — `VARCHAR` + `CHECK` para campos categóricos (em vez de `ENUM`)

**Status:** Aceito
**Data:** maio/2026
**Decisores:** Jhonatan, Diogo · revisão Prof. Tarcísio Lemos
**Aplica-se a:** `documents.tipo_norma`, `documents.area_juridica`

## Contexto

A revisão sugeriu migrar `tipo_norma` e `area_juridica` de `VARCHAR` para `ENUM`, visando integridade referencial e economia de espaço.

`ENUM` no PostgreSQL garante que só valores de uma lista fechada sejam aceitos. Porém, alterar um tipo `ENUM` depois de criado é custoso: adicionar um valor exige `ALTER TYPE ... ADD VALUE` (com restrições, ex.: não pode rodar dentro de certas transações em versões antigas); **remover ou renomear** um valor é ainda mais complicado, exigindo recriar o tipo e atualizar todas as colunas dependentes.

O próprio v1 prevê expansão futura do domínio: `tipo_norma` pode receber `lei-complementar`, `medida-provisoria`; `area_juridica` pode crescer para outras áreas em Trabalhos Futuros.

## Decisão

Manter os campos como `VARCHAR` com constraint `CHECK`:

```sql
tipo_norma   VARCHAR(30) NOT NULL CHECK (tipo_norma IN ('lei','decreto-lei')),
area_juridica VARCHAR(20) NOT NULL CHECK (area_juridica IN ('consumidor','trabalho'))
```

O `CHECK` lista **apenas os valores presentes no corpus atual** — não antecipa valores que ainda não existem (um CHECK que aceita valores nunca usados é uma guarda mais fraca). Expandir o domínio é uma migration de uma linha (`DROP CONSTRAINT` + `ADD CONSTRAINT` com a lista nova), barata e versionada pelo Alembic.

## Consequências

**Positivas:** mesma garantia de integridade do ENUM (rejeita valores fora da lista); expansão trivial via migration, alinhada com a expansão já prevista no projeto; sem dependência de um tipo customizado no dump/restore do banco.

**Negativas / trade-offs:** `VARCHAR` ocupa marginalmente mais espaço que `ENUM` — irrelevante para 5 documentos / ~1.800 chunks; a lista de valores válidos vive na constraint (e nos ADRs), não num tipo nomeado autodescritivo.

**Observação:** esta é uma divergência fundamentada em relação à recomendação da revisão, alinhada e aceita pelo coorientador. O princípio — não introduzir rigidez para um domínio que sabidamente vai crescer — é o mesmo que orienta o ADR-006 (não pagar complexidade que o escopo não pede).
