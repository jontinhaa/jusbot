"""Utilitários compartilhados pelos geradores de documentos jurídicos — JusBot.

Não contém lógica específica de nenhum documento. Cada módulo de documento
(notificacao.py, procon.py, peticao.py) importa daqui o que precisar.

Arquitetura: funções soltas, não classe base. As diferenças entre documentos
são de dados (template, campos do render, validação extra), não de comportamento
— herança traria cerimônia sem ganho real para três módulos procedurais.
"""

from __future__ import annotations

from datetime import date as _date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sqlalchemy.orm import Session

from src.generation.client import _MODEL, get_client
from src.rag.retrieval import ContextualChunk, build_context, search_hybrid

# Diretório de templates compartilhado por todos os documentos
TEMPLATES_DIR = Path(__file__).parent / "templates"

# ─── Helpers de formatação ────────────────────────────────────────────────────

_MESES_PT: dict[int, str] = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}

_EXTENSO: dict[int, str] = {
    1: "um",
    2: "dois",
    3: "três",
    4: "quatro",
    5: "cinco",
    6: "seis",
    7: "sete",
    8: "oito",
    9: "nove",
    10: "dez",
    11: "onze",
    12: "doze",
    13: "treze",
    14: "quatorze",
    15: "quinze",
    16: "dezesseis",
    17: "dezessete",
    18: "dezoito",
    19: "dezenove",
    20: "vinte",
    30: "trinta",
    45: "quarenta e cinco",
    60: "sessenta",
    90: "noventa",
    120: "cento e vinte",
    180: "cento e oitenta",
}


def dias_extenso(n: int) -> str:
    """Converte inteiro para extenso. Cobre os valores típicos de prazo jurídico."""
    if n in _EXTENSO:
        return _EXTENSO[n]
    if n < 100:
        dezena = (n // 10) * 10
        unidade = n % 10
        if dezena in _EXTENSO and unidade in _EXTENSO:
            return f"{_EXTENSO[dezena]} e {_EXTENSO[unidade]}"
    return str(n)


def formatar_data(d: _date) -> str:
    """Formata date como 'D de mês de AAAA' em português."""
    return f"{d.day} de {_MESES_PT[d.month]} de {d.year}"


# ─── Filtro Jinja2 ────────────────────────────────────────────────────────────


def filtro_preencher(value: str | None, label: str) -> str:
    """None ou vazio → '[A PREENCHER: <label>]', senão o valor."""
    if value is None or str(value).strip() == "":
        return f"[A PREENCHER: {label}]"
    return str(value)


# ─── RAG ─────────────────────────────────────────────────────────────────────


def buscar_fundamento(
    session: Session,
    emb_model: Any,
    relato: str,
    k: int = 8,
    area: str | None = None,
) -> list[ContextualChunk]:
    """Executa o retrieval híbrido com filtro de área e monta o contexto hierárquico."""
    hybrid_items = search_hybrid(session, emb_model, relato, k=k, area=area)
    return build_context(session, hybrid_items)


# ─── Geração de fatos via LLM ─────────────────────────────────────────────────


def redigir_fatos(
    relato: str,
    tipo_documento: str = "notificação extrajudicial",
) -> str:
    """LLM redige a seção DOS FATOS em linguagem jurídica formal.

    Usa EXCLUSIVAMENTE o que o usuário narrou — não acrescenta, não presume.
    O parâmetro tipo_documento nomeia o documento no system prompt para que o
    LLM ajuste o registro se necessário (ex: 'reclamação ao PROCON').
    """
    system = (
        f"Você é um redator de documentos jurídicos do sistema JusBot. "
        f"Sua tarefa é redigir a seção 'DOS FATOS' de uma {tipo_documento}.\n\n"
        "REGRAS ABSOLUTAS:\n"
        "1. Use EXCLUSIVAMENTE os fatos narrados pelo usuário. Não invente, não presuma, "
        "não acrescente detalhes que não foram mencionados.\n"
        "2. Escreva em linguagem formal, em 3ª pessoa, no tempo passado.\n"
        "3. Mencione datas, valores e nomes APENAS se o usuário os forneceu explicitamente.\n"
        "4. Seja conciso: 2 a 4 parágrafos.\n"
        "5. NÃO inclua fundamentação legal — isso vai em seção separada.\n"
        "6. NÃO inclua cabeçalho, título da seção nem texto introdutório. "
        "Retorne apenas o corpo da narrativa factual."
    )

    client = get_client()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=800,
        system=system,
        messages=[{"role": "user", "content": f"Relato do usuário:\n{relato}"}],
    )
    return response.content[0].text.strip()


# ─── Validação base ───────────────────────────────────────────────────────────


def validar_campos_base(fatos: str, chunks: list[ContextualChunk]) -> list[str]:
    """Verifica os campos obrigatórios comuns a qualquer documento.

    Retorna lista de descrições do que falta (vazia = tudo ok).
    Cada módulo de documento chama isso, acrescenta suas próprias verificações
    e levanta seu próprio erro com a lista combinada.
    """
    faltando: list[str] = []
    if not fatos.strip():
        faltando.append("fatos (LLM retornou vazio)")
    if not chunks:
        faltando.append("fundamento_legal (RAG não encontrou dispositivos na área declarada)")
    return faltando


# ─── Ambiente Jinja2 ─────────────────────────────────────────────────────────


def criar_jinja_env(templates_dir: Path = TEMPLATES_DIR) -> Environment:
    """Cria Environment Jinja2 com o filtro 'preencher' registrado."""
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["preencher"] = filtro_preencher
    return env
