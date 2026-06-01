"""extensoes + tabelas documents e chunks (croqui v2)

Revision ID: 0001
Revises:
Create Date: 2026-06-01
"""

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Extensões (idempotente; init_db.sql já cria, mas a migration
    # garante que qualquer ambiente sem o init script funcione)
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ------------------------------------------------------------------
    # Tabela: documents
    # Armazena os metadados de cada norma ingerida (CDC, CLT, etc.)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE documents (
            id               SERIAL       PRIMARY KEY,
            codigo           VARCHAR(50)  NOT NULL,
            tipo_norma       VARCHAR(30)  NOT NULL,
            numero           VARCHAR(20)  NOT NULL,
            ano              INTEGER      NOT NULL,
            titulo_oficial   TEXT         NOT NULL,
            ementa           TEXT,
            area_juridica    VARCHAR(20)  NOT NULL,
            data_assinatura  DATE,
            data_vigencia    DATE,
            data_revogacao   DATE,
            fonte_url        TEXT         NOT NULL,
            hash_html_bruto  VARCHAR(64)  NOT NULL,
            data_ingestao    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            observacao       TEXT,

            CONSTRAINT uq_documents_codigo
                UNIQUE (codigo),
            CONSTRAINT ck_documents_tipo_norma
                CHECK (tipo_norma IN ('lei', 'decreto-lei')),
            CONSTRAINT ck_documents_area_juridica
                CHECK (area_juridica IN ('consumidor', 'trabalho'))
        )
    """
    )

    op.execute("CREATE INDEX ix_documents_area_juridica ON documents (area_juridica)")

    # ------------------------------------------------------------------
    # Tabela: chunks
    # Cada dispositivo legal (artigo, parágrafo, inciso, alínea, item)
    # conforme LC 95/1998 — ADR-009. Embedding populado em batch.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE chunks (
            id                   SERIAL      PRIMARY KEY,
            document_id          INTEGER     NOT NULL,
            parent_chunk_id      INTEGER,
            tipo                 VARCHAR(20) NOT NULL,
            numero               VARCHAR(20) NOT NULL,
            caminho_hierarquico  JSONB,
            texto                TEXT        NOT NULL,
            tamanho_chunk        INTEGER     GENERATED ALWAYS AS (length(texto)) STORED,
            posicao_ordem        INTEGER     NOT NULL,
            embedding            vector(1024),
            alterado_por         JSONB,
            metadata             JSONB,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT fk_chunks_document_id
                FOREIGN KEY (document_id)
                REFERENCES documents (id) ON DELETE CASCADE,
            CONSTRAINT fk_chunks_parent_chunk_id
                FOREIGN KEY (parent_chunk_id)
                REFERENCES chunks (id) ON DELETE CASCADE,
            CONSTRAINT ck_chunks_tipo
                CHECK (tipo IN ('artigo', 'paragrafo', 'inciso', 'alinea', 'item'))
        )
    """
    )

    # Cobre document_id sozinho e o par (document_id, posicao_ordem)
    op.execute("CREATE INDEX ix_chunks_document_posicao ON chunks (document_id, posicao_ordem)")
    op.execute("CREATE INDEX ix_chunks_parent_chunk_id ON chunks (parent_chunk_id)")
    op.execute("CREATE INDEX ix_chunks_tipo ON chunks (tipo)")

    # GIN para busca em JSONB do caminho hierárquico — ADR-008
    op.execute("CREATE INDEX ix_chunks_caminho_gin ON chunks USING GIN (caminho_hierarquico)")

    # GIN trigram para busca lexical híbrida (BM25-like) — pg_trgm
    op.execute("CREATE INDEX ix_chunks_texto_trgm ON chunks USING GIN (texto gin_trgm_ops)")

    # HNSW parcial: ignora linhas sem embedding ainda — ADR-004/croqui v2
    op.execute(
        """
        CREATE INDEX ix_chunks_embedding_hnsw
        ON chunks USING hnsw (embedding vector_cosine_ops)
        WHERE embedding IS NOT NULL
    """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chunks   CASCADE")
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
