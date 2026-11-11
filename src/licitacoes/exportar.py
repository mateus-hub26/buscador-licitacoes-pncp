"""Exportação dos resultados para Excel."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .pncp import Licitacao

COLUNAS = {
    "pontuacao": "Pontuação",
    "encerramento": "Encerramento das propostas",
    "uf": "UF",
    "municipio": "Município",
    "orgao": "Órgão",
    "modalidade": "Modalidade",
    "valor": "Valor estimado (R$)",
    "objeto": "Objeto",
    "link": "Link",
}

LARGURAS = {"Objeto": 80, "Órgão": 40, "Link": 40, "Município": 20, "Modalidade": 24}


def para_dataframe(resultados: list[tuple[Licitacao, int]]) -> pd.DataFrame:
    linhas = [
        {
            "pontuacao": pontos,
            "encerramento": lic.encerramento_propostas,
            "uf": lic.uf,
            "municipio": lic.municipio,
            "orgao": lic.orgao,
            "modalidade": lic.modalidade,
            "valor": lic.valor_estimado,
            "objeto": lic.objeto,
            "link": lic.link,
        }
        for lic, pontos in resultados
    ]
    return pd.DataFrame(linhas, columns=list(COLUNAS)).rename(columns=COLUNAS)


def salvar_excel(df: pd.DataFrame, caminho: Path) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Licitações")
        ws = writer.sheets["Licitações"]

        cabecalho = PatternFill("solid", fgColor="1F3864")
        for cel in ws[1]:
            cel.font = Font(bold=True, color="FFFFFF")
            cel.fill = cabecalho

        for i, nome in enumerate(df.columns, start=1):
            ws.column_dimensions[get_column_letter(i)].width = LARGURAS.get(nome, 16)

        col_valor = df.columns.get_loc(COLUNAS["valor"]) + 1
        col_data = df.columns.get_loc(COLUNAS["encerramento"]) + 1
        col_link = df.columns.get_loc(COLUNAS["link"]) + 1
        for linha in range(2, ws.max_row + 1):
            ws.cell(linha, col_valor).number_format = "#,##0.00"
            ws.cell(linha, col_data).number_format = "dd/mm/yyyy hh:mm"
            cel_link = ws.cell(linha, col_link)
            if cel_link.value:
                cel_link.hyperlink = cel_link.value
                cel_link.font = Font(color="0563C1", underline="single")

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    return caminho
