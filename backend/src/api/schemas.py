"""Schemas Pydantic da API JusBot."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PerguntaRequest(BaseModel):
    pergunta: str = Field(..., min_length=1, max_length=2000)


class DispositivoCitado(BaseModel):
    endereco: str
    texto: str
    documento: str


class RespostaResponse(BaseModel):
    resposta: str
    dispositivos: list[DispositivoCitado]
