"""
Validação ETAPA 1 — Busca semântica e lexical isoladas.

Uso:
    python -m src.rag.validate_etapa1
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Força UTF-8 no stdout (Windows usa cp1252 por padrão)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.rag.retrieval import ChunkResult, search_lexical, search_semantic  # noqa: E402

QUERY = "fui demitido sem justa causa, tenho direito a quê?"
K = 5
PREVIEW = 130


def clip(text: str, n: int = PREVIEW) -> str:
    t = text.strip().replace("\n", " ")
    return (t[:n] + "…") if len(t) > n else t


def print_list(title: str, elapsed: float, results: list[ChunkResult]) -> None:
    print(f"\n{'═' * 74}")
    print(f"  {title}  [{elapsed:.2f}s]")
    print(f"{'═' * 74}")
    if not results:
        print("  (nenhum resultado)")
        return
    for r in results:
        print(
            f"\n  #{r.rank}  id={r.chunk_id}  score={r.score:.4f}"
            f"  [{r.area_juridica}]  parent_id={r.parent_chunk_id}"
        )
        print(f"  {r.doc_titulo}")
        print(f"  tipo={r.tipo}  numero={r.numero}")
        print(f"  ↳ {clip(r.texto)}")


def main() -> None:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        print("ERRO: DATABASE_URL não definida.", file=sys.stderr)
        sys.exit(1)

    db_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(db_url, echo=False)

    print("Carregando intfloat/multilingual-e5-large...", flush=True)
    t0 = time.time()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("intfloat/multilingual-e5-large")
    print(f"Modelo pronto em {time.time() - t0:.1f}s\n", flush=True)

    print(f'Query : "{QUERY}"')
    print(f"K     : {K}")

    with Session(engine) as session:
        t = time.time()
        sem = search_semantic(session, model, QUERY, k=K)
        elapsed_sem = time.time() - t

        t = time.time()
        lex = search_lexical(session, QUERY, k=K)
        elapsed_lex = time.time() - t

    print_list("SEMÂNTICA  (pgvector cosseno)", elapsed_sem, sem)
    print_list("LEXICAL    (pg_trgm word_similarity)", elapsed_lex, lex)

    sem_ids = {r.chunk_id for r in sem}
    lex_ids = {r.chunk_id for r in lex}

    print(f"\n{'─' * 74}")
    print(f"  Interseção (em ambas)  : {sorted(sem_ids & lex_ids) or '—'}")
    print(f"  Só semântica           : {sorted(sem_ids - lex_ids) or '—'}")
    print(f"  Só lexical             : {sorted(lex_ids - sem_ids) or '—'}")
    print(f"{'─' * 74}\n")


if __name__ == "__main__":
    main()
