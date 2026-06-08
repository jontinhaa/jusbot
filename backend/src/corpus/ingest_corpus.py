"""
Ingere (ou re-ingere) todos os documentos do corpus jurídico no banco.

Uso:
    python -m src.corpus.ingest_corpus [--force] [--dry-run] [codigo ...]

Flags:
    --force     Re-ingere documentos já presentes no banco (delete + insert).
    --dry-run   Só mostra o que faria, sem tocar no banco.
    codigo ...  Ingere apenas os documentos listados (default: todos).

Verificação de regressão do bug psycopg3:
    Detecta automaticamente se um documento foi inserido com Python None → JSON null
    em colunas JSONB (em vez de SQL NULL) e o re-ingere mesmo sem --force.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.corpus.parser_planalto import _CORPUS_MAP, ingest  # noqa: E402


def _detect_jsonb_bug(session: Session, document_id: int) -> bool:
    """Retorna True se algum chunk do documento tem JSON null em coluna JSONB nullable.

    O bug do psycopg3 converte Python None → literalmente 'null' (JSON null) em vez de
    SQL NULL. Isso é detectável comparando IS NULL vs ::text = 'null'.
    """
    result = session.execute(
        text(
            """
            SELECT COUNT(*) FROM chunks
            WHERE document_id = :doc_id
              AND (
                    alterado_por::text = 'null'
                 OR caminho_hierarquico::text = 'null'
                 OR metadata::text = 'null'
              )
            """
        ),
        {"doc_id": document_id},
    )
    return result.scalar_one() > 0


def _delete_document(session: Session, document_id: int) -> None:
    """Remove documento e seus chunks (CASCADE garantido pelo schema)."""
    session.execute(text("DELETE FROM documents WHERE id = :id"), {"id": document_id})
    session.commit()


def run(
    targets: list[str],
    *,
    force: bool = False,
    dry_run: bool = False,
    db_url: str,
) -> None:
    engine = create_engine(db_url, echo=False)

    with Session(engine) as session:
        for codigo in targets:
            if codigo not in _CORPUS_MAP:
                print(f"[SKIP]  {codigo} — não encontrado no _CORPUS_MAP")
                continue

            rel_path, doc_kwargs = _CORPUS_MAP[codigo]
            html_path = Path(__file__).resolve().parents[2] / rel_path

            if not html_path.exists():
                print(f"[ERRO]  {codigo} — arquivo não encontrado: {html_path}")
                continue

            # Verifica se já existe no banco
            existing = session.execute(
                text("SELECT id FROM documents WHERE codigo = :c"), {"c": codigo}
            ).fetchone()

            if existing:
                doc_id = existing[0]
                has_bug = _detect_jsonb_bug(session, doc_id)

                if has_bug:
                    reason = "bug psycopg3 detectado (JSON null em JSONB)"
                elif force:
                    reason = "--force"
                else:
                    print(f"[OK]    {codigo} — já ingerido corretamente, pulando.")
                    continue

                if dry_run:
                    print(f"[DRY]   {codigo} — re-ingeriria ({reason})")
                    continue

                print(f"[REINGEST] {codigo} — {reason}")
                _delete_document(session, doc_id)

            else:
                if dry_run:
                    print(f"[DRY]   {codigo} — ingeriria (novo)")
                    continue
                print(f"[INGEST]   {codigo} — novo documento")

            doc_id, n_chunks, n_desc = ingest(html_path, doc_kwargs, session)
            print(f"           document_id={doc_id}, " f"chunks={n_chunks}, descartados={n_desc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("codigos", nargs="*", default=list(_CORPUS_MAP))
    args = parser.parse_args()

    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        print("ERRO: DATABASE_URL não definida.", file=sys.stderr)
        sys.exit(1)

    db_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    run(args.codigos, force=args.force, dry_run=args.dry_run, db_url=db_url)


if __name__ == "__main__":
    main()
