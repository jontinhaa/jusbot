from __future__ import annotations

from datetime import date, datetime
from typing import Any

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(sa.String(50), unique=True)
    tipo_norma: Mapped[str] = mapped_column(sa.String(30))
    numero: Mapped[str] = mapped_column(sa.String(20))
    ano: Mapped[int]
    titulo_oficial: Mapped[str] = mapped_column(sa.Text)
    ementa: Mapped[str | None] = mapped_column(sa.Text)
    area_juridica: Mapped[str] = mapped_column(sa.String(20))
    data_assinatura: Mapped[date | None]
    data_vigencia: Mapped[date | None]
    data_revogacao: Mapped[date | None]
    fonte_url: Mapped[str] = mapped_column(sa.Text)
    hash_html_bruto: Mapped[str] = mapped_column(sa.String(64))
    data_ingestao: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    observacao: Mapped[str | None] = mapped_column(sa.Text)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    chunks: Mapped[list[Chunk]] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(sa.ForeignKey("documents.id", ondelete="CASCADE"))
    parent_chunk_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("chunks.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(sa.String(20))
    numero: Mapped[str] = mapped_column(sa.String(20))
    caminho_hierarquico: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    texto: Mapped[str] = mapped_column(sa.Text)
    # GENERATED ALWAYS AS (length(texto)) STORED — somente leitura via ORM
    tamanho_chunk: Mapped[int] = mapped_column(Computed("length(texto)", persisted=True))
    posicao_ordem: Mapped[int]
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    alterado_por: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # "metadata" é reservado pelo SQLAlchemy — atributo Python usa sufixo _
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    document: Mapped[Document] = relationship("Document", back_populates="chunks")
    parent: Mapped[Chunk | None] = relationship(
        "Chunk", remote_side="Chunk.id", back_populates="children"
    )
    children: Mapped[list[Chunk]] = relationship("Chunk", back_populates="parent")
