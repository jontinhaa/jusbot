"""
Parser HTML para leis do Planalto.gov.br (encoding cp1252/Windows-1252).

Extrai dispositivos (artigo, parágrafo, inciso, alínea, item) conforme a
taxonomia da LC 95/1998 (ADR-009) e insere em documents + chunks
respeitando o schema v2 (parent_chunk_id FK auto-referencial — ADR-007).

Regras de anotação:
  (Incluído pela Lei nº X)      → extraído para alterado_por, removido do texto
  (Redação dada pela Lei nº X)  → idem
  (Revogado)                    → chunk inteiro pulado, não inserido
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# .env está dois níveis acima de backend/
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# ──────────────────────────────────────────────────────────────────────────────
# Padrões de texto (aplicados após limpeza de HTML)
# ──────────────────────────────────────────────────────────────────────────────

# Tracos usados em dispositivos: hifen, en-dash, em-dash
_TRACOS = r"[-\u2013\u2014]"

# Artigo: "Art. 1° -" (4.090), "Art. 18. texto" (CDC com ponto), "Art. 15. (Vetado)"
# "Art . 597." (CLT — FrontPage insere espaço antes do ponto em alguns artigos revogados)
# Ponto apos ordinal captura articulacao do CDC; traco opcional mantem formato da 4.090
_ART = re.compile(
    r"^Art\s*\.?\s*(\d[a-zA-Z\d-]*)\s*[°º]?\s*\.?\s*" + _TRACOS + r"?\s*(.*)",
    re.DOTALL | re.IGNORECASE,
)

# Paragrafo numerado: "§ 1° -" (4.090), "§ 1° texto" (CDC sem traco), "§ 1 º" (espaco antes do ordinal)
_PAR = re.compile(r"^§\s*(\d+)\s*[°º]?\s*" + _TRACOS + r"?\s*(.*)", re.DOTALL)

# Parágrafo único
_PAR_UNICO = re.compile(r"^Parágrafo único", re.IGNORECASE)

# Inciso: apenas algarismos romanos maiúsculos seguidos de traço
_INC = re.compile(r"^([IVXLCDM]+)\s*" + _TRACOS + r"\s*(.*)", re.DOTALL)

# Alínea: "a)", "b)"
_ALI = re.compile(r"^([a-z])\)\s*(.*)", re.DOTALL)

# Extrai número e ano de anotações: "Lei nº 9.011, de 1995" → ("9.011", "1995")
_LEI_NUM = re.compile(r"n[°º.]?\s*([\d.]+)[,\s]+de\s+(\d{4})", re.IGNORECASE)

# Caput que inicia com marcador de veto/revogação — chunk deve ser descartado.
# Usa prefixo (\b) em vez de âncora final: captura "(Revogado).", "(Revogado). (Vigência)", etc.
_MARCADOR = re.compile(r"^\((?:Vetado|Revogad[oa])\b", re.IGNORECASE)

# Mínimo de chars alfanuméricos antes do primeiro ";" no corpo de uma alínea.
# Abaixo disto: artefato HTML (separador de dispositivo que vazou para o <p> da alínea).
_MIN_ALI_CORPO = 5


def _classify_tipo(text: str) -> tuple[str, str]:
    """Retorna (tipo, numero) usando os mesmos detectores do pipeline de vigentes.

    Fonte única de verdade para classificar o tipo de um dispositivo — usada tanto
    no pipeline de chunks vigentes quanto no registro de descartados, garantindo
    que alíneas revogadas não caiam como 'desconhecido'.
    """
    m = _ART.match(text)
    if m:
        return "artigo", m.group(1)
    if _PAR_UNICO.match(text):
        return "paragrafo", "único"
    m = _PAR.match(text)
    if m:
        return "paragrafo", m.group(1)
    m = _INC.match(text)
    if m:
        return "inciso", m.group(1)
    m = _ALI.match(text)
    if m:
        return "alinea", m.group(1)
    return "desconhecido", "-"


def _ali_corpo_util(body: str) -> bool:
    """True se o corpo da alínea tem >= _MIN_ALI_CORPO chars alfanum antes do primeiro ';'.

    Alíneas cujo texto começa com ';' são artefatos de formatação HTML do Planalto:
    o ponto-e-vírgula separador do inciso pai vazou para o <p> da alínea filho.
    Esses elementos não representam dispositivos legais e não devem ir nem para metadata.
    """
    pre_semi = re.split(r";", body.lstrip())[0]
    return sum(1 for c in pre_semi if c.isalpha() or c.isdigit()) >= _MIN_ALI_CORPO


def _dispositivo_from_href(href: str) -> str | None:
    """Converte o fragment de um href em rótulo legível: 'L9011.htm#art1' → 'art. 1'."""
    frag = href.split("#", 1)[-1] if "#" in href else ""
    m = re.match(r"art(\d+[\w-]*)", frag, re.IGNORECASE)
    return f"art. {m.group(1)}" if m else None


# ──────────────────────────────────────────────────────────────────────────────
# Estrutura intermediária (antes de ter IDs do banco)
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class _ChunkDraft:
    tipo: str
    numero: str
    texto: str
    posicao_ordem: int
    caminho_hierarquico: dict[str, str] | None
    chunk_key: str  # chave lógica para construir parent_chunk_id
    parent_key: str | None  # chave lógica do pai (None = raiz)
    alterado_por: dict[str, Any] | None = None
    metadata_: dict[str, Any] | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Processamento de um <p>: extrai texto limpo e anotações
# ──────────────────────────────────────────────────────────────────────────────


def _process_annotation_a(a: Any, p: Tag) -> tuple[dict[str, Any] | None, bool]:
    """Processa um único <a> de anotação parentética dentro de p.

    Retorna (alterado_por | None, is_revogado).
    O HTML do FrontPage aninha <p> dentro de <p> (inválido mas preservado pelo BS4).
    find_all("a") traversa todos os descendentes — só processa <a> cujo ancestral
    <p> mais próximo é o próprio p, para evitar capturar links de artigos aninhados.
    """
    if a.find_parent("p") is not p:
        return None, False

    link_text = a.get_text(strip=True)
    if not link_text.startswith("("):
        return None, False  # âncora de navegação <a name="...">

    href = a.get("href", "")

    if re.search(r"Revogad[oa]|Vetado", link_text, re.IGNORECASE):
        a.decompose()
        return None, True

    if re.search(r"Incluíd[oa]", link_text, re.IGNORECASE):
        m = _LEI_NUM.search(link_text)
        alt = (
            {
                "tipo": "inclusao",
                "lei": f"{m.group(1)}/{m.group(2)}",
                "url": href,
                "dispositivo_alterado": _dispositivo_from_href(href),
                "data_publicacao": None,
            }
            if m
            else None
        )
        a.decompose()
        return alt, False

    if re.search(r"Redação dada", link_text, re.IGNORECASE):
        m = _LEI_NUM.search(link_text)
        alt = (
            {
                "tipo": "redacao",
                "lei": f"{m.group(1)}/{m.group(2)}",
                "url": href,
                "dispositivo_alterado": _dispositivo_from_href(href),
                "data_publicacao": None,
            }
            if m
            else None
        )
        a.decompose()
        return alt, False

    a.unwrap()  # outras anotações parentéticas: remove link, mantém texto
    return None, False


def _process_p(p: Tag) -> tuple[str, dict[str, Any] | None, bool]:
    """
    Retorna (texto_limpo, alterado_por | None, is_revogado).
    Decompõe in-place as <a> de anotação parentéticas.
    """
    alterado_por: dict[str, Any] | None = None
    is_revogado = False

    for a in p.find_all("a"):
        alt, rev = _process_annotation_a(a, p)
        if rev:
            is_revogado = True
        if alt:
            alterado_por = alt

    # Detecta (Vetado)/(Revogado) em <font> — padrão do CDC (não usa <a>)
    # Exige parênteses para não casar com "revogadas as disposições em contrário"
    for font in p.find_all("font"):
        if re.search(r"\((?:Revogad[oa]|Vetado)", font.get_text(strip=True), re.IGNORECASE):
            is_revogado = True
            break

    raw = p.get_text(separator=" ", strip=True)
    text = re.sub(r"[\xa0\u00a0]+", " ", raw)  # &nbsp; → espaço
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text, alterado_por, is_revogado


# ──────────────────────────────────────────────────────────────────────────────
# Extração de metadados do documento
# ──────────────────────────────────────────────────────────────────────────────


def _extract_titulo(soup: BeautifulSoup) -> str:
    """Título oficial: primeiro <strong> (possivelmente dentro de <a>) com 'LEI' ou 'DECRETO'.

    Estratégia primária: <p align='center'> > <strong> (CDC, Lei 4.090).
    Fallback: qualquer <strong> no documento (CLT — título fica em <a><font><strong>
    fora do <p> por causa de um </font> órfão que confunde o parser HTML).
    """
    for p in soup.find_all("p"):
        if p.get("align", "").lower() == "center":
            strong = p.find("strong")
            if strong:
                t = re.sub(r"\s+", " ", strong.get_text(strip=True))
                if t.upper().startswith(("LEI", "DECRETO")):
                    return t
    # Fallback: qualquer <strong> com conteúdo iniciando em LEI/DECRETO
    for strong in soup.find_all("strong"):
        t = re.sub(r"\s+", " ", strong.get_text(strip=True))
        if t.upper().startswith(("LEI", "DECRETO")):
            return t
    return ""


def _extract_ementa(soup: BeautifulSoup) -> str:
    """Ementa: primeiro <font color='#800000'> com conteúdo não vazio."""
    for tag in soup.find_all("font", attrs={"color": re.compile(r"#800000", re.IGNORECASE)}):
        t = re.sub(r"\s+", " ", tag.get_text(strip=True))
        if t:
            return t
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# Estado da máquina de parse (rastreia o contexto hierárquico corrente)
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class _State:
    art_key: str | None = None
    art_caminho: dict[str, str] = None  # type: ignore[assignment]
    par_key: str | None = None
    par_caminho: dict[str, str] = None  # type: ignore[assignment]
    inc_key: str | None = None

    def __post_init__(self) -> None:
        if self.art_caminho is None:
            self.art_caminho = {}
        if self.par_caminho is None:
            self.par_caminho = {}

    def enter_art(self, numero: str) -> None:
        self.art_key = f"art_{numero}"
        self.art_caminho = {"artigo": numero}
        self.par_key = None
        self.par_caminho = {}
        self.inc_key = None

    def enter_par(self, numero: str) -> None:
        safe = numero.replace("ú", "u").replace("í", "i")
        self.par_key = f"{self.art_key}_par_{safe}"
        self.par_caminho = {**self.art_caminho, "paragrafo": numero}
        self.inc_key = None

    def enter_inc(self, numero: str) -> None:
        parent = self.par_key or self.art_key
        self.inc_key = f"{parent}_inc_{numero}"

    @property
    def current_parent_key(self) -> str | None:
        """Pai imediato para um inciso (parágrafo se existir, senão artigo)."""
        return self.par_key or self.art_key

    @property
    def current_inc_parent_key(self) -> str | None:
        """Pai imediato para uma alínea."""
        return self.inc_key or self.par_key or self.art_key

    @property
    def current_inc_caminho(self) -> dict[str, str]:
        parent_caminho = self.par_caminho if self.par_key else self.art_caminho
        return parent_caminho


# ──────────────────────────────────────────────────────────────────────────────
# Extração dos dispositivos
# ──────────────────────────────────────────────────────────────────────────────


def _extract_dispositivos(  # noqa: C901
    soup: BeautifulSoup,
) -> tuple[list[_ChunkDraft], list[dict[str, str]]]:
    """
    Retorna (drafts, descartados).
    descartados: lista de {"tipo", "numero", "motivo"} para rastreabilidade.
    """
    drafts: list[_ChunkDraft] = []
    descartados: list[dict[str, str]] = []
    pos = 0
    s = _State()

    for p in soup.find_all("p"):
        text, alterado_por, is_revogado = _process_p(p)

        if not text:
            continue

        # Revogado/Vetado detectado via <a> ou <font> em _process_p
        if is_revogado:
            motivo = "vetado" if re.search(r"vetado", text, re.IGNORECASE) else "revogado"
            tipo, numero = _classify_tipo(text)
            if tipo == "artigo":
                descartados.append({"tipo": tipo, "numero": numero, "motivo": motivo})
                s.enter_art(numero)
                s.art_key = None  # invalida: filhos sem artigo → descartados
            elif tipo == "alinea":
                ma = _ALI.match(text)
                if ma and _ali_corpo_util(ma.group(2)):
                    descartados.append({"tipo": tipo, "numero": numero, "motivo": motivo})
                # corpo vazio/separador HTML — silenciosamente ignorado (fora do metadata tb)
            elif tipo != "desconhecido":
                descartados.append({"tipo": tipo, "numero": numero, "motivo": motivo})
            else:
                descartados.append({"tipo": "desconhecido", "numero": "-", "motivo": motivo})
            continue

        # ── Artigo ─────────────────────────────────────────────────────────
        m = _ART.match(text)
        if m:
            numero = m.group(1)
            caput = m.group(2).strip()

            # Caput é só marcador de veto/revogação → descarta
            if _MARCADOR.match(caput):
                motivo = "vetado" if "vetad" in caput.lower() else "revogado"
                descartados.append({"tipo": "artigo", "numero": numero, "motivo": motivo})
                s.enter_art(numero)
                s.art_key = None  # invalida filhos
                continue

            texto = f"Art. {numero}° - {caput}" if caput else text
            s.enter_art(numero)
            drafts.append(
                _ChunkDraft(
                    tipo="artigo",
                    numero=numero,
                    texto=texto,
                    posicao_ordem=pos,
                    caminho_hierarquico=dict(s.art_caminho),
                    chunk_key=s.art_key,  # type: ignore[arg-type]
                    parent_key=None,
                    alterado_por=alterado_por,
                )
            )
            pos += 1
            continue

        # Dispositivos filhos exigem que já haja um artigo corrente
        if not s.art_key:
            continue

        # ── Parágrafo único ────────────────────────────────────────────────
        if _PAR_UNICO.match(text):
            s.enter_par("único")
            drafts.append(
                _ChunkDraft(
                    tipo="paragrafo",
                    numero="único",
                    texto=text,
                    posicao_ordem=pos,
                    caminho_hierarquico=dict(s.par_caminho),
                    chunk_key=s.par_key,  # type: ignore[arg-type]
                    parent_key=s.art_key,
                    alterado_por=alterado_por,
                )
            )
            pos += 1
            continue

        # ── Parágrafo numerado ─────────────────────────────────────────────
        m = _PAR.match(text)
        if m:
            numero = m.group(1)
            s.enter_par(numero)
            drafts.append(
                _ChunkDraft(
                    tipo="paragrafo",
                    numero=numero,
                    texto=text,
                    posicao_ordem=pos,
                    caminho_hierarquico=dict(s.par_caminho),
                    chunk_key=s.par_key,  # type: ignore[arg-type]
                    parent_key=s.art_key,
                    alterado_por=alterado_por,
                )
            )
            pos += 1
            continue

        # ── Inciso ─────────────────────────────────────────────────────────
        m = _INC.match(text)
        if m:
            numero = m.group(1)
            parent_key = s.current_parent_key
            parent_caminho = s.par_caminho if s.par_key else s.art_caminho
            s.enter_inc(numero)
            drafts.append(
                _ChunkDraft(
                    tipo="inciso",
                    numero=numero,
                    texto=text,
                    posicao_ordem=pos,
                    caminho_hierarquico={**parent_caminho, "inciso": numero},
                    chunk_key=s.inc_key,  # type: ignore[arg-type]
                    parent_key=parent_key,
                    alterado_por=alterado_por,
                )
            )
            pos += 1
            continue

        # ── Alínea ─────────────────────────────────────────────────────────
        m = _ALI.match(text)
        if m:
            numero = m.group(1)
            parent_key = s.current_inc_parent_key
            parent_caminho = s.current_inc_caminho
            ali_key = f"{parent_key}_ali_{numero}"
            drafts.append(
                _ChunkDraft(
                    tipo="alinea",
                    numero=numero,
                    texto=text,
                    posicao_ordem=pos,
                    caminho_hierarquico={**parent_caminho, "alinea": numero},
                    chunk_key=ali_key,
                    parent_key=parent_key,
                    alterado_por=alterado_por,
                )
            )
            pos += 1
            continue

        # Texto não reconhecido (preâmbulo, rodapé, assinaturas…) → descarta

    return drafts, descartados


# ──────────────────────────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────────────────────────


def parse_html(
    html_bytes: bytes,
) -> tuple[str, str, list[_ChunkDraft], list[dict[str, str]]]:
    """
    Faz o parse do HTML de uma lei do Planalto.
    Retorna (titulo_oficial, ementa, drafts, descartados).
    """
    soup = BeautifulSoup(html_bytes, "html.parser", from_encoding="cp1252")
    titulo = _extract_titulo(soup)
    ementa = _extract_ementa(soup)
    drafts, descartados = _extract_dispositivos(soup)
    return titulo, ementa, drafts, descartados


def ingest(
    html_path: Path,
    doc_kwargs: dict[str, Any],
    session: Session,
) -> tuple[int, int, int]:
    """
    Lê o HTML, parseia, insere 1 linha em documents e N em chunks.
    Retorna (document_id, n_chunks, n_descartados).
    """
    # Importação local para não criar dependência circular em testes unitários do parser
    from sqlalchemy import null as _sql_null

    from src.db.models import Chunk, Document

    # psycopg3 converte Python None → JSON null para colunas JSONB (não SQL NULL).
    # _j() força SQL NULL quando o valor é None.
    def _j(v: dict | None) -> dict | object:
        return v if v is not None else _sql_null()

    raw = html_path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()

    titulo, ementa, drafts, descartados = parse_html(raw)

    doc = Document(
        codigo=doc_kwargs["codigo"],
        tipo_norma=doc_kwargs["tipo_norma"],
        numero=doc_kwargs["numero"],
        ano=doc_kwargs["ano"],
        titulo_oficial=titulo or doc_kwargs.get("titulo_oficial", ""),
        ementa=ementa or None,
        area_juridica=doc_kwargs["area_juridica"],
        data_assinatura=doc_kwargs.get("data_assinatura"),
        fonte_url=doc_kwargs["fonte_url"],
        hash_html_bruto=sha256,
        metadata_=_j({"dispositivos_descartados": descartados} if descartados else None),
    )
    session.add(doc)
    session.flush()  # obtém doc.id antes de inserir os chunks

    # Mapa chave_lógica → id real do banco (para resolução de parent_chunk_id)
    id_map: dict[str, int] = {}

    for draft in drafts:
        parent_id = id_map[draft.parent_key] if draft.parent_key else None
        chunk = Chunk(
            document_id=doc.id,
            parent_chunk_id=parent_id,
            tipo=draft.tipo,
            numero=draft.numero,
            texto=draft.texto,
            posicao_ordem=draft.posicao_ordem,
            caminho_hierarquico=_j(draft.caminho_hierarquico),
            alterado_por=_j(draft.alterado_por),
            metadata_=_j(draft.metadata_),
        )
        session.add(chunk)
        session.flush()  # obtém chunk.id antes do próximo filho
        id_map[draft.chunk_key] = chunk.id

    session.commit()
    return doc.id, len(drafts), len(descartados)


# ──────────────────────────────────────────────────────────────────────────────
# CLI — ingestão da Lei 4.090
# ──────────────────────────────────────────────────────────────────────────────

_CORPUS_MAP: dict[str, tuple[str, dict[str, Any]]] = {
    "lei-4090-1962": (
        "data/raw/decimo_terceiro/lei_4090_planalto.html",
        {
            "codigo": "lei-4090-1962",
            "tipo_norma": "lei",
            "numero": "4.090",
            "ano": 1962,
            "area_juridica": "trabalho",
            "data_assinatura": date(1962, 7, 13),
            "fonte_url": "https://www.planalto.gov.br/ccivil_03/leis/l4090.htm",
        },
    ),
    "lei-4749-1965": (
        "data/raw/decimo_terceiro/lei_4749_planalto.html",
        {
            "codigo": "lei-4749-1965",
            "tipo_norma": "lei",
            "numero": "4.749",
            "ano": 1965,
            "area_juridica": "trabalho",
            "data_assinatura": date(1965, 8, 12),
            "fonte_url": "https://www.planalto.gov.br/ccivil_03/leis/l4749.htm",
        },
    ),
    "lei-8036-1990": (
        "data/raw/fgts/lei_8036_planalto.html",
        {
            "codigo": "lei-8036-1990",
            "tipo_norma": "lei",
            "numero": "8.036",
            "ano": 1990,
            "area_juridica": "trabalho",
            "data_assinatura": date(1990, 5, 11),
            "fonte_url": "https://www.planalto.gov.br/ccivil_03/leis/l8036consol.htm",
        },
    ),
    "lei-8078-1990": (
        "data/raw/cdc/cdc_planalto.html",
        {
            "codigo": "lei-8078-1990",
            "tipo_norma": "lei",
            "numero": "8.078",
            "ano": 1990,
            "area_juridica": "consumidor",
            "data_assinatura": date(1990, 9, 11),
            "fonte_url": "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm",
        },
    ),
    "decreto-lei-5452-1943": (
        "data/raw/clt/clt_planalto.html",
        {
            "codigo": "decreto-lei-5452-1943",
            "tipo_norma": "decreto-lei",
            "numero": "5.452",
            "ano": 1943,
            "area_juridica": "trabalho",
            "data_assinatura": date(1943, 5, 1),
            "fonte_url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452compilado.htm",
        },
    ),
}

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "lei-4090-1962"
    if target not in _CORPUS_MAP:
        print(f"Uso: python -m src.corpus.parser_planalto [{' | '.join(_CORPUS_MAP)}]")
        sys.exit(1)

    DB_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(DB_URL, echo=False)

    rel_path, doc_kwargs = _CORPUS_MAP[target]
    html_path = Path(__file__).resolve().parents[2] / rel_path

    with Session(engine) as session:
        doc_id, n_chunks, n_descartados = ingest(html_path, doc_kwargs, session)

    print(f"OK — document_id={doc_id}, chunks inseridos={n_chunks}, descartados={n_descartados}")
