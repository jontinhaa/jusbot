"""
Preparação de texto para embedding com intfloat/multilingual-e5-large.

O modelo e5 exige prefixos distintos:
  "passage: " — para documentos indexados (este módulo)
  "query: "   — para perguntas em tempo de retrieval (RAG)

build_embedding_text() é o ÚNICO ponto que monta o texto de um chunk
para embedding. Trocar a estratégia (ex: enriquecer com contexto
hierárquico) significa editar apenas esta função.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.db.models import Chunk


def build_embedding_text(chunk: Chunk) -> str:
    return f"passage: {chunk.texto}"
