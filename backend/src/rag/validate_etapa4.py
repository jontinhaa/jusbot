"""
Validação ETAPA 4 — Pipeline completo com 5 queries de domínios diferentes.

Uso:
    python -m src.rag.validate_etapa4
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

from src.rag.retrieval import ContextualChunk, build_context, search_hybrid  # noqa: E402

K = 5
PREVIEW = 120

QUERIES = [
    ("trabalho", "fui demitido sem justa causa, tenho direito a quê?"),
    ("consumidor", "comprei um produto com defeito, posso devolver?"),
    ("FGTS/trab.", "qual o prazo para sacar o FGTS depois de ser mandado embora?"),
    ("consumidor", "a loja pode cobrar diferente no cartão e no dinheiro?"),
    ("trabalho", "tenho direito a férias proporcionais se peço demissão?"),
]


def clip(text: str, n: int = PREVIEW) -> str:
    t = text.strip().replace("\n", " ")
    return (t[:n] + "…") if len(t) > n else t


def print_query_results(
    qnum: int, label: str, query: str, results: list[ContextualChunk], elapsed: float
) -> None:
    print(f"\n{'═' * 74}")
    print(f"  Q{qnum} [{label}]  {elapsed:.2f}s")
    print(f'  "{query}"')
    print(f"{'═' * 74}")
    for i, c in enumerate(results, 1):
        anc_count = len(c.ancestrais)
        anc_label = (
            f"{anc_count} ancestral{'is' if anc_count != 1 else ''}" if anc_count else "raiz"
        )
        print(
            f"\n  #{i}  {c.endereco}"
            f"  [{c.area_juridica}]  rrf={c.score_rrf:.5f}"
            f"  fontes=[{'+'.join(c.fontes)}]  {anc_label}"
        )
        if c.ancestrais:
            print(f"      pai: {clip(c.ancestrais[-1].texto, 90)}")
        print(f"      ↳  {clip(c.texto)}")


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

    print(f"K={K}, sem filtro de área, pool sub-buscas={max(K*2,10)}")

    with Session(engine) as session:
        for qnum, (label, query) in enumerate(QUERIES, 1):
            t = time.time()
            hybrid = search_hybrid(session, model, query, k=K)
            ctx = build_context(session, hybrid)
            elapsed = time.time() - t
            print_query_results(qnum, label, query, ctx, elapsed)

    print(f"\n{'─' * 74}")
    print("  Fim da validação ETAPA 4. Avalie relevância por query acima.")
    print(f"{'─' * 74}\n")


if __name__ == "__main__":
    main()
