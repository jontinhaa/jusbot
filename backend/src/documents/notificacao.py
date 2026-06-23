"""Geração de notificação extrajudicial — JusBot, Semana 8.

Pipeline:
    relato → RAG (search_hybrid + build_context) → fatos via LLM
           → validação estrutural → render Jinja2 → NotificacaoResult

Divisão de responsabilidades:
  LLM     → apenas DOS FATOS (item 1): narrativa em 3ª pessoa do relato do usuário
  RAG     → DO FUNDAMENTO LEGAL (item 2): dispositivos recuperados por search_hybrid
  Usuário → DO REQUERIMENTO (item 3, alíneas): DadosCaso.requerimentos, não gerado
  Template → consequência fixa do não-atendimento (texto imutável no .jinja2)

O LLM nunca preenche nome, CPF/CNPJ ou valor — vêm exclusivamente do formulário.
"""

from __future__ import annotations

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sqlalchemy.orm import Session

from src.generation.client import _MODEL, get_client
from src.rag.retrieval import ContextualChunk, build_context, search_hybrid

from .schemas import DadosCaso, NotificacaoResult

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_TEMPLATE_NAME = "notificacao_extrajudicial.jinja2"

_MESES_PT = {
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


class NotificacaoError(Exception):
    pass


def _dias_extenso(n: int) -> str:
    if n in _EXTENSO:
        return _EXTENSO[n]
    if n < 100:
        dezena = (n // 10) * 10
        unidade = n % 10
        if dezena in _EXTENSO and unidade in _EXTENSO:
            return f"{_EXTENSO[dezena]} e {_EXTENSO[unidade]}"
    return str(n)


def _formatar_data(d: object) -> str:
    from datetime import date as date_type

    assert isinstance(d, date_type)
    return f"{d.day} de {_MESES_PT[d.month]} de {d.year}"


def _filtro_preencher(value: str | None, label: str) -> str:
    """Filtro Jinja2: None ou vazio → '[A PREENCHER: <label>]', senão o valor."""
    if value is None or str(value).strip() == "":
        return f"[A PREENCHER: {label}]"
    return str(value)


def _redigir_fatos(relato: str) -> str:
    """LLM redige a seção DOS FATOS em linguagem jurídica formal.

    Usa EXCLUSIVAMENTE o que o usuário narrou — não acrescenta, não presume.
    """
    system = (
        "Você é um redator de documentos jurídicos do sistema JusBot. "
        "Sua tarefa é redigir a seção 'DOS FATOS' de uma notificação extrajudicial.\n\n"
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


def _validar_campos(
    dados: DadosCaso,
    fatos: str,
    chunks: list[ContextualChunk],
) -> None:
    """Verifica presença dos campos obrigatórios antes de renderizar.

    Campos opcionais (qualificação do notificado, endereço, etc.) nunca disparam erro —
    ficam como marcador [A PREENCHER] no documento.
    """
    faltando: list[str] = []
    if not fatos.strip():
        faltando.append("fatos (LLM retornou vazio)")
    if not chunks:
        faltando.append("fundamento_legal (RAG não encontrou dispositivos relevantes)")
    if not dados.requerimentos:
        faltando.append("requerimentos (lista vazia — ao menos um item obrigatório)")
    if faltando:
        raise NotificacaoError(
            "Campos obrigatórios ausentes na notificação: " + ", ".join(faltando)
        )


def gerar_notificacao(
    dados: DadosCaso,
    relato: str,
    session: Session,
    emb_model: object,
    k: int = 8,
) -> NotificacaoResult:
    """Gera rascunho de notificação extrajudicial para o caso descrito.

    Args:
        dados: Campos duros confirmados pelo usuário. O LLM não preenche nenhum destes.
               dados.requerimentos define as alíneas do item 3 (voz do usuário, não do LLM).
        relato: Texto livre do usuário descrevendo o que aconteceu.
        session: Sessão SQLAlchemy com acesso ao banco de chunks.
        emb_model: Modelo sentence-transformers já carregado.
        k: Número de dispositivos legais a recuperar via RAG (default 8).

    Returns:
        NotificacaoResult com documento renderizado, fatos, requerimentos e chunks usados.

    Raises:
        NotificacaoError: Se campos obrigatórios (fatos, chunks, requerimentos) estiverem
                          ausentes no resultado.
    """
    # Etapa 1 — RAG: recupera dispositivos da área declarada pelo usuário
    hybrid_items = search_hybrid(session, emb_model, relato, k=k, area=dados.area)
    chunks = build_context(session, hybrid_items)

    # Etapa 2 — LLM redige apenas os fatos (ancorado no relato, nunca nos dados duros)
    fatos = _redigir_fatos(relato)

    # Etapa 3 — Validação estrutural: recusa devolver peça incompleta
    _validar_campos(dados, fatos, chunks)

    # Etapa 4 — Renderiza o template com dados duros + conteúdo gerado/fornecido
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["preencher"] = _filtro_preencher

    template = env.get_template(_TEMPLATE_NAME)

    fundamento_legal = [{"endereco": c.endereco, "texto": c.texto} for c in chunks]

    documento = template.render(
        # Notificante
        notificante_nome=dados.notificante_nome,
        notificante_cpf=dados.notificante_cpf,
        notificante_qualificacao=dados.notificante_qualificacao,
        notificante_nacionalidade=dados.notificante_nacionalidade,
        notificante_estado_civil=dados.notificante_estado_civil,
        notificante_profissao=dados.notificante_profissao,
        notificante_endereco=dados.notificante_endereco,
        # Notificado
        notificado_nome=dados.notificado_nome,
        notificado_qualificacao=dados.notificado_qualificacao,
        notificado_nacionalidade=dados.notificado_nacionalidade,
        notificado_estado_civil=dados.notificado_estado_civil,
        notificado_profissao=dados.notificado_profissao,
        notificado_cpf_cnpj=dados.notificado_cpf_cnpj,
        notificado_endereco=dados.notificado_endereco,
        # Caso
        assunto=dados.assunto,
        prazo_dias=dados.prazo_dias,
        prazo_dias_extenso=_dias_extenso(dados.prazo_dias),
        cidade=dados.cidade,
        data_formatada=_formatar_data(dados.data),
        # Conteúdo
        fatos=fatos,
        requerimentos=dados.requerimentos,
        fundamento_legal=fundamento_legal,
    )

    return NotificacaoResult(
        documento=documento,
        fatos=fatos,
        requerimentos=dados.requerimentos,
        chunks=chunks,
    )


# ─── Teste standalone ────────────────────────────────────────────────────────


def _setup_engine_e_model() -> tuple[object, object]:
    import sys
    import time
    from pathlib import Path

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from sqlalchemy import create_engine

    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        import sys as _sys

        print("ERRO: DATABASE_URL não definida no .env", file=_sys.stderr)
        _sys.exit(1)

    db_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(db_url, echo=False)

    print("Carregando intfloat/multilingual-e5-large...", flush=True)
    t0 = time.time()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("intfloat/multilingual-e5-large")
    print(f"Modelo pronto em {time.time() - t0:.1f}s\n", flush=True)

    return engine, model


def _teste_a_consumidor() -> None:
    """(a) Internet abaixo da velocidade, area='consumidor' — deve trazer CDC."""
    import time
    from datetime import date

    engine, model = _setup_engine_e_model()

    dados = DadosCaso(
        notificante_nome="Maria da Silva",
        notificante_qualificacao="consumidora",
        notificante_cpf="123.456.789-00",
        notificante_nacionalidade="brasileira",
        notificante_estado_civil="casada",
        notificante_profissao="professora",
        notificante_endereco="Rua das Palmeiras, 123, Bairro Centro, Paragominas/PA, CEP 68.625-000",
        notificado_nome="TeleconBrasil S.A.",
        notificado_qualificacao="empresa prestadora de serviços de telecomunicações",
        notificado_cpf_cnpj=None,
        notificado_endereco=None,
        requerimentos=[
            "forneça a velocidade de internet de 100 Mbps contratada em janeiro de 2026, "
            "conforme pactuado no contrato de prestação de serviços",
            "apresente comprovante técnico de adequação do serviço ao padrão contratado "
            "dentro do prazo acima fixado",
            "abstenha-se de cobrar pelo período em que o serviço foi prestado abaixo do "
            "padrão contratado, sob pena de devolução em dobro (CDC, art. 42, par. único)",
        ],
        area="consumidor",
        assunto=(
            "Descumprimento contratual — prestação de serviço de internet "
            "abaixo da velocidade contratada (100 Mbps entregue a 10 Mbps)"
        ),
        prazo_dias=15,
        cidade="Paragominas",
        data=date(2026, 6, 23),
    )

    relato = (
        "Contratei um plano de internet banda larga de 100 Mbps com a empresa TeleconBrasil "
        "em janeiro de 2026, pelo valor mensal de R$ 99,90. Desde a instalação, a velocidade "
        "nunca ultrapassou 10 Mbps, ou seja, apenas 10% do que foi contratado e que estou "
        "pagando. Realizei três ligações para o serviço de atendimento ao cliente nos meses "
        "de fevereiro, março e abril de 2026, mas o problema não foi resolvido. Continuo "
        "pagando a mensalidade integralmente por um serviço que não é entregue conforme contratado."
    )

    print("=" * 72)
    print("TESTE (a) — CONSUMIDOR | area='consumidor'")
    print(f"  Notificado: {dados.notificado_nome} | CPF/CNPJ: {dados.notificado_cpf_cnpj}")
    print("=" * 72)

    from sqlalchemy.orm import Session

    t1 = time.time()
    try:
        with Session(engine) as session:
            resultado = gerar_notificacao(dados, relato, session, model)
        elapsed = time.time() - t1
        print(f"Gerado em {elapsed:.1f}s\n")
        print(f"Dispositivos recuperados ({len(resultado.chunks)}):")
        for c in resultado.chunks:
            print(f"  • {c.endereco}  [area={c.area_juridica}]  [rrf={c.score_rrf:.4f}]")
        print("\n" + "=" * 72)
        print("DOCUMENTO GERADO:")
        print("=" * 72)
        print(resultado.documento)
    except NotificacaoError as e:
        elapsed = time.time() - t1
        print(f"\n*** NotificacaoError em {elapsed:.1f}s: {e} ***\n")


def _teste_b_trabalhista() -> None:
    """(b) Demissão sem justa causa, area='trabalho' — deve trazer CLT."""
    import time
    from datetime import date

    engine, model = _setup_engine_e_model()

    dados = DadosCaso(
        notificante_nome="João Pereira dos Santos",
        notificante_qualificacao="trabalhador",
        notificante_cpf="987.654.321-00",
        notificante_nacionalidade="brasileiro",
        notificante_estado_civil="solteiro",
        notificante_profissao="operador de máquinas",
        notificante_endereco="Av. Brasil, 456, Bairro Industrial, Paragominas/PA, CEP 68.625-100",
        notificado_nome="Mineradora Alfa Ltda.",
        notificado_qualificacao="empresa do setor de mineração, empregadora do notificante",
        notificado_cpf_cnpj=None,
        notificado_endereco=None,
        requerimentos=[
            "pague as verbas rescisórias devidas pela demissão sem justa causa: aviso prévio, "
            "saldo de salário, férias proporcionais acrescidas de 1/3 e 13º proporcional",
            "libere o saque do FGTS com a multa de 40% sobre o saldo, nos termos do art. 18 "
            "da Lei 8.036/1990",
            "forneça as guias do seguro-desemprego (SD/CD) dentro do prazo legal",
        ],
        area="trabalho",
        assunto="Verbas rescisórias — demissão sem justa causa não quitada",
        prazo_dias=10,
        cidade="Paragominas",
        data=date(2026, 6, 23),
    )

    relato = (
        "Trabalhei na empresa Mineradora Alfa Ltda. como operador de máquinas por 3 anos. "
        "Fui demitido sem justa causa em 10 de junho de 2026. A empresa não pagou nenhuma "
        "das verbas rescisórias até hoje: não recebi aviso prévio, férias proporcionais, "
        "13º salário proporcional nem saldo de salário do mês de junho. Também não liberaram "
        "o FGTS com a multa de 40% nem me entregaram as guias do seguro-desemprego. "
        "Tentei contato com o RH da empresa em 15 e 20 de junho, sem resposta."
    )

    print("=" * 72)
    print("TESTE (b) — TRABALHISTA | area='trabalho'")
    print(f"  Notificado: {dados.notificado_nome} | CPF/CNPJ: {dados.notificado_cpf_cnpj}")
    print("=" * 72)

    from sqlalchemy.orm import Session

    t1 = time.time()
    try:
        with Session(engine) as session:
            resultado = gerar_notificacao(dados, relato, session, model)
        elapsed = time.time() - t1
        print(f"Gerado em {elapsed:.1f}s\n")
        print(f"Dispositivos recuperados ({len(resultado.chunks)}):")
        for c in resultado.chunks:
            print(f"  • {c.endereco}  [area={c.area_juridica}]  [rrf={c.score_rrf:.4f}]")
        print("\n" + "=" * 72)
        print("DOCUMENTO GERADO:")
        print("=" * 72)
        print(resultado.documento)
    except NotificacaoError as e:
        elapsed = time.time() - t1
        print(f"\n*** NotificacaoError em {elapsed:.1f}s: {e} ***\n")


if __name__ == "__main__":
    import sys

    modo = sys.argv[1] if len(sys.argv) > 1 else "ambos"
    if modo == "a":
        _teste_a_consumidor()
    elif modo == "b":
        _teste_b_trabalhista()
    else:
        _teste_a_consumidor()
        print("\n\n")
        _teste_b_trabalhista()
