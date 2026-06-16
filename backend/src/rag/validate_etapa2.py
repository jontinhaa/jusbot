"""
Validação ETAPA 2 — Fusão RRF (search_hybrid).

Uso:
    python -m src.rag.validate_etapa2
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.rag.retrieval import search_hybrid, search_lexical, search_semantic  # noqa: E402

QUERY = "fui demitido sem justa causa, tenho direito a quê?"
K = 5
PREVIEW = 130


def clip(text: str, n: int = PREVIEW) -> str:
    t = text.strip().replace("\n", " ")
    return (t[:n] + "…") if len(t) > n else t


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
    print(f"K     : {K}  (pool sub-buscas: {max(K * 2, 10)})")

    with Session(engine) as session:
        # Sub-buscas com pool=10 para mostrar o que entrou no RRF
        pool = max(K * 2, 10)
        sem = search_semantic(session, model, QUERY, k=pool)
        lex = search_lexical(session, QUERY, k=pool)

        # Fusão híbrida final
        t = time.time()
        hybrid = search_hybrid(session, model, QUERY, k=K)
        elapsed = time.time() - t

    # Índices de posição nas sub-buscas para exibição
    sem_rank = {r.chunk_id: r.rank for r in sem}
    lex_rank = {r.chunk_id: r.rank for r in lex}

    print(f"\n{'═' * 74}")
    print(f"  HÍBRIDO  (RRF k_const=60)  [{elapsed:.2f}s]")
    print(f"{'═' * 74}")

    for i, item in enumerate(hybrid, 1):
        rank_sem = sem_rank.get(item.chunk_id)
        rank_lex = lex_rank.get(item.chunk_id)

        # Score RRF calculado manualmente para conferência
        rrf_contrib = []
        if rank_sem:
            rrf_contrib.append(f"vetorial(#{rank_sem})=1/{60+rank_sem}={1/(60+rank_sem):.5f}")
        if rank_lex:
            rrf_contrib.append(f"lexical(#{rank_lex})=1/{60+rank_lex}={1/(60+rank_lex):.5f}")

        fontes_str = " + ".join(item.fontes)
        print(
            f"\n  #{i}  id={item.chunk_id}  score_rrf={item.score_rrf:.6f}"
            f"  [{item.area_juridica}]  fontes=[{fontes_str}]"
        )
        print(f"  {item.doc_titulo}")
        print(f"  tipo={item.tipo}  numero={item.numero}  parent_id={item.parent_chunk_id}")
        print(f"  RRF: {' + '.join(rrf_contrib)}")
        print(f"  ↳ {clip(item.texto)}")

    print(f"\n{'─' * 74}")
    both = [i for i in hybrid if len(i.fontes) == 2]
    only_sem = [i for i in hybrid if i.fontes == ["vetorial"]]
    only_lex = [i for i in hybrid if i.fontes == ["lexical"]]
    print(f"  Em ambas as listas  : {[i.chunk_id for i in both] or '—'}")
    print(f"  Só vetorial         : {[i.chunk_id for i in only_sem] or '—'}")
    print(f"  Só lexical          : {[i.chunk_id for i in only_lex] or '—'}")
    print(f"{'─' * 74}\n")


if __name__ == "__main__":
    main()
