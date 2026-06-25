"""Geração de petição inicial para o Juizado Especial Cível — JusBot.

Pipeline (a implementar em Etapas 2-3):
    relato → RAG com filtro area='consumidor' → fatos via LLM
           → validação estrutural → render Jinja2 → JecResult

Divisão de responsabilidades:
  LLM     → apenas seção DOS FATOS: narrativa em 3ª pessoa
  RAG     → seção DO DIREITO: dispositivos recuperados (CDC, etc.)
  Usuário → seção DOS PEDIDOS: requerimentos definidos pelo requerente
            tipo_acao: escolha assistida, LLM não enquadra o rito
            valor_causa: dado duro, nunca calculado pelo sistema
  Template → cabeçalho da comarca, qualificações, condicional de dano moral

O LLM nunca preenche nome, CPF, RG, CNPJ, valor, data ou valor da causa.
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
    valor_centavos_extenso,
)
from .schemas import JecResult


class DadosJec(BaseModel):
    """Dados duros do caso preenchidos e confirmados pelo usuário.

    Campos obrigatórios (Pydantic recusa se faltar): comarca_cidade,
    comarca_uf, requerente_nome, requerente_cpf, requerido_nome,
    tipo_acao, relato, requerimentos, valor_causa.

    Campos opcionais ficam como marcador [A PREENCHER: ...] no documento.
    O LLM nunca preenche nome, CPF, RG, CNPJ, valor, data ou valor da causa.

    Nota (Etapa 2 — template): o parágrafo de dano moral é renderizado
    condicionalmente se 'indenização por danos morais' ou 'indenização por
    danos materiais e morais' constar nos requerimentos. Não é campo próprio.
    """

    # ── Comarca — obrigatórios ────────────────────────────────────────────────
    comarca_cidade: str = Field(..., min_length=2, max_length=100)
    comarca_uf: str = Field(..., min_length=2, max_length=2)

    # ── Requerente — obrigatórios ─────────────────────────────────────────────
    requerente_nome: str = Field(..., min_length=2, max_length=200)
    requerente_cpf: str = Field(
        ...,
        min_length=11,
        max_length=14,
        description="CPF do requerente (000.000.000-00)",
    )

    # ── Requerido — obrigatório ───────────────────────────────────────────────
    requerido_nome: str = Field(..., min_length=2, max_length=200)

    # ── Tipo de ação — escolha assistida do usuário; LLM não enquadra ─────────
    tipo_acao: Literal[
        "indenização por danos materiais",
        "indenização por danos morais",
        "indenização por danos materiais e morais",
        "obrigação de fazer",
        "obrigação de não fazer",
        "cobrança",
        "restituição de valores",
    ] = Field(..., description="Ação escolhida pelo usuário via menu; não gerada pelo LLM")

    # ── Caso — obrigatórios ───────────────────────────────────────────────────
    relato: str = Field(
        ...,
        min_length=10,
        description="Texto livre do usuário; LLM redige a narrativa factual a partir disto",
    )
    requerimentos: list[str] = Field(
        ...,
        min_length=1,
        description="Pedidos do usuário; cada item vira um pedido na seção DOS PEDIDOS",
    )
    valor_causa_centavos: int = Field(
        ...,
        gt=0,
        description=(
            "Valor da causa em CENTAVOS (ex: 543000 = R$ 5.430,00). "
            "Inteiro para evitar erro de ponto flutuante; a conversão "
            "de texto do usuário para centavos é responsabilidade da "
            "camada de entrada (formulário, Semana 3)."
        ),
    )

    # ── Área — fixo consumidor (MVP) ──────────────────────────────────────────
    area: Literal["consumidor"] = "consumidor"

    # ── Requerente — qualificação agrupada e demais opcionais ─────────────────
    # requerente_qualificacao: texto único, ex: "brasileira, solteira, professora"
    requerente_qualificacao: str | None = None
    requerente_rg: str | None = None
    requerente_endereco: str | None = None
    requerente_telefone: str | None = None
    requerente_email: str | None = None

    # ── Requerido — qualificação agrupada e demais opcionais ──────────────────
    # requerido_qualificacao: pessoa física ou jurídica, texto único
    requerido_qualificacao: str | None = None
    requerido_cpf_cnpj: str | None = None  # campo único — CPF ou CNPJ
    requerido_endereco: str | None = None
    requerido_contato: str | None = None

    # ── Dado do fato — opcional mas duro (nunca gerado pelo LLM) ─────────────
    data_fato: date | None = None

    # ── Data do documento ─────────────────────────────────────────────────────
    data: date = Field(default_factory=date.today)

    @model_validator(mode="after")
    def _requerimentos_nao_vazio(self) -> DadosJec:
        if not self.requerimentos:
            raise ValueError("requerimentos deve conter ao menos um item")
        return self


class JecError(Exception):
    pass


_TEMPLATE_NAME = "jec.jinja2"


def _validar_campos(
    dados: DadosJec,
    fatos: str,
    chunks: list[ContextualChunk],
) -> None:
    """Validação específica da petição JEC: base + requerimentos não-vazio."""
    from .base import validar_campos_base

    faltando = validar_campos_base(fatos, chunks)
    if not dados.requerimentos:
        faltando.append("requerimentos (lista vazia — ao menos um item obrigatório)")
    if faltando:
        raise JecError("Campos obrigatórios ausentes na petição JEC: " + ", ".join(faltando))


def gerar_jec(
    dados: DadosJec,
    session: Session,
    emb_model: Any,
    k: int = 8,
) -> JecResult:
    """Gera rascunho de petição inicial para o JEC para o caso descrito.

    Args:
        dados: Campos duros confirmados pelo usuário. O LLM não preenche nenhum destes.
               dados.relato é o texto livre; dados.requerimentos define os itens da
               seção DOS PEDIDOS (voz do usuário, não do LLM).
               dados.valor_causa_centavos é inteiro de centavos (dado duro).
        session: Sessão SQLAlchemy com acesso ao banco de chunks.
        emb_model: Modelo sentence-transformers já carregado.
        k: Número de dispositivos legais a recuperar via RAG (default 8).

    Returns:
        JecResult com documento renderizado, fatos, requerimentos, chunks usados
        e lista de avisos ao usuário (por ora vazia — regras de aviso pendentes).

    Raises:
        JecError: Se RAG não encontrar fundamento ou se campos obrigatórios
                  (fatos, requerimentos) estiverem ausentes no resultado.
    """
    # Etapa 1 — RAG com filtro de área fixo em "consumidor" (MVP); aborta antes
    # do LLM se não houver fundamento — não desperdiça a chamada ao LLM.
    chunks = buscar_fundamento(session, emb_model, dados.relato, k=k, area="consumidor")
    if not chunks:
        raise JecError(
            "sem fundamento legal recuperado para o relato; não é possível gerar a petição"
        )
    chunks = filtrar_pertinencia(dados.relato, chunks)

    # Etapa 2 — LLM redige apenas a narrativa factual (seção DOS FATOS)
    fatos = redigir_fatos(
        dados.relato, tipo_documento="petição inicial para Juizado Especial Cível"
    )

    # Etapa 3 — Validação estrutural: recusa devolver peça incompleta
    _validar_campos(dados, fatos, chunks)

    # Etapa 4 — Monta contexto e renderiza o template
    fundamentos = montar_fundamento(chunks)
    valor_formatado, valor_extenso = valor_centavos_extenso(dados.valor_causa_centavos)
    data_fato_formatada = formatar_data(dados.data_fato) if dados.data_fato else None
    data_formatada = formatar_data(dados.data)

    env = criar_jinja_env(TEMPLATES_DIR)
    documento = env.get_template(_TEMPLATE_NAME).render(
        # Comarca
        comarca_cidade=dados.comarca_cidade,
        comarca_uf=dados.comarca_uf,
        # Requerente
        requerente_nome=dados.requerente_nome,
        requerente_qualificacao=dados.requerente_qualificacao,
        requerente_rg=dados.requerente_rg,
        requerente_cpf=dados.requerente_cpf,
        requerente_endereco=dados.requerente_endereco,
        requerente_email=dados.requerente_email,
        requerente_telefone=dados.requerente_telefone,
        # Ação
        tipo_acao=dados.tipo_acao,
        # Requerido
        requerido_nome=dados.requerido_nome,
        requerido_qualificacao=dados.requerido_qualificacao,
        requerido_cpf_cnpj=dados.requerido_cpf_cnpj,
        requerido_endereco=dados.requerido_endereco,
        # Fatos
        data_fato_formatada=data_fato_formatada,
        fatos=fatos,
        # Fundamentos (RAG)
        fundamentos=fundamentos,
        # Pedidos
        requerimentos=dados.requerimentos,
        # Valor da causa
        valor_formatado=valor_formatado,
        valor_extenso=valor_extenso,
        # Data do documento
        data_formatada=data_formatada,
    )

    return JecResult(
        documento=documento,
        fatos=fatos,
        requerimentos=dados.requerimentos,
        chunks=chunks,
        avisos=[],
    )
