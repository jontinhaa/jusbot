"""
Gera embeddings para todos os chunks com embedding IS NULL.

Uso:
    python -m src.corpus.generate_embeddings [--batch-size N]

Idempotente: se interrompido, rodar de novo retoma de onde parou
(filtra sempre WHERE embedding IS NULL).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.corpus.embeddings import build_embedding_text  # noqa: E402
from src.db.models import Chunk  # noqa: E402


def run(db_url: str, batch_size: int = 32) -> None:
    from sentence_transformers import SentenceTransformer

    print("Carregando intfloat/multilingual-e5-large...", flush=True)
    t_model = time.time()
    model = SentenceTransformer("intfloat/multilingual-e5-large")
    print(f"Modelo pronto em {time.time() - t_model:.1f}s\n", flush=True)

    engine = create_engine(db_url, echo=False)

    with Session(engine) as session:
        total_pending: int = session.execute(
            text("SELECT COUNT(*) FROM chunks WHERE embedding IS NULL")
        ).scalar_one()

        print(f"Chunks com embedding IS NULL : {total_pending}", flush=True)

        if total_pending == 0:
            print("Nada a processar. Saindo.")
            return

        n_batches = (total_pending + batch_size - 1) // batch_size
        print(f"Batches de {batch_size}         : {n_batches}", flush=True)
        print(flush=True)

        processed = 0
        t_start = time.time()

        for batch_num in range(1, n_batches + 1):
            chunks = (
                session.query(Chunk)
                .filter(Chunk.embedding.is_(None))
                .order_by(Chunk.id)
                .limit(batch_size)
                .all()
            )
            if not chunks:
                break

            texts = [build_embedding_text(c) for c in chunks]
            vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

            for chunk, vec in zip(chunks, vectors, strict=False):
                chunk.embedding = vec.tolist()

            session.commit()
            # Libera objetos já commitados da identity map
            session.expunge_all()

            processed += len(chunks)
            elapsed = time.time() - t_start
            rate = processed / elapsed
            eta = (total_pending - processed) / rate if rate > 0 else 0

            print(
                f"batch {batch_num:>4}/{n_batches}"
                f" — {processed:>5}/{total_pending} chunks"
                f" | {rate:>5.1f} chunks/s"
                f" | ETA {eta:>4.0f}s",
                flush=True,
            )

        total_elapsed = time.time() - t_start

        remaining: int = session.execute(
            text("SELECT COUNT(*) FROM chunks WHERE embedding IS NULL")
        ).scalar_one()

        print(flush=True)
        print("=" * 55, flush=True)
        print(f"Total processado : {processed}", flush=True)
        print(f"Tempo total      : {total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)", flush=True)
        print(f"IS NULL restantes: {remaining}", flush=True)
        print("=" * 55, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        print("ERRO: DATABASE_URL não definida.", file=sys.stderr)
        sys.exit(1)

    db_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    run(db_url, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
