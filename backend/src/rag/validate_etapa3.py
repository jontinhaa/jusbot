"""
Validação ETAPA 3 — Montagem de contexto com ancestrais (build_context).

Uso:
    python -m src.rag.validate_etapa3
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

QUERY = "fui demitido sem justa causa, tenho direito a quê?"
K = 5
PREVIEW = 150


def clip(text: str, n: int = PREVIEW) -> str:
    t = text.strip().replace("\n", " ")
    return (t[:n] + "…") if len(t) > n else t


def print_contextual(i: int, c: ContextualChunk) -> None:
    print(f"\n{'═' * 74}")
    print(f"  #{i}  chunk_id={c.chunk_id}  score_rrf={c.score_rrf:.6f}  [{c.area_juridica}]")
    print(f"  fontes=[{' + '.join(c.fontes)}]")
    print(f"{'═' * 74}")
    print(f"  Endereço  : {c.endereco}")
    print(f"  Documento : {c.documento}")

    if c.ancestrais:
        print(f"\n  Ancestrais ({len(c.ancestrais)}):")
        for anc in c.ancestrais:
            print(f"    [{anc.tipo} {anc.numero}]  {clip(anc.texto, 100)}")
    else:
        print("\n  Ancestrais: — (chunk é raiz)")

    print("\n  Texto do chunk:")
    print(f"    {clip(c.texto)}")


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
        hybrid = search_hybrid(session, model, QUERY, k=K)

        t = time.time()
        contextuais = build_context(session, hybrid)
        elapsed = time.time() - t

    print(f"\nbuild_context: {elapsed:.3f}s para {len(contextuais)} chunks\n")

    # Mostra os 3 primeiros completos (o usuário pediu 2 ou 3)
    for i, c in enumerate(contextuais[:3], 1):
        print_contextual(i, c)

    print(f"\n{'─' * 74}")
    print(
        f"  Chunks com ancestrais : {sum(1 for c in contextuais if c.ancestrais)}/{len(contextuais)}"
    )
    print(
        f"  Chunks raiz (sem pai) : {sum(1 for c in contextuais if not c.ancestrais)}/{len(contextuais)}"
    )
    print(f"{'─' * 74}\n")


if __name__ == "__main__":
    main()
