"""Preview do prompt de geração — imprime sem chamar o modelo.

Uso: poetry run python preview_prompt.py
"""

import os

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv("../.env")

from src.generation.prompt import build_prompt  # noqa: E402
from src.rag.retrieval import build_context, search_hybrid  # noqa: E402

QUERY = "fui demitido sem justa causa, tenho direito a quê?"

db_url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(db_url)
emb_model = SentenceTransformer("intfloat/multilingual-e5-large")

with Session(engine) as session:
    items = search_hybrid(session, emb_model, QUERY, k=5)
    chunks = build_context(session, items)

system_prompt, user_message = build_prompt(QUERY, chunks)

print("=" * 70)
print("SYSTEM PROMPT")
print("=" * 70)
print(system_prompt)
print()
print("=" * 70)
print("USER MESSAGE")
print("=" * 70)
print(user_message)
print()
print("=" * 70)
print(f"Dispositivos recuperados: {len(chunks)}")
for c in chunks:
    print(f"  [{c.score_rrf:.4f}] {c.endereco} — fontes: {c.fontes}")
