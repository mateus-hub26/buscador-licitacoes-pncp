from openpyxl import load_workbook

from licitacoes import exportar


def test_gera_planilha_formatada(tmp_path, nova_licitacao):
    resultados = [(nova_licitacao("Reforma de laboratório", valor=1234.5), 80)]
    df = exportar.para_dataframe(resultados)
    arquivo = exportar.salvar_excel(df, tmp_path / "saida" / "teste.xlsx")

    ws = load_workbook(arquivo).active
    cabecalho = [c.value for c in ws[1]]
    assert cabecalho[0] == "Pontuação"
    assert "Objeto" in cabecalho
    assert ws.freeze_panes == "A2"

    col_link = cabecalho.index("Link") + 1
    assert ws.cell(2, col_link).hyperlink is not None


def test_planilha_vazia_mantem_cabecalho(tmp_path):
    df = exportar.para_dataframe([])
    arquivo = exportar.salvar_excel(df, tmp_path / "vazia.xlsx")
    ws = load_workbook(arquivo).active
    assert ws.max_row == 1
