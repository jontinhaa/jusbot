"""Compara os dispositivos recuperados para k=5, 8, 10 — sem gerar resposta."""

import os

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv("../.env")

from src.rag.retrieval import build_context, search_hybrid  # noqa: E402

QUERY = "fui demitido sem justa causa, tenho direito a quê?"

db_url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(db_url)
emb_model = SentenceTransformer("intfloat/multilingual-e5-large")

with Session(engine) as session:
    for k in (5, 8, 10):
        items = search_hybrid(session, emb_model, QUERY, k=k)
        chunks = build_context(session, items)
        print(f"\n{'='*60}")
        print(f"k={k}  ({len(chunks)} dispositivos)")
        print(f"{'='*60}")
        for i, c in enumerate(chunks, 1):
            print(f"  [{i:2}] {c.endereco:<40}  rrf={c.score_rrf:.4f}  {c.fontes}")
