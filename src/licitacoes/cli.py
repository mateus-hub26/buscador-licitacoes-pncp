"""Linha de comando: busca no PNCP, filtra, gera a planilha e (opcionalmente) envia por e-mail."""

from __future__ import annotations

import argparse
import logging
import sys
import tomllib
from datetime import date, datetime, timedelta
from pathlib import Path

from . import exportar, notificar
from .filtros import Filtro, filtrar
from .pncp import MODALIDADES, ClientePNCP

log = logging.getLogger("licitacoes")


def carregar_config(caminho: Path) -> dict:
    with caminho.open("rb") as f:
        return tomllib.load(f)


def montar_argumentos() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="licitacoes",
        description="Busca licitações com propostas abertas no PNCP e gera uma planilha priorizada.",
    )
    p.add_argument("-c", "--config", type=Path, default=Path("config.toml"),
                   help="arquivo TOML com os filtros (padrão: config.toml)")
    p.add_argument("-o", "--saida", type=Path, default=Path("resultados"),
                   help="pasta onde salvar a planilha (padrão: resultados/)")
    p.add_argument("--max-paginas", type=int, default=None,
                   help="limita as páginas por modalidade (útil para testes rápidos)")
    p.add_argument("--email", action="store_true",
                   help="envia a planilha para os destinatários do config (requer variáveis SMTP_*)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = montar_argumentos().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.config.exists():
        log.error("Arquivo de configuração não encontrado: %s (copie config.exemplo.toml)", args.config)
        return 2
    cfg = carregar_config(args.config)

    filtro = Filtro(
        palavras_chave=cfg["busca"]["palavras_chave"],
        excluir=cfg["busca"].get("excluir", []),
        ufs=cfg["busca"].get("ufs", []),
        valor_min=cfg["busca"].get("valor_min"),
        valor_max=cfg["busca"].get("valor_max"),
    )
    modalidades = cfg["busca"].get("modalidades", [4, 5, 6])
    horizonte = int(cfg["busca"].get("horizonte_dias", 30))
    ate = date.today() + timedelta(days=horizonte)
    log.info("Buscando propostas que encerram até %s (%d dias)", ate.strftime("%d/%m/%Y"), horizonte)

    cliente = ClientePNCP()
    encontradas = []
    # As UFs são filtradas na própria API, uma consulta por UF: baixa só o necessário.
    ufs_api: list[str | None] = list(filtro.ufs) or [None]
    for codigo in modalidades:
        nome = MODALIDADES.get(codigo, str(codigo))
        antes = len(encontradas)
        for uf in ufs_api:
            encontradas.extend(
                cliente.propostas_abertas(codigo, ate=ate, uf=uf, max_paginas=args.max_paginas)
            )
        log.info("%-28s %5d licitações abertas", nome, len(encontradas) - antes)

    resultados = filtrar(encontradas, filtro)
    log.info("%d de %d passaram nos filtros", len(resultados), len(encontradas))

    df = exportar.para_dataframe(resultados)
    arquivo = args.saida / f"licitacoes_{datetime.now():%Y%m%d_%H%M}.xlsx"
    exportar.salvar_excel(df, arquivo)
    log.info("Planilha salva em %s", arquivo)

    if args.email:
        destinatarios = cfg.get("email", {}).get("destinatarios", [])
        if not destinatarios:
            log.error("--email usado, mas [email].destinatarios está vazio no config")
            return 2
        if df.empty:
            log.info("Nenhuma oportunidade nova; e-mail não enviado")
        else:
            notificar.enviar(df, arquivo, destinatarios)
            log.info("E-mail enviado para %s", ", ".join(destinatarios))
    return 0


if __name__ == "__main__":
    sys.exit(main())
