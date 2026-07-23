"""FastAPI app — JusBot."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv("../.env")

from src.api.schemas import DispositivoCitado, PerguntaRequest, RespostaResponse  # noqa: E402
from src.documents.jec import DadosJec, JecError, gerar_jec  # noqa: E402
from src.documents.notificacao import NotificacaoError, gerar_notificacao  # noqa: E402
from src.documents.procon import DadosProcon, ProconError, gerar_procon  # noqa: E402
from src.documents.schemas import DadosCaso  # noqa: E402
from src.generation.generate import generate_answer  # noqa: E402

logger = logging.getLogger(__name__)

_UI_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_UI_TEMPLATES_DIR))

_TITULOS = {
    "notificacao": "Notificação Extrajudicial",
    "procon": "Reclamação ao PROCON",
    "jec": "Petição Inicial — Juizado Especial Cível",
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    db_url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
    app.state.engine = create_engine(db_url, pool_pre_ping=True)
    app.state.emb_model = SentenceTransformer("intfloat/multilingual-e5-large")
    yield
    app.state.engine.dispose()


app = FastAPI(lifespan=lifespan)


# ─── API JSON existente ───────────────────────────────────────────────────────


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


# ─── Interface HTML ───────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "home.html")


@app.get("/novo/{tipo}", response_class=HTMLResponse)
def formulario(tipo: str, request: Request) -> HTMLResponse:
    if tipo not in _TITULOS:
        return HTMLResponse("Tipo inválido. Use: notificacao, procon ou jec.", status_code=404)
    return templates.TemplateResponse(request, f"form_{tipo}.html")


def _parse_requerimentos(raw: str) -> list[str]:
    return [linha.strip() for linha in raw.splitlines() if linha.strip()]


def _parse_valor_centavos(valor_str: str) -> int:
    normalizado = valor_str.strip().replace(",", ".").replace("\xa0", "").replace(" ", "")
    try:
        d = Decimal(normalizado)
    except InvalidOperation as exc:
        raise ValueError(
            f"Valor inválido: {valor_str!r}. Use formato como 4924,70 ou 4924.70"
        ) from exc
    centavos = int(round(d * 100))
    if centavos <= 0:
        raise ValueError("O valor da causa deve ser positivo.")
    return centavos


def _erro_html(request: Request, tipo: str, msg: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "resultado.html",
        {"titulo": _TITULOS[tipo], "erro": msg, "documento": None, "avisos": []},
    )


@app.post("/gerar/notificacao", response_class=HTMLResponse)
def gerar_notificacao_route(
    request: Request,
    notificante_nome: str = Form(...),
    notificante_qualificacao: str = Form(...),
    notificante_cpf: str = Form(...),
    notificado_nome: str = Form(...),
    area: str = Form(...),
    assunto: str = Form(...),
    cidade: str = Form(...),
    prazo_dias: int = Form(15),
    relato: str = Form(...),
    requerimentos: str = Form(...),
) -> HTMLResponse:
    try:
        dados = DadosCaso(
            notificante_nome=notificante_nome,
            notificante_qualificacao=notificante_qualificacao,
            notificante_cpf=notificante_cpf,
            notificado_nome=notificado_nome,
            area=area,
            assunto=assunto,
            cidade=cidade,
            prazo_dias=prazo_dias,
            requerimentos=_parse_requerimentos(requerimentos),
        )
        with Session(request.app.state.engine) as session:
            resultado = gerar_notificacao(dados, relato, session, request.app.state.emb_model)
    except (NotificacaoError, ValidationError, ValueError) as exc:
        return _erro_html(request, "notificacao", str(exc))
    except Exception as exc:
        logger.error("Erro inesperado em /gerar/notificacao: %s", exc, exc_info=True)
        return _erro_html(request, "notificacao", f"Erro interno: {exc}")

    # NotificacaoResult não tem .avisos — não tente acessar
    return templates.TemplateResponse(
        request,
        "resultado.html",
        {
            "titulo": _TITULOS["notificacao"],
            "documento": resultado.documento,
            "avisos": [],
            "erro": None,
        },
    )


@app.post("/gerar/procon", response_class=HTMLResponse)
def gerar_procon_route(
    request: Request,
    nome_requerente: str = Form(...),
    cpf_requerente: str = Form(...),
    procon_cidade: str = Form(...),
    procon_uf: str = Form(...),
    requerida_nome: str = Form(...),
    produto_servico: str = Form(...),
    relato: str = Form(...),
    requerimentos: str = Form(...),
) -> HTMLResponse:
    try:
        dados = DadosProcon(
            nome_requerente=nome_requerente,
            cpf_requerente=cpf_requerente,
            procon_cidade=procon_cidade,
            procon_uf=procon_uf,
            requerida_nome=requerida_nome,
            produto_servico=produto_servico,
            relato=relato,
            requerimentos=_parse_requerimentos(requerimentos),
        )
        with Session(request.app.state.engine) as session:
            resultado = gerar_procon(dados, session, request.app.state.emb_model)
    except (ProconError, ValidationError, ValueError) as exc:
        return _erro_html(request, "procon", str(exc))
    except Exception as exc:
        logger.error("Erro inesperado em /gerar/procon: %s", exc, exc_info=True)
        return _erro_html(request, "procon", f"Erro interno: {exc}")

    return templates.TemplateResponse(
        request,
        "resultado.html",
        {
            "titulo": _TITULOS["procon"],
            "documento": resultado.documento,
            "avisos": resultado.avisos,
            "erro": None,
        },
    )


@app.post("/gerar/jec", response_class=HTMLResponse)
def gerar_jec_route(
    request: Request,
    comarca_cidade: str = Form(...),
    comarca_uf: str = Form(...),
    requerente_nome: str = Form(...),
    requerente_cpf: str = Form(...),
    requerido_nome: str = Form(...),
    tipo_acao: str = Form(...),
    valor_causa: str = Form(...),
    relato: str = Form(...),
    requerimentos: str = Form(...),
) -> HTMLResponse:
    try:
        valor_centavos = _parse_valor_centavos(valor_causa)
        dados = DadosJec(
            comarca_cidade=comarca_cidade,
            comarca_uf=comarca_uf,
            requerente_nome=requerente_nome,
            requerente_cpf=requerente_cpf,
            requerido_nome=requerido_nome,
            tipo_acao=tipo_acao,
            valor_causa_centavos=valor_centavos,
            relato=relato,
            requerimentos=_parse_requerimentos(requerimentos),
        )
        with Session(request.app.state.engine) as session:
            resultado = gerar_jec(dados, session, request.app.state.emb_model)
    except (JecError, ValidationError, ValueError) as exc:
        return _erro_html(request, "jec", str(exc))
    except Exception as exc:
        logger.error("Erro inesperado em /gerar/jec: %s", exc, exc_info=True)
        return _erro_html(request, "jec", f"Erro interno: {exc}")

    return templates.TemplateResponse(
        request,
        "resultado.html",
        {
            "titulo": _TITULOS["jec"],
            "documento": resultado.documento,
            "avisos": resultado.avisos,
            "erro": None,
        },
    )
