"""Reformulação de perguntas de acompanhamento — JusBot.

Converte perguntas com referências implícitas ("e o FGTS?") em perguntas
autônomas antes da busca RAG. A pergunta original é preservada para o
prompt de geração; a reformulada serve apenas para retrieval.

Os pares original/reformulada são logados para uso na avaliação empírica.
"""

from __future__ import annotations

import logging

import anthropic

logger = logging.getLogger(__name__)

_SYSTEM_REFORMULADOR = """\
Você recebe o histórico de uma conversa jurídica e a última pergunta do usuário.
Reescreva essa pergunta de forma que ela faça sentido sozinha, sem depender do histórico.

REGRAS:
- Resolva pronomes e referências implícitas ("ele" → quem é, "e o FGTS?" → a pergunta \
completa sobre FGTS no contexto discutido).
- NÃO adicione temas, teses, consequências jurídicas ou dispositivos que não estejam \
na conversa. Você resolve referências, não expande o assunto.
- NÃO responda a pergunta. Apenas reescreva.
- Se a pergunta já é autônoma e não depende do histórico, devolva-a sem alteração.
- Devolva APENAS a pergunta reescrita, sem preâmbulo, sem aspas, sem markdown.\
"""


def _formatar_historico(historico: list[dict[str, str]]) -> str:
    linhas: list[str] = []
    for entrada in historico:
        papel = "Usuário" if entrada["papel"] == "user" else "Assistente"
        linhas.append(f"{papel}: {entrada['texto']}")
    return "\n".join(linhas)


def reformular_pergunta(
    pergunta: str,
    historico: list[dict[str, str]],
    llm: anthropic.Anthropic,
) -> str:
    """Reescreve a pergunta em forma autônoma se houver histórico.

    Primeiro turno (histórico vazio): devolve a pergunta inalterada, sem
    gastar chamada ao LLM.

    Returns:
        Pergunta reescrita (ou original se primeiro turno / já autônoma).
    """
    if not historico:
        logger.info("[reformulador] turno 1 — sem reformulação | original: %r", pergunta)
        return pergunta

    historico_fmt = _formatar_historico(historico)
    user_message = (
        f"HISTÓRICO DA CONVERSA:\n{historico_fmt}\n\n" f"ÚLTIMA PERGUNTA DO USUÁRIO:\n{pergunta}"
    )

    response = llm.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=_SYSTEM_REFORMULADOR,
        messages=[{"role": "user", "content": user_message}],
    )
    reformulada = response.content[0].text.strip()

    logger.info("[reformulador] original: %r | reformulada: %r", pergunta, reformulada)
    return reformulada
