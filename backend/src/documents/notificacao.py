"""Geração de notificação extrajudicial — JusBot, Semana 8.

Pipeline:
    relato → RAG com filtro de área → fatos via LLM
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
from datetime import date

from sqlalchemy.orm import Session

from src.rag.retrieval import ContextualChunk

from .base import (
    TEMPLATES_DIR,
    buscar_fundamento,
    criar_jinja_env,
    dias_extenso,
    filtrar_pertinencia,
    formatar_data,
    montar_fundamento,
    redigir_fatos,
    validar_campos_base,
)
from .schemas import DadosCaso, NotificacaoResult

_TEMPLATE_NAME = "notificacao_extrajudicial.jinja2"


class NotificacaoError(Exception):
    pass


def _validar_campos(
    dados: DadosCaso,
    fatos: str,
    chunks: list[ContextualChunk],
) -> None:
    """Validação específica da notificação: base + requerimentos não-vazio.

    Campos opcionais (qualificação do notificado, endereço, etc.) nunca disparam
    erro — ficam como marcador [A PREENCHER] no documento.
    """
    faltando = validar_campos_base(fatos, chunks)
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
    chunks = buscar_fundamento(session, emb_model, relato, k=k, area=dados.area)
    chunks = filtrar_pertinencia(relato, chunks)

    # Etapa 2 — LLM redige apenas os fatos (ancorado no relato, nunca nos dados duros)
    fatos = redigir_fatos(relato)

    # Etapa 3 — Validação estrutural: recusa devolver peça incompleta
    _validar_campos(dados, fatos, chunks)

    # Etapa 4 — Renderiza o template com dados duros + conteúdo gerado/fornecido
    env = criar_jinja_env(TEMPLATES_DIR)
    documento = env.get_template(_TEMPLATE_NAME).render(
        # Notificante
        notificante_nome=dados.notificante_nome,
        notificante_cpf=dados.notificante_cpf,
        notificante_qualificacao=dados.notificante_qualificacao,
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
        prazo_dias_extenso=dias_extenso(dados.prazo_dias),
        cidade=dados.cidade,
        data_formatada=formatar_data(dados.data),
        # Conteúdo
        fatos=fatos,
        requerimentos=dados.requerimentos,
        fundamento_legal=montar_fundamento(chunks),
    )

    return NotificacaoResult(
        documento=documento,
        fatos=fatos,
        requerimentos=dados.requerimentos,
        chunks=chunks,
    )


# ─── Testes standalone ───────────────────────────────────────────────────────


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
        print("ERRO: DATABASE_URL não definida no .env", file=sys.stderr)
        sys.exit(1)

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

    engine, model = _setup_engine_e_model()

    dados = DadosCaso(
        notificante_nome="Maria da Silva",
        notificante_qualificacao="brasileira, casada, professora",
        notificante_cpf="123.456.789-00",
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

    engine, model = _setup_engine_e_model()

    dados = DadosCaso(
        notificante_nome="João Pereira dos Santos",
        notificante_qualificacao="brasileiro, solteiro, operador de máquinas",
        notificante_cpf="987.654.321-00",
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

    modo = sys.argv[1] if len(sys.argv) > 1 else "a"
    if modo == "a":
        _teste_a_consumidor()
    elif modo == "b":
        _teste_b_trabalhista()
    else:
        _teste_a_consumidor()
        print("\n\n")
        _teste_b_trabalhista()
