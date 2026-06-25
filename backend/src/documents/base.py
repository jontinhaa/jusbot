"""Utilitários compartilhados pelos geradores de documentos jurídicos — JusBot.

Não contém lógica específica de nenhum documento. Cada módulo de documento
(notificacao.py, procon.py, peticao.py) importa daqui o que precisar.

Arquitetura: funções soltas, não classe base. As diferenças entre documentos
são de dados (template, campos do render, validação extra), não de comportamento
— herança traria cerimônia sem ganho real para três módulos procedurais.
"""

from __future__ import annotations

import re
from datetime import date as _date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from num2words import num2words as _num2words
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


def valor_centavos_extenso(centavos: int) -> tuple[str, str]:
    """Converte inteiro de centavos em (valor_formatado, valor_por_extenso).

    Exemplos:
        543000  → ("R$ 5.430,00", "cinco mil, quatrocentos e trinta reais")
        184753  → ("R$ 1.847,53", "mil, oitocentos e quarenta e sete reais e cinquenta e três centavos")
        100     → ("R$ 1,00", "um real")
        99      → ("R$ 0,99", "noventa e nove centavos")

    Defensivo: centavos <= 0 retorna marcadores em vez de quebrar
    (o schema DadosJec já barra gt=0, mas o helper não deve explodir se chamado isolado).
    Sem float em nenhum momento — reais e centavos obtidos por divisão inteira.
    """
    if centavos <= 0:
        return ("[A PREENCHER: valor]", "[A PREENCHER: valor por extenso]")

    reais = centavos // 100
    cents = centavos % 100

    # Formatação monetária: separador de milhar = ponto, decimal = vírgula
    reais_str = f"{reais:,}".replace(",", ".")
    valor_formatado = f"R$ {reais_str},{cents:02d}"

    # Extenso: monta partes separadas para não depender do formato de num2words de moeda dupla
    partes: list[str] = []
    if reais > 0:
        # to='currency' entrega concordância "um real" / "dois reais" automaticamente
        partes.append(_num2words(reais, lang="pt_BR", to="currency"))
    if cents > 0:
        cents_label = "centavo" if cents == 1 else "centavos"
        partes.append(f"{_num2words(cents, lang='pt_BR')} {cents_label}")

    valor_por_extenso = f"{partes[0]} e {partes[1]}" if len(partes) == 2 else partes[0]

    # Praxe forense: num2words omite "um" em valores 1.000-1.999 ("mil reais",
    # "mil, oitocentos..."). \b isola a palavra - nao casa "milhao"/"milhoes".
    if re.match(r"^mil\b", valor_por_extenso):
        valor_por_extenso = "um " + valor_por_extenso

    return (valor_formatado, valor_por_extenso)


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


# ─── Filtro de pertinência ───────────────────────────────────────────────────


