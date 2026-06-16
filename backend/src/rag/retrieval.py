"""
Motor de retrieval do JusBot — Semana 5.

Funções públicas:
    search_semantic(session, model, query, k, area) -> list[ChunkResult]
    search_lexical(session, query, k, area)          -> list[ChunkResult]
    search_hybrid(session, model, query, k, area)    -> list[HybridItem]
    build_context(session, items)                    -> list[ContextualChunk]
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

# ─── Diplomas conhecidos (codigo → abreviação) ───────────────────────────────

_CODIGOS_CONHECIDOS: dict[str, str] = {
    "lei-8078-1990": "CDC",
    "decreto-lei-5452-1943": "CLT",
}


# ─── Tipos de saída ──────────────────────────────────────────────────────────


@dataclass
class ChunkResult:
    """Resultado bruto de search_semantic ou search_lexical."""

    chunk_id: int
    tipo: str
    numero: str
    texto: str
    parent_chunk_id: int | None
    area_juridica: str
    doc_titulo: str
    doc_codigo: str
    doc_numero: str
    doc_ano: int
    doc_tipo_norma: str
    score: float
    rank: int  # posição 1-based na lista de origem


@dataclass
class HybridItem:
    """Chunk após fusão RRF, com proveniência das listas de origem."""

    chunk_id: int
    tipo: str
    numero: str
    texto: str
    parent_chunk_id: int | None
    area_juridica: str
    doc_titulo: str
    doc_codigo: str
    doc_numero: str
    doc_ano: int
    doc_tipo_norma: str
    score_rrf: float
    fontes: list[str]  # ['vetorial'] | ['lexical'] | ['vetorial', 'lexical']


@dataclass
class Ancestor:
    tipo: str
    numero: str
    texto: str


@dataclass
class ContextualChunk:
    """Chunk com contexto hierárquico montado, pronto para o LLM."""

    chunk_id: int
    tipo: str
    numero: str
    texto: str
    endereco: str  # ex: "CLT, Art. 477, § 1º"
    documento: str  # título completo do diploma legal
    area_juridica: str
    ancestrais: list[Ancestor]
    score_rrf: float
    fontes: list[str]


# ─── Helpers internos ────────────────────────────────────────────────────────


def _vec_literal(vec: list[float]) -> str:
    """Formata vetor float como literal PostgreSQL '[...]'::vector."""
    return "'[" + ",".join(f"{x:.8f}" for x in vec) + "]'::vector"


def _tipo_label(tipo: str, numero: str) -> str:
    if tipo == "artigo":
        return f"Art. {numero}"
    if tipo == "paragrafo":
        return "§ único" if numero == "único" else f"§ {numero}º"
    if tipo == "inciso":
        return f"Inciso {numero}"
    if tipo == "alinea":
        return f"alínea {numero}"
    if tipo == "item":
        return f"item {numero}"
    return f"{tipo} {numero}"


def _doc_short(codigo: str, tipo_norma: str, numero: str, ano: int) -> str:
    if codigo in _CODIGOS_CONHECIDOS:
        return _CODIGOS_CONHECIDOS[codigo]
    labels = {"lei": "Lei", "decreto-lei": "Decreto-Lei"}
    prefix = labels.get(tipo_norma, tipo_norma.title())
    return f"{prefix} {numero}/{ano}"


def _row_to_chunk_result(r: Any, rank: int) -> ChunkResult:
    return ChunkResult(
        chunk_id=r["chunk_id"],
        tipo=r["tipo"],
        numero=r["numero"],
        texto=r["texto"],
        parent_chunk_id=r["parent_chunk_id"],
        area_juridica=r["area_juridica"],
        doc_titulo=r["doc_titulo"],
        doc_codigo=r["doc_codigo"],
        doc_numero=r["doc_numero"],
        doc_ano=r["doc_ano"],
        doc_tipo_norma=r["doc_tipo_norma"],
        score=float(r["score"]),
        rank=rank,
    )


# ─── Busca semântica ─────────────────────────────────────────────────────────


def search_semantic(
    session: Session,
    model: Any,
    query: str,
    k: int = 5,
    area: str | None = None,
) -> list[ChunkResult]:
    """Busca vetorial por cosseno via pgvector (índice HNSW).

    Prefixo 'query: ' é obrigatório para intfloat/multilingual-e5-large.
    """
    query_vec = model.encode(f"query: {query}", normalize_embeddings=True).tolist()
    vec_lit = _vec_literal(query_vec)
    area_filter = "AND d.area_juridica = :area" if area else ""

    sql = text(
        f"""
        SELECT
            c.id               AS chunk_id,
            c.tipo,
            c.numero,
            c.texto,
            c.parent_chunk_id,
            d.area_juridica,
            d.titulo_oficial   AS doc_titulo,
            d.codigo           AS doc_codigo,
            d.numero           AS doc_numero,
            d.ano              AS doc_ano,
            d.tipo_norma       AS doc_tipo_norma,
            1 - (c.embedding <=> {vec_lit}) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
          {area_filter}
        ORDER BY c.embedding <=> {vec_lit}
        LIMIT :k
    """
    )

    params: dict[str, Any] = {"k": k}
    if area:
        params["area"] = area

    rows = session.execute(sql, params).mappings().all()
    return [_row_to_chunk_result(r, i + 1) for i, r in enumerate(rows)]


# ─── Busca lexical ───────────────────────────────────────────────────────────


def search_lexical(
    session: Session,
    query: str,
    k: int = 5,
    area: str | None = None,
) -> list[ChunkResult]:
    """Busca lexical por trigramas via pg_trgm (word_similarity).

    word_similarity(q, t) mede sobreposição de trigramas de q com a melhor
    substring contígua de t — mais robusto que similarity() para queries curtas
    sobre textos longos (artigos jurídicos).
    """
    area_filter = "WHERE d.area_juridica = :area" if area else ""

    sql = text(
        f"""
        SELECT
            chunk_id, tipo, numero, texto, parent_chunk_id,
            area_juridica, doc_titulo, doc_codigo, doc_numero,
            doc_ano, doc_tipo_norma, score
        FROM (
            SELECT
                c.id               AS chunk_id,
                c.tipo,
                c.numero,
                c.texto,
                c.parent_chunk_id,
                d.area_juridica,
                d.titulo_oficial   AS doc_titulo,
                d.codigo           AS doc_codigo,
                d.numero           AS doc_numero,
                d.ano              AS doc_ano,
                d.tipo_norma       AS doc_tipo_norma,
                word_similarity(:query, c.texto) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            {area_filter}
        ) sub
        WHERE score > 0.05
        ORDER BY score DESC
        LIMIT :k
    """
    )

    params: dict[str, Any] = {"query": query, "k": k}
    if area:
        params["area"] = area

    rows = session.execute(sql, params).mappings().all()
    return [_row_to_chunk_result(r, i + 1) for i, r in enumerate(rows)]


# ─── Reciprocal Rank Fusion ───────────────────────────────────────────────────


def _rrf(
    lists: list[tuple[list[ChunkResult], str]],
    k_const: int = 60,
) -> list[tuple[ChunkResult, float, list[str]]]:
    """Funde listas de resultados por Reciprocal Rank Fusion.

    score_rrf = sum(1 / (k_const + rank)) sobre todas as listas em que o chunk aparece.
    k_const=60 é o padrão da literatura (Cormack et al., 2009).

    Args:
        lists: [(result_list, source_name), ...]
    Returns:
        [(chunk_result, score_rrf, [sources]), ...] ordenado por score_rrf desc.
    """
    scores: dict[int, float] = {}
    sources: dict[int, list[str]] = {}
    best: dict[int, ChunkResult] = {}

    for result_list, fonte in lists:
        for chunk in result_list:
            cid = chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k_const + chunk.rank)
            sources.setdefault(cid, []).append(fonte)
            best[cid] = chunk

    ranked = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [(best[cid], scores[cid], sources[cid]) for cid in ranked]


# ─── Busca híbrida ───────────────────────────────────────────────────────────


def search_hybrid(
    session: Session,
    model: Any,
    query: str,
    k: int = 5,
    area: str | None = None,
) -> list[HybridItem]:
    """Busca híbrida: semântica + lexical fundidas por RRF.

    Cada sub-busca usa pool = max(k*2, 10) candidatos para dar margem à fusão.
    Filtro area é opcional — None = sem filtro (vetor decide a área sozinho).
    """
    pool = max(k * 2, 10)
    sem = search_semantic(session, model, query, k=pool, area=area)
    lex = search_lexical(session, query, k=pool, area=area)

    fused = _rrf([(sem, "vetorial"), (lex, "lexical")])

    return [
        HybridItem(
            chunk_id=chunk.chunk_id,
            tipo=chunk.tipo,
            numero=chunk.numero,
            texto=chunk.texto,
            parent_chunk_id=chunk.parent_chunk_id,
            area_juridica=chunk.area_juridica,
            doc_titulo=chunk.doc_titulo,
            doc_codigo=chunk.doc_codigo,
            doc_numero=chunk.doc_numero,
            doc_ano=chunk.doc_ano,
            doc_tipo_norma=chunk.doc_tipo_norma,
            score_rrf=score_rrf,
            fontes=fontes,
        )
        for chunk, score_rrf, fontes in fused[:k]
    ]


# ─── Montagem de contexto ────────────────────────────────────────────────────


def build_context(session: Session, items: list[HybridItem]) -> list[ContextualChunk]:
    """Enriquece cada HybridItem com contexto hierárquico dos ancestrais.

    CTE recursiva sobe a árvore via parent_chunk_id até a raiz.
    O embedding permanece intocado — enriquecimento acontece só na saída.
    """
    if not items:
        return []

    chunk_ids = [item.chunk_id for item in items]

    sql = text(
        """
            WITH RECURSIVE tree AS (
                SELECT
                    c.id                 AS id,
                    c.parent_chunk_id,
                    c.tipo,
                    c.numero,
                    c.texto,
                    c.id                 AS origin_chunk_id,
                    0                    AS depth
                FROM chunks c
                WHERE c.id IN :chunk_ids

                UNION ALL

                SELECT
                    p.id,
                    p.parent_chunk_id,
                    p.tipo,
                    p.numero,
                    p.texto,
                    tree.origin_chunk_id,
                    tree.depth + 1
                FROM chunks p
                JOIN tree ON p.id = tree.parent_chunk_id
            )
            SELECT
                origin_chunk_id,
                id,
                tipo,
                numero,
                texto,
                depth
            FROM tree
            ORDER BY origin_chunk_id, depth DESC
        """
    ).bindparams(bindparam("chunk_ids", expanding=True))

    rows = session.execute(sql, {"chunk_ids": chunk_ids}).mappings().all()

    by_origin: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_origin[int(r["origin_chunk_id"])].append(dict(r))

    result: list[ContextualChunk] = []
    for item in items:
        chain = by_origin.get(item.chunk_id, [])
        # chain: depth DESC → [raiz, ..., pai, próprio chunk]

        ancestrais = [
            Ancestor(tipo=node["tipo"], numero=node["numero"], texto=node["texto"])
            for node in chain
            if int(node["id"]) != item.chunk_id
        ]

        doc_short = _doc_short(item.doc_codigo, item.doc_tipo_norma, item.doc_numero, item.doc_ano)
        path_parts = [_tipo_label(node["tipo"], node["numero"]) for node in chain]
        endereco = f"{doc_short}, {', '.join(path_parts)}" if path_parts else doc_short

        result.append(
            ContextualChunk(
                chunk_id=item.chunk_id,
                tipo=item.tipo,
                numero=item.numero,
                texto=item.texto,
                endereco=endereco,
                documento=item.doc_titulo,
                area_juridica=item.area_juridica,
                ancestrais=ancestrais,
                score_rrf=item.score_rrf,
                fontes=item.fontes,
            )
        )

    return result
