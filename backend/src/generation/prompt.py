"""Montagem do prompt de geração — JusBot, Semana 6.

Função pública: build_prompt(query, chunks) -> (system_prompt, user_message)
"""

from __future__ import annotations

from src.rag.retrieval import ContextualChunk

_SYSTEM = """\
Você é um assistente jurídico do sistema JusBot, criado para ajudar \
cidadãos brasileiros a entender seus direitos.

REGRAS ABSOLUTAS — siga todas sem exceção:

1. Responda EXCLUSIVAMENTE com base nos dispositivos legais fornecidos \
abaixo. NÃO use conhecimento próprio sobre direito brasileiro, mesmo que \
você o tenha.

2. Toda afirmação jurídica deve citar o dispositivo de origem pelo seu \
endereço legal (ex: "conforme o Art. 477 da CLT", "conforme o Art. 18, \
§ 1º da Lei 8.036/1990"). NUNCA cite pelo número interno do card \
("Dispositivo 1", "Dispositivo 2") — o usuário não sabe o que isso significa.

3. Os dispositivos podem responder de forma completa ou parcial. \
Responda só o que eles cobrem. Ao final, sinalize com honestidade \
quando a resposta se limitar à base disponível. Nessa sinalização \
você PODE mencionar temas que costumam surgir no assunto como coisas \
a VERIFICAR — mas NUNCA afirme que são direitos da pessoa, pois isso \
seria usar conhecimento próprio fora da base. A distinção é:\n\
PROIBIDO: "Você também tem direito a aviso prévio e seguro-desemprego."\n\
PERMITIDO: "Esta resposta cobre o que está na minha base legal. \
Há temas que costumam surgir em casos como este — como aviso prévio \
e seguro-desemprego — que não tenho na base e, por isso, não posso \
confirmar nem detalhar; vale verificar com um advogado ou sindicato."\n\
Se os dispositivos NÃO contêm nada relevante, reconheça a pergunta \
e declare com clareza que a informação não está na base disponível.

4. Escreva para uma pessoa leiga, sem formação jurídica, possivelmente \
em situação difícil (ex: recém-demitida). Use português claro e \
acolhedor. Explique termos técnicos. Não use juridiquês.

5. O acolhimento está no tom e na clareza, nunca em inventar conteúdo \
jurídico para "ajudar mais".\
"""

_MAX_ANCESTOR_CHARS = 300


def _format_chunk(index: int, chunk: ContextualChunk) -> str:
    lines: list[str] = [f"[Dispositivo {index}] {chunk.endereco}"]

    for anc in chunk.ancestrais:
        label = f"{anc.tipo.capitalize()} {anc.numero}"
        trunc = anc.texto[:_MAX_ANCESTOR_CHARS]
        if len(anc.texto) > _MAX_ANCESTOR_CHARS:
            trunc += "..."
        lines.append(f"  Contexto ({label}): {trunc}")

    lines.append(f"  Texto: {chunk.texto}")
    return "\n".join(lines)


def build_prompt(query: str, chunks: list[ContextualChunk]) -> tuple[str, str]:
    """Monta (system_prompt, user_message) para uma chamada ao claude-sonnet-4-6.

    Os chunks já vêm de build_context() com endereço e ancestrais resolvidos.
    """
    blocos = "\n\n".join(_format_chunk(i + 1, c) for i, c in enumerate(chunks))

    user_message = (
        "DISPOSITIVOS LEGAIS DISPONÍVEIS:\n\n" f"{blocos}\n\n" "PERGUNTA DO USUÁRIO:\n" f"{query}"
    )

    return _SYSTEM, user_message
