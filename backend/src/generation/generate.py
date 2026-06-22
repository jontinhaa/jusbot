"""Geração de resposta jurídica — JusBot, Semana 6.

Função pública: generate_answer(query, session, emb_model) -> GenerationResult
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.generation.client import _MODEL, get_client
from src.generation.prompt import build_prompt
from src.rag.retrieval import ContextualChunk, build_context, search_hybrid


@dataclass
class GenerationResult:
    query: str
    answer: str
    chunks: list[ContextualChunk]


def generate_answer(
    query: str,
    session: Session,
    emb_model: object,
    k: int = 8,
) -> GenerationResult:
    """Retrieval → prompt → geração. Retorna resposta + chunks usados."""
    items = search_hybrid(session, emb_model, query, k=k)
    chunks = build_context(session, items)

    system_prompt, user_message = build_prompt(query, chunks)

    client = get_client()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return GenerationResult(
        query=query,
        answer=response.content[0].text,
        chunks=chunks,
    )
