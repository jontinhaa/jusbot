"""Etapa 3 — geração ponta a ponta, query de demissão."""

import os

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv("../.env")

from src.generation.generate import generate_answer  # noqa: E402

QUERY = "fui demitido sem justa causa, tenho direito a quê?"

db_url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(db_url)
emb_model = SentenceTransformer("intfloat/multilingual-e5-large")

with Session(engine) as session:
    result = generate_answer(QUERY, session, emb_model, k=8)

print("=" * 70)
print("RESPOSTA GERADA")
print("=" * 70)
print(result.answer)
print()
print("=" * 70)
print("DISPOSITIVOS PASSADOS AO MODELO")
print("=" * 70)
for i, c in enumerate(result.chunks, 1):
    print(f"[{i}] {c.endereco}")
    if c.ancestrais:
        print(f"     contexto pai: {c.ancestrais[-1].texto[:120]}...")
    print(f"     {c.texto[:200]}{'...' if len(c.texto) > 200 else ''}")
    print()
