"""Schemas Pydantic para geração de documentos — JusBot.

Regra central: DadosCaso contém os campos duros que o usuário preencheu e confirmou.
O LLM nunca preenche nome, CPF/CNPJ ou valor. Esses vêm do DadosCaso ou ficam como marcador.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.rag.retrieval import ContextualChunk


class DadosCaso(BaseModel):
    """Dados duros do caso preenchidos e confirmados pelo usuário.

    Campos obrigatórios (Pydantic recusa se faltar): notificante_nome,
    notificante_qualificacao, notificante_cpf, notificado_nome, assunto,
    prazo_dias, cidade, requerimentos.

    Campos opcionais ficam como marcador [A PREENCHER: ...] no documento gerado.
    O LLM nunca preenche nome, CPF/CNPJ ou valor.
    """

    # ── Notificante — obrigatórios ────────────────────────────────────────────
    notificante_nome: str = Field(..., min_length=2, max_length=200)
    notificante_qualificacao: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Papel/vínculo sucinto: ex: 'consumidora', 'trabalhador'",
    )
    notificante_cpf: str = Field(
        ...,
        min_length=11,
        max_length=14,
        description="CPF do notificante (000.000.000-00)",
    )

    # ── Notificante — qualificação completa (opcionais) ───────────────────────
    notificante_endereco: str | None = None

    # ── Notificado — obrigatório ──────────────────────────────────────────────
    notificado_nome: str = Field(..., min_length=2, max_length=200)

    # ── Notificado — qualificação inteiramente opcional ───────────────────────
    # (cidadão frequentemente não conhece os dados completos da outra parte)
    notificado_qualificacao: str | None = None
    notificado_cpf_cnpj: str | None = None
    notificado_endereco: str | None = None

    # ── Pedido — definido pelo usuário, NÃO pelo LLM ─────────────────────────
    requerimentos: list[str] = Field(
        ...,
        min_length=1,
        description="Ações exigidas do notificado; cada item vira uma alínea (a, b, ...)",
    )

    # ── Caso ──────────────────────────────────────────────────────────────────
    area: Literal["consumidor", "trabalho"] = Field(
        ...,
        description="Área jurídica declarada pelo usuário — restringe o retrieval ao corpus correto",
    )
    assunto: str = Field(..., min_length=3, max_length=300)
    prazo_dias: int = Field(default=15, ge=1, le=365)
    cidade: str = Field(..., min_length=2, max_length=100)
    data: date = Field(default_factory=date.today)

    @model_validator(mode="after")
    def _requerimentos_nao_vazio(self) -> DadosCaso:
        if not self.requerimentos:
            raise ValueError("requerimentos deve conter ao menos um item")
        return self


@dataclass
class NotificacaoResult:
    """Resultado da geração da notificação extrajudicial."""

    documento: str
    fatos: str
    requerimentos: list[str]
    chunks: list[ContextualChunk]


@dataclass
class ProconResult:
    """Resultado da geração da reclamação ao PROCON."""

    documento: str
    fatos: str
    requerimentos: list[str]
    chunks: list[ContextualChunk]
    avisos: list[str] = field(default_factory=list)


@dataclass
class JecResult:
    """Resultado da geração da petição inicial para o JEC."""

    documento: str
    fatos: str
    requerimentos: list[str]
    chunks: list[ContextualChunk]
    avisos: list[str] = field(default_factory=list)