def filtrar_pertinencia(relato: str, chunks: list[ContextualChunk]) -> list[ContextualChunk]:
    """Filtra os chunks recuperados pelo RAG para manter só os pertinentes ao relato.

    O LLM recebe a lista numerada de dispositivos e retorna APENAS os índices
    que se aplicam juridicamente ao relato. A saída é fechada ao conjunto de
    entrada: impossível introduzir dispositivo não recuperado.

    Fallback: se o parse falhar, vier vazio ou ocorrer exceção, retorna os
    chunks originais sem filtrar (degrada ao comportamento sem filtro).
    """
    if not chunks:
        return chunks

    lista_numerada = "\n".join(f"[{i}] {c.endereco}: {c.texto}" for i, c in enumerate(chunks, 1))

    system = (
        "Você é um assistente jurídico do sistema JusBot. "
        "Sua única tarefa é selecionar, de uma lista numerada de dispositivos legais, "
        "quais se aplicam juridicamente ao relato do usuário.\n\n"
        "REGRAS ABSOLUTAS:\n"
        "1. Responda APENAS com os números dos dispositivos pertinentes, separados por vírgula. "
        "Exemplo de resposta válida: 1,3,5\n"
        "2. NÃO escreva texto de lei. NÃO invente dispositivos. NÃO explique.\n"
        "3. Exclua dispositivos de área jurídica diferente do problema "
        "(ex: dispositivo sobre vício de serviço num caso de vício de produto).\n"
        "4. NA DÚVIDA sobre um dispositivo, INCLUA — preferimos manter um a mais "
        "que descartar um pertinente.\n"
        "5. Se absolutamente nenhum dispositivo for pertinente, responda com todos os números."
    )

    user_msg = (
        f"Relato do usuário:\n{relato}\n\n" f"Dispositivos legais recuperados:\n{lista_numerada}"
    )

    try:
        client = get_client()
        response = client.messages.create(
            model=_MODEL,
            max_tokens=50,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        indices = [int(x) for x in re.findall(r"\d+", raw)]
        validos = [i for i in indices if 1 <= i <= len(chunks)]
        if not validos:
            print(
                f"[filtrar_pertinencia] FALLBACK: índices vazios/inválidos "
                f"(raw={raw!r}, chunks={len(chunks)})"
            )
            return chunks
        vistos: set[int] = set()
        resultado: list[ContextualChunk] = []
        for i in validos:
            if i not in vistos:
                vistos.add(i)
                resultado.append(chunks[i - 1])
        return resultado
    except Exception as exc:
        print(
            f"[filtrar_pertinencia] FALLBACK: exceção no filtro " f"({type(exc).__name__}: {exc})"
        )
        return chunks


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


# ─── Montagem de fundamentos para templates ──────────────────────────────────

_TIPOS_FILHO: frozenset[str] = frozenset({"paragrafo", "inciso", "alinea", "item"})


def montar_fundamento(chunks: list[ContextualChunk]) -> list[dict]:
    """Constrói a lista de dicts de fundamentos que os templates iteram.

    Quando o dispositivo recuperado é filho de um artigo (parágrafo, inciso,
    alínea ou item), inclui o texto do caput-pai nos campos caput_*. Garante
    que o documento não cite o §6º isolado sem o artigo que o rege.

    Dedup por (documento, numero_do_artigo): se o artigo-pai já aparece como
    chunk recuperado diretamente na lista, caput_* = None — evita repetição.
    Usa (documento, numero) em vez de comparar enderecos porque o endereco do
    artigo recuperado pode incluir Título/Capítulo ("CDC, Cap. IV, Art. 18"),
    enquanto o caput_endereco é sempre a forma curta ("CDC, Art. 18").

    Formato de cada item:
        {
            "endereco":       str,        # endereço do dispositivo recuperado
            "texto":          str,        # texto do dispositivo recuperado
            "caput_endereco": str | None, # ex: "CDC, Art. 18" (None se não aplicável)
            "caput_texto":    str | None, # texto do caput do artigo-pai (None se não aplicável)
        }
    """
    artigos_recuperados: set[tuple[str, str]] = {
        (c.documento, c.numero) for c in chunks if c.tipo == "artigo"
    }

    result: list[dict] = []
    for c in chunks:
        caput_endereco: str | None = None
        caput_texto: str | None = None

        if c.tipo in _TIPOS_FILHO:
            artigo_anc = next(
                (a for a in c.ancestrais if a.tipo == "artigo"),
                None,
            )
            if (
                artigo_anc is not None
                and (c.documento, artigo_anc.numero) not in artigos_recuperados
            ):
                doc_short = c.endereco.split(", ", 1)[0]
                caput_endereco = f"{doc_short}, Art. {artigo_anc.numero}"
                caput_texto = artigo_anc.texto

        result.append(
            {
                "endereco": c.endereco,
                "texto": c.texto,
                "caput_endereco": caput_endereco,
                "caput_texto": caput_texto,
            }
        )

    return result


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
