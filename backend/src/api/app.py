"""FastAPI app — JusBot."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv("../.env")

from src.api.schemas import DispositivoCitado, PerguntaRequest, RespostaResponse  # noqa: E402
from src.generation.generate import generate_answer  # noqa: E402

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    db_url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
    app.state.engine = create_engine(db_url, pool_pre_ping=True)
    app.state.emb_model = SentenceTransformer("intfloat/multilingual-e5-large")
    yield
    app.state.engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.post("/pergunta", response_model=RespostaResponse)
def pergunta(req: PerguntaRequest, request: Request) -> RespostaResponse:
    try:
        with Session(request.app.state.engine) as session:
            result = generate_answer(req.pergunta, session, request.app.state.emb_model, k=8)
    except Exception as exc:
        logger.error("Erro na geração: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Erro interno ao processar a pergunta."
        ) from exc

    return RespostaResponse(
        resposta=result.answer,
        dispositivos=[
            DispositivoCitado(
                endereco=c.endereco,
                texto=c.texto,
                documento=c.documento,
            )
            for c in result.chunks
        ],
    )
