"""Gerenciamento de histórico de conversa em memória — JusBot.

Separação de responsabilidades:
- obter_historico()   → histórico COMPLETO, usado apenas para renderizar a página.
                        Nunca é descartado; o usuário sempre vê todos os turnos.
- historico_para_llm() → últimos _LIMITE_LLM mensagens (5 pares), sem dispositivos.
                         O corte acontece AQUI, na montagem das mensagens para o LLM,
                         não no armazenamento. Isso torna verdadeira a afirmação de
                         que o usuário vê o histórico completo.

Política de dispositivos: cada turno de assistente guarda os endereços legais
recuperados NAQUELE turno, para exibição. Eles nunca são reinjetados no prompt
dos turnos anteriores (ADR-013).

Thread-safety: adequado para uvicorn single-process (GIL protege append/assignment).
"""

from __future__ import annotations

import uuid

# { conversa_id: [ {"papel": "user"|"assistant", "texto": str, "dispositivos": [str]} ] }
_historicos: dict[str, list[dict]] = {}

_LIMITE_LLM = 10  # máximo de mensagens enviadas ao LLM (5 pares user+assistant)


def criar_conversa() -> str:
    """Inicializa uma nova conversa e retorna o conversa_id."""
    cid = str(uuid.uuid4())
    _historicos[cid] = []
    return cid


def obter_historico(conversa_id: str) -> list[dict]:
    """Retorna o histórico COMPLETO para renderização da página.

    Inclui o campo 'dispositivos' de cada turno de assistente.
    Lista vazia se conversa_id desconhecido (ex: após reinício do servidor).
    """
    return _historicos.get(conversa_id, [])


def adicionar_turno(
    conversa_id: str,
    papel: str,
    texto: str,
    dispositivos: list[str] | None = None,
) -> None:
    """Anexa uma mensagem ao histórico. Nunca descarta — exibição é sempre completa.

    Args:
        conversa_id: ID da conversa. Criado automaticamente se não existir.
        papel: "user" ou "assistant".
        texto: Conteúdo da mensagem (pergunta ou resposta).
        dispositivos: Endereços legais dos chunks (só para turnos de assistente).
    """
    if conversa_id not in _historicos:
        _historicos[conversa_id] = []
    _historicos[conversa_id].append(
        {
            "papel": papel,
            "texto": texto,
            "dispositivos": dispositivos or [],
        }
    )


def historico_para_llm(conversa_id: str) -> list[dict[str, str]]:
    """Retorna os últimos _LIMITE_LLM turnos formatados para o LLM.

    - Apenas "papel" e "texto" — dispositivos nunca são reinjetados (ADR-013).
    - Truncado a _LIMITE_LLM entradas para controlar o tamanho do prompt.
    - O truncamento acontece aqui, não no armazenamento.
    """
    entradas = _historicos.get(conversa_id, [])
    return [{"papel": e["papel"], "texto": e["texto"]} for e in entradas[-_LIMITE_LLM:]]
