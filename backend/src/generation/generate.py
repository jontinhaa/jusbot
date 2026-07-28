"""Geração de resposta jurídica — JusBot.

Função pública: generate_answer(query, session, emb_model, ...) -> GenerationResult

Fluxo por turno:
  1. reformular_pergunta(query, historico, llm) → query_busca
  2. RAG com query_busca
  3. build_prompt(query_ORIGINAL, chunks) → system + user_message
  4. messages = histórico como texto puro + user_message do turno atual
  5. LLM gera a resposta
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.generation.client import _MODEL, get_client
from src.generation.prompt import build_prompt
from src.generation.reformulador import reformular_pergunta
from src.rag.retrieval import ContextualChunk, build_context, search_hybrid

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    query: str
    query_busca: str  # pergunta usada no RAG (reformulada ou igual à original)
    answer: str
    chunks: list[ContextualChunk]


def _historico_para_messages(historico: list[dict[str, str]]) -> list[dict[str, str]]:
    """Converte histórico interno → formato messages da API Anthropic.

    Injeta APENAS texto puro. O bloco DISPOSITIVOS LEGAIS de turnos anteriores
    nunca é reinjetado — cada resposta se fundamenta só nos chunks deste turno
    (ADR-013).
    """
    messages = []
    for entrada in historico:
        role = "user" if entrada["papel"] == "user" else "assistant"
        messages.append({"role": role, "content": entrada["texto"]})
    return messages


def generate_answer(
    query: str,
    session: Session,
    emb_model: object,
    k: int = 8,
    historico: list[dict[str, str]] | None = None,
) -> GenerationResult:
    """Retrieval → reformulação → prompt → geração. Retorna resposta + chunks usados.

    Args:
        query: Pergunta bruta do usuário no turno atual.
        session: Sessão SQLAlchemy.
        emb_model: Modelo sentence-transformers já carregado.
        k: Número de dispositivos a recuperar.
        historico: Turnos anteriores [{"papel": "user"|"assistant", "texto": str}].
                   Default vazio — compatível com a rota /pergunta existente.
    """
    if historico is None:
        historico = []

    # Client criado uma vez; reutilizado na reformulação e na geração
    client = get_client()

    # 1. Reformula apenas se há histórico; primeiro turno passa direto
    query_busca = reformular_pergunta(query, historico, client)

    # 2. RAG com a pergunta reformulada (melhor recall em acompanhamentos)
    items = search_hybrid(session, emb_model, query_busca, k=k)
    chunks = build_context(session, items)

    # 3. Prompt usa a pergunta ORIGINAL — é o que o usuário quis perguntar
    system_prompt, user_message = build_prompt(query, chunks)

    # 4. Histórico como texto puro + turno atual com dispositivos
    messages = _historico_para_messages(historico)
    messages.append({"role": "user", "content": user_message})

    # 5. Geração
    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )

    return GenerationResult(
        query=query,
        query_busca=query_busca,
        answer=response.content[0].text,
        chunks=chunks,
    )
