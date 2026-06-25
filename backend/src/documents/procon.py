"""Geração de reclamação ao PROCON — JusBot.

Pipeline:
    relato → RAG com filtro area='consumidor' → fatos via LLM
           → validação estrutural → render Jinja2 → ProconResult

Divisão de responsabilidades:
  LLM     → apenas seção III(b): narrativa do problema em 3ª pessoa
  RAG     → seção IV: dispositivos recuperados (Art. 18 CDC, Art. 42, etc.)
  Usuário → seção V: requerimentos definidos pelo requerente, não pelo LLM
  Template → frase-líder de fatos, parágrafo condicional de contato prévio,
             itens fixos de providência administrativa

O LLM nunca preenche nome, CPF, RG, CNPJ, valor, data ou número de protocolo.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from src.rag.retrieval import ContextualChunk

from .base import (
    TEMPLATES_DIR,
    buscar_fundamento,
    criar_jinja_env,
    filtrar_pertinencia,
    formatar_data,
    montar_fundamento,
    redigir_fatos,
    validar_campos_base,
)
from .schemas import ProconResult


class DadosProcon(BaseModel):
    """Dados duros do caso preenchidos e confirmados pelo usuário.

    Campos obrigatórios (Pydantic recusa se faltar): nome_requerente,
    cpf_requerente, procon_cidade, procon_uf, requerida_nome,
    produto_servico, relato, requerimentos.

    Campos opcionais ficam como marcador [A PREENCHER: ...] no documento.
    O LLM nunca preenche nome, CPF, RG, CNPJ, valor, data ou protocolo.
    """

    # ── Requerente — obrigatórios ─────────────────────────────────────────────
    nome_requerente: str = Field(..., min_length=2, max_length=200)
    cpf_requerente: str = Field(
        ...,
        min_length=11,
        max_length=14,
        description="CPF do requerente (000.000.000-00)",
    )

    # ── PROCON destinatário — obrigatórios ────────────────────────────────────
    procon_cidade: str = Field(..., min_length=2, max_length=100)
    procon_uf: str = Field(..., min_length=2, max_length=2)

    # ── Requerida — obrigatório ───────────────────────────────────────────────
    requerida_nome: str = Field(..., min_length=2, max_length=200)

    # ── Caso — obrigatórios ───────────────────────────────────────────────────
    produto_servico: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="O que foi adquirido/contratado; marca/modelo/série incluídos aqui",
    )
    relato: str = Field(
        ...,
        min_length=10,
        description="Texto livre do usuário descrevendo o problema; LLM redige a narrativa a partir disto",
    )
    requerimentos: list[str] = Field(
        ...,
        min_length=1,
        description="Pedidos do usuário; cada item vira um item na seção V (não gerado por LLM)",
    )

    # ── Área — fixo consumidor ────────────────────────────────────────────────
    area: Literal["consumidor"] = "consumidor"

    # ── Requerente — qualificação completa (opcionais) ────────────────────────
    requerente_qualificacao: str | None = None
    rg_requerente: str | None = None
    endereco_requerente: str | None = None
    telefone_requerente: str | None = None
    email_requerente: str | None = None

    # ── Requerida — qualificação opcional ─────────────────────────────────────
    requerida_cnpj: str | None = None
    requerida_endereco: str | None = None
    requerida_contato: str | None = None

    # ── Dados do fato — opcionais mas duros (nunca gerados pelo LLM) ─────────
    valor: str | None = None
    forma_pagamento: str | None = None
    data_fato: date | None = None
    data: date = Field(default_factory=date.today)

    # ── Contato prévio — opcionais condicionais ───────────────────────────────
    contato_previo_datas: list[str] | None = None
    contato_previo_protocolos: list[str] | None = None

    @model_validator(mode="after")
    def _requerimentos_nao_vazio(self) -> DadosProcon:
        if not self.requerimentos:
            raise ValueError("requerimentos deve conter ao menos um item")
        return self


class ProconError(Exception):
    pass


_TEMPLATE_NAME = "procon.jinja2"


def _validar_campos(
    dados: DadosProcon,
    fatos: str,
    chunks: list[ContextualChunk],
) -> None:
    """Validação específica da reclamação PROCON: base + requerimentos não-vazio."""
    faltando = validar_campos_base(fatos, chunks)
    if not dados.requerimentos:
        faltando.append("requerimentos (lista vazia — ao menos um item obrigatório)")
    if faltando:
        raise ProconError(
            "Campos obrigatórios ausentes na reclamação PROCON: " + ", ".join(faltando)
        )


def gerar_procon(
    dados: DadosProcon,
    session: Session,
    emb_model: Any,
    k: int = 8,
) -> ProconResult:
    """Gera rascunho de reclamação ao PROCON para o caso descrito.

    Args:
        dados: Campos duros confirmados pelo usuário. O LLM não preenche nenhum destes.
               dados.relato é o texto livre; dados.requerimentos define os itens da
               seção V (voz do usuário, não do LLM).
        session: Sessão SQLAlchemy com acesso ao banco de chunks.
        emb_model: Modelo sentence-transformers já carregado.
        k: Número de dispositivos legais a recuperar via RAG (default 8).

    Returns:
        ProconResult com documento renderizado, fatos, requerimentos, chunks usados
        e lista de avisos ao usuário (avisos não compõem o documento).

    Raises:
        ProconError: Se RAG não encontrar fundamento ou se campos obrigatórios
                     (fatos, requerimentos) estiverem ausentes no resultado.
    """
    # Etapa 1 — RAG com filtro de área fixo em "consumidor"; aborta antes do LLM
    # se não houver fundamento recuperado — não desperdiça a chamada ao LLM.
    # (Diferença da notificação: a checagem de chunks vazio é explícita e antecipada.)
    chunks = buscar_fundamento(session, emb_model, dados.relato, k=k, area="consumidor")
    if not chunks:
        raise ProconError(
            "sem fundamento legal recuperado para o relato; " "não é possível gerar a reclamação"
        )
    chunks = filtrar_pertinencia(dados.relato, chunks)

    # Etapa 2 — LLM redige apenas a narrativa factual (seção III-b)
    fatos = redigir_fatos(dados.relato, tipo_documento="reclamação ao PROCON")

    # Etapa 3 — Validação estrutural: recusa devolver peça incompleta
    _validar_campos(dados, fatos, chunks)

    # Etapa 4 — Monta contexto e renderiza o template
    fundamentos = montar_fundamento(chunks)
    data_fato_formatada = formatar_data(dados.data_fato) if dados.data_fato else None
    data_formatada = formatar_data(dados.data)

    env = criar_jinja_env(TEMPLATES_DIR)
    documento = env.get_template(_TEMPLATE_NAME).render(
        # PROCON destinatário
        procon_cidade=dados.procon_cidade,
        procon_uf=dados.procon_uf,
        # Requerente
        nome_requerente=dados.nome_requerente,
        requerente_qualificacao=dados.requerente_qualificacao,
        rg_requerente=dados.rg_requerente,
        cpf_requerente=dados.cpf_requerente,
        endereco_requerente=dados.endereco_requerente,
        telefone_requerente=dados.telefone_requerente,
        email_requerente=dados.email_requerente,
        # Requerida
        requerida_nome=dados.requerida_nome,
        requerida_cnpj=dados.requerida_cnpj,
        requerida_endereco=dados.requerida_endereco,
        requerida_contato=dados.requerida_contato,
        # Fatos
        data_fato_formatada=data_fato_formatada,
        produto_servico=dados.produto_servico,
        valor=dados.valor,
        forma_pagamento=dados.forma_pagamento,
        fatos=fatos,
        contato_previo_datas=dados.contato_previo_datas,
        contato_previo_protocolos=dados.contato_previo_protocolos,
        # Fundamentos (RAG)
        fundamentos=fundamentos,
        # Pedidos
        requerimentos=dados.requerimentos,
        # Data do documento
        data_formatada=data_formatada,
    )

    # Aviso ao usuário — não compõe o documento
    sem_contato = not dados.contato_previo_datas and not dados.contato_previo_protocolos
    avisos = (
        [
            "Recomendado registrar tentativa de contato com a empresa antes de "
            "protocolar — fortalece a reclamação."
        ]
        if sem_contato
        else []
    )

    return ProconResult(
        documento=documento,
        fatos=fatos,
        requerimentos=dados.requerimentos,
        chunks=chunks,
        avisos=avisos,
    )
