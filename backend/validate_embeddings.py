"""
Validação em 3 níveis dos embeddings gerados.
Uso: python backend/validate_embeddings.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

# ──────────────────────────────────────────────
# Conexão
# ──────────────────────────────────────────────
raw_url = os.environ.get("DATABASE_URL", "")
if not raw_url:
    print("ERRO: DATABASE_URL não definida.", file=sys.stderr)
    sys.exit(1)

db_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(db_url, echo=False)


def cosine(a: list, b: list) -> float:
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


# ══════════════════════════════════════════════
# NÍVEL 1 — Estrutural
# ══════════════════════════════════════════════
print("=" * 60)
print("NÍVEL 1 — Estrutural")
print("=" * 60)

with engine.connect() as conn:
    null_count = conn.execute(
        text("SELECT COUNT(*) FROM chunks WHERE embedding IS NULL")
    ).scalar_one()
    print(f"embedding IS NULL : {null_count}")

    # dimensão numa amostra de 20 chunks
    rows = conn.execute(
        text("SELECT id, vector_dims(embedding) AS dims FROM chunks ORDER BY id LIMIT 20")
    ).fetchall()

dims_set = {r.dims for r in rows}
print(f"Dimensões na amostra (20 chunks) : {dims_set}")
for r in rows[:5]:
    print(f"  chunk id={r.id} -> {r.dims}d")

# ══════════════════════════════════════════════
# NÍVEL 2 — Sanidade semântica
# ══════════════════════════════════════════════
print()
print("=" * 60)
print("NÍVEL 2 — Sanidade semântica")
print("=" * 60)

with engine.connect() as conn:
    # Par RELACIONADO: Art. 487 e Art. 488 CLT — ambos definem aviso previo
    # (IDs fixos para garantir que sao os chunks certos)
    relacionados = conn.execute(
        text(
            """
        SELECT c.id, c.numero, c.tipo, d.codigo, c.texto, c.embedding::text
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.id IN (12636, 12645)
        ORDER BY c.id
    """
        )
    ).fetchall()

    # Par NAO RELACIONADO:
    #   11188 = CDC Art. 30 (publicidade/oferta ao consumidor)
    #   11648 = CLT Art. 66 (intervalo entre jornadas)
    nao_rel_a = conn.execute(
        text(
            """
        SELECT c.id, c.numero, c.tipo, d.codigo, c.texto, c.embedding::text
        FROM chunks c JOIN documents d ON c.document_id = d.id
        WHERE c.id = 11188
    """
        )
    ).fetchone()

    nao_rel_b = conn.execute(
        text(
            """
        SELECT c.id, c.numero, c.tipo, d.codigo, c.texto, c.embedding::text
        FROM chunks c JOIN documents d ON c.document_id = d.id
        WHERE c.id = 11648
    """
        )
    ).fetchone()


def parse_vec(pg_text: str) -> list[float]:
    return [float(x) for x in pg_text.strip("[]").split(",")]


if len(relacionados) < 2:
    print("AVISO: não encontrei 2 chunks sobre 'aviso prévio' na CLT — ajuste a query.")
else:
    r1, r2 = relacionados
    vec_r1 = parse_vec(r1.embedding)
    vec_r2 = parse_vec(r2.embedding)
    sim_rel = cosine(vec_r1, vec_r2)
    print("Par RELACIONADO (aviso previo / trabalho):")
    print(f"  chunk {r1.id} — {r1.tipo} {r1.numero} [{r1.codigo}]")
    print(f'    "{r1.texto[:100]}..."')
    print(f"  chunk {r2.id} — {r2.tipo} {r2.numero} [{r2.codigo}]")
    print(f'    "{r2.texto[:100]}..."')
    print(f"  cosseno = {sim_rel:.4f}")

if nao_rel_a and nao_rel_b:
    vec_a = parse_vec(nao_rel_a.embedding)
    vec_b = parse_vec(nao_rel_b.embedding)
    sim_nrel = cosine(vec_a, vec_b)
    print()
    print("Par NAO RELACIONADO (FGTS/trabalho vs defeito-produto/consumidor):")
    print(f"  chunk {nao_rel_a.id} — {nao_rel_a.tipo} {nao_rel_a.numero} [{nao_rel_a.codigo}]")
    print(f'    "{nao_rel_a.texto[:100]}..."')
    print(f"  chunk {nao_rel_b.id} — {nao_rel_b.tipo} {nao_rel_b.numero} [{nao_rel_b.codigo}]")
    print(f'    "{nao_rel_b.texto[:100]}..."')
    print(f"  cosseno = {sim_nrel:.4f}")

    if len(relacionados) >= 2:
        print()
        if sim_rel > sim_nrel:
            print(f"ORDEM OK: relacionado ({sim_rel:.4f}) > não-relacionado ({sim_nrel:.4f})")
        else:
            print(f"PROBLEMA: relacionado ({sim_rel:.4f}) <= não-relacionado ({sim_nrel:.4f})")
            print("  -> Verificar prefixo 'passage:' no pipeline e normalizacao.")
else:
    print("AVISO: não encontrei chunks para o par não-relacionado — ajuste as queries.")

# ══════════════════════════════════════════════
# NÍVEL 3 — Smoke test de retrieval
# ══════════════════════════════════════════════
print()
print("=" * 60)
print("NÍVEL 3 — Smoke test de retrieval")
print("=" * 60)

print("Carregando multilingual-e5-large...", flush=True)
model = SentenceTransformer("intfloat/multilingual-e5-large")

query_text = "fui demitido sem justa causa, tenho direito a quê?"
prefixed = f"query: {query_text}"
print(f'Query  : "{query_text}"')
print(f'Prefixo: "{prefixed[:50]}..."', flush=True)

q_vec = model.encode(prefixed, normalize_embeddings=True).tolist()
q_vec_str = "[" + ",".join(str(x) for x in q_vec) + "]"

with engine.connect() as conn:
    results = conn.execute(
        text(
            """
        SELECT c.id, c.numero, c.tipo, d.codigo,
               LEFT(c.texto, 120) AS preview,
               (c.embedding <=> CAST(:qv AS vector)) AS dist
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        ORDER BY c.embedding <=> CAST(:qv AS vector)
        LIMIT 5
    """
        ),
        {"qv": q_vec_str},
    ).fetchall()

print()
print(f'Top-5 para: "{query_text}"')
print()
for i, r in enumerate(results, 1):
    print(f"  [{i}] id={r.id} | {r.tipo} {r.numero} | [{r.codigo}] | dist={r.dist:.4f}")
    print(f'      "{r.preview}"')
    print()
