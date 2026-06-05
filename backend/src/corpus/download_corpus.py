"""
Download do corpus juridico do Planalto.gov.br.

Salva os bytes originais do servidor SEM conversao de encoding.
O parser usa from_encoding='cp1252' e continua funcionando.

Por padrao: dry-run -- calcula hashes, NAO sobrescreve.
Com --write: grava CDC, FGTS, CLT e Lei 4.749. Lei 4.090 NUNCA e sobrescrita
            (serve apenas como teste de regressao do script).

Uso:
    poetry run python -m src.corpus.download_corpus           # dry-run
    poetry run python -m src.corpus.download_corpus --write   # sobrescreve os 4
"""

from __future__ import annotations

import hashlib
import re
import sys
import urllib.request
from pathlib import Path
from typing import NamedTuple

# ──────────────────────────────────────────────────────────────────────────────
# Corpus
# ──────────────────────────────────────────────────────────────────────────────


class _Entry(NamedTuple):
    nome: str
    url: str
    destino: str  # relativo a backend/
    writeable: bool  # False = so teste de regressao, nunca sobrescreve


CORPUS: list[_Entry] = [
    _Entry(
        "Lei 4.090 [REGRESSAO - nao sobrescreve]",
        "https://www.planalto.gov.br/ccivil_03/leis/l4090.htm",
        "data/raw/decimo_terceiro/lei_4090_planalto.html",
        writeable=False,
    ),
    _Entry(
        "Lei 4.749",
        "https://www.planalto.gov.br/ccivil_03/leis/l4749.htm",
        "data/raw/decimo_terceiro/lei_4749_planalto.html",
        writeable=True,
    ),
    _Entry(
        "CDC -- Lei 8.078/1990",
        "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm",
        "data/raw/cdc/cdc_planalto.html",
        writeable=True,
    ),
    _Entry(
        "FGTS -- Lei 8.036/1990",
        "https://www.planalto.gov.br/ccivil_03/leis/l8036consol.htm",
        "data/raw/fgts/lei_8036_planalto.html",
        writeable=True,
    ),
    _Entry(
        "CLT -- DL 5.452/1943",
        "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452compilado.htm",
        "data/raw/clt/clt_planalto.html",
        writeable=True,
    ),
]

# SHA-256 da Lei 4.090 validada (cp1252, 9 chunks, hierarquia confirmada)
LEI_4090_KNOWN_SHA = "6712cb8af173d377ae28d78ce772d3a6a2151b8d4ac50881c63821f5f16e2617"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strip_f5(raw: bytes) -> bytes:
    """Remove o bloco <script id="f5_cspm">...</script> antes de comparar hashes.
    O F5 load-balancer do Planalto injeta esse script dinamicamente a cada request --
    o valor muda entre downloads mas nao tem conteudo juridico.
    """
    text = raw.decode("latin-1")
    cleaned = re.sub(r'<script id="f5_cspm">.*?</script>', "", text, flags=re.DOTALL)
    return cleaned.encode("latin-1")


def _diagnostico(raw: bytes) -> tuple[int, int, int]:
    """Retorna (bytes_0x3f, bytes_nao_ascii, contagem_paragrafos).
    Contagem de paragrafos usa decodificacao latin-1 (1:1 com bytes).
    """
    q = raw.count(b"\x3f")
    na = sum(1 for b in raw if b > 127)
    text = raw.decode("latin-1")
    par = text.count("\xa7")  # byte 0xA7 = § em latin-1/cp1252
    return q, na, par


def _download(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; JusBot-TCC/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────


def run(write: bool = False) -> None:  # noqa: C901
    base = Path(__file__).resolve().parents[2]  # backend/
    mode = "ESCRITA" if write else "DRY-RUN"
    sep_duplo = "=" * 68
    sep = "-" * 68

    print(f"\n{sep_duplo}")
    print(f"  Download do corpus -- modo {mode}")
    print(sep_duplo)

    regressao_ok = None  # None = nao testado ainda

    for entry in CORPUS:
        path = base / entry.destino
        nome = entry.nome

        old_sha = _sha256(path.read_bytes()) if path.exists() else None
        old_label = (old_sha[:16] + "...") if old_sha else "NAO EXISTE"

        print(f"\n{sep}")
        print(f"  {nome}")
        print(f"  URL    : {entry.url}")
        print(f"  Hash atual : {old_label}")

        try:
            raw = _download(entry.url)
        except Exception as e:
            print(f"  [ERRO] download falhou: {e}")
            if not entry.writeable:
                regressao_ok = False
            continue

        q, na, par = _diagnostico(raw)
        # Hash comparavel: sem o script f5_cspm dinamico do servidor
        new_sha_cmp = _sha256(_strip_f5(raw))
        old_sha_cmp = _sha256(_strip_f5(path.read_bytes())) if path.exists() else None

        print(f"  Tamanho    : {len(raw):,} bytes | nao-ASCII: {na:,} | '?': {q:,} | par. S: {par}")
        print(f"  Hash novo (sem f5): {new_sha_cmp[:16]}...")

        # Teste de regressao: Lei 4.090 deve ser identica ao arquivo validado
        if not entry.writeable:
            # Compara versao sem f5 do arquivo local validado
            local_cmp = _sha256(_strip_f5(Path(base / entry.destino).read_bytes()))
            if new_sha_cmp == local_cmp:
                print("  [REGRESSAO OK] hash bate com arquivo validado -- servidor integro")
                regressao_ok = True
            else:
                print("  [REGRESSAO FALHOU] hash diferente do validado!")
                print(f"    Local (sem f5) : {local_cmp[:16]}...")
                print(f"    Remoto (sem f5): {new_sha_cmp[:16]}...")
                print("  Investigar antes de sobrescrever qualquer arquivo.")
                regressao_ok = False
            continue  # nunca grava Lei 4.090

        # Arquivos writeable
        if old_sha_cmp == new_sha_cmp:
            print("  [=] IDENTICO (conteudo juridico) -- nada mudaria")
        else:
            print("  [~] DIFERENTE -- arquivo seria atualizado")
            if na == 0 and len(raw) > 10_000:
                print("  [ATENCAO] servidor devolveu arquivo sem nao-ASCII -- suspeito")

        if write:
            if regressao_ok is False:
                print("  [PULADO] regressao da Lei 4.090 falhou -- nao sobrescrevendo")
                continue
            if regressao_ok is None:
                print("  [PULADO] regressao da Lei 4.090 ainda nao foi testada")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            print(f"  [SALVO] {len(raw):,} bytes (cp1252 original do servidor)")

    print(f"\n{sep_duplo}")
    if regressao_ok is False:
        print("  [!!!] Regressao da Lei 4.090 FALHOU -- nenhum arquivo foi sobrescrito")
    elif regressao_ok is True:
        if write:
            print("  Corpus atualizado (4 arquivos). Reingiria os documentos afetados no banco.")
        else:
            print("  Regressao OK. Use --write para aplicar.")
    else:
        print("  Regressao nao testada (download da 4.090 falhou).")
    print(f"{sep_duplo}\n")


if __name__ == "__main__":
    write = "--write" in sys.argv
    run(write=write)
