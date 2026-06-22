"""Etapa 4 — validação de grounding para Q2-Q5."""

import os

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv("../.env")

from src.generation.generate import generate_answer  # noqa: E402

QUERIES = [
    ("Q2", "comprei um produto com defeito, posso devolver?"),
    ("Q3", "qual o prazo para sacar o FGTS depois de ser mandado embora?"),
    ("Q4", "a loja pode cobrar diferente no cartão e no dinheiro?"),
    ("Q5", "tenho direito a férias proporcionais se peço demissão?"),
]

db_url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(db_url)
emb_model = SentenceTransformer("intfloat/multilingual-e5-large")

SEP = "=" * 70

with Session(engine) as session:
    for tag, query in QUERIES:
        result = generate_answer(query, session, emb_model, k=8)

        print(f"\n{SEP}")
        print(f"{tag} — PERGUNTA: {query}")
        print(SEP)
        print(result.answer)
        print(f"\n{SEP}")
        print(f"{tag} — DISPOSITIVOS PASSADOS")
        print(SEP)
        for i, c in enumerate(result.chunks, 1):
            print(f"[{i}] {c.endereco}")
            if c.ancestrais:
                print(f"     ctx pai: {c.ancestrais[-1].texto[:150]}...")
            print(f"     {c.texto[:250]}{'...' if len(c.texto) > 250 else ''}")
            print()
