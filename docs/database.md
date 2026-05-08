# Documentação do Banco de Dados — JusBot

## Visão Geral

O projeto JusBot utiliza **PostgreSQL 16** com a extensão **pgvector** como banco de dados unificado, responsável por:

- Armazenar e indexar embeddings do corpus jurídico (Camada 1 — Ingestão)
- Executar buscas semânticas e lexicais no RAG (Camada 3 — Recuperação)
- Persistir dados estruturados (usuários, sessões, documentos gerados)
- Conformidade com LGPD: criptografia, auditoria, direitos de acesso

**Decisão arquitetural:** [ADR-004] Migração de ChromaDB para PostgreSQL + pgvector (30/04/2026)

---

## Subindo o Banco

### Pré-requisitos
- Docker e Docker Compose instalados
- Arquivo `.env` configurado na raiz do projeto (template em `.env.example`)

### Comando
```bash
docker-compose up -d
```

Isto vai:
1. Baixar a imagem `pgvector/pgvector:pg16` (se necessário)
2. Criar o container `jusbot-postgres`
3. Executar o script de inicialização (`scripts/init_db.sql`)
4. Expor PostgreSQL na porta 5432
5. Criar um volume persistente para dados

---

## Verificando se está Rodando

```bash
docker-compose ps
```

Resultado esperado:
```
NAME               IMAGE                   STATUS
jusbot-postgres    pgvector/pgvector:pg16  Up (healthy)
```

Ou verifique o healthcheck:
```bash
docker-compose logs postgres
```

Você deve ver:
```
... pg_isready ... accepting connections
```

---

## Conectando via psql

### Direto do host
```bash
psql postgresql://jusbot:jusbot_dev_password@localhost:5432/jusbot_dev
```

### Dentro do container
```bash
docker exec -it jusbot-postgres psql -U jusbot -d jusbot_dev
```

### Verificar que as extensões foram criadas
```sql
SELECT extname FROM pg_extension;
```

Resultado esperado:
```
  extname
-----------
 plpgsql
 vector
 pg_trgm
```

---

## Derrubando o Banco

### Remover container e volumes
```bash
docker-compose down
```

### Remover tudo (incluindo dados persistentes)
**⚠️ CUIDADO — isto deleta os dados!**
```bash
docker-compose down -v
```

---

## Resetando Completamente

Se precisar recriar o banco do zero:
```bash
docker-compose down -v
docker-compose up -d
```

Isto vai:
1. Remover o volume antigo
2. Recriar o banco
3. Re-executar `scripts/init_db.sql`

---

## Variáveis de Ambiente

Configure em `.env` (copie de `.env.example`):

| Variável | Descrição | Default |
|----------|-----------|---------|
| `POSTGRES_USER` | Usuário do banco | `jusbot` |
| `POSTGRES_PASSWORD` | Senha | `jusbot_dev_password` |
| `POSTGRES_DB` | Nome do banco | `jusbot_dev` |
| `DATABASE_URL` | URL de conexão (para ORMs/drivers) | `postgresql://...` |

---

## Dicas

### Performance
- Aumentar `shared_buffers` em produção: adicione ao docker-compose.yml
  ```yaml
  command: -c shared_buffers=256MB
  ```

### Persistência
- Os dados estão em `postgres_data/` (volume Docker)
- Faça backup periódico: `docker exec jusbot-postgres pg_dump -U jusbot -d jusbot_dev > backup.sql`

### Troubleshooting
- **Porta 5432 já em uso:** `docker-compose.yml` pode usar porta diferente
- **Erro de permissão:** garanta que `scripts/init_db.sql` tem permissão de leitura
- **Container não sobe:** verifique logs com `docker-compose logs postgres`

---

**Última atualização:** 2026-05-08
