from unittest.mock import MagicMock

import pytest
import requests

from licitacoes.pncp import ClientePNCP, Licitacao

ITEM_API = {
    "numeroControlePNCP": "12345678000199-1-000042/2026",
    "objetoCompra": "  Construção de creche  ",
    "orgaoEntidade": {"razaoSocial": "MUNICIPIO DE EXEMPLO"},
    "unidadeOrgao": {"municipioNome": "Exemplo", "ufSigla": "SP"},
    "modalidadeNome": "Concorrência - Eletrônica",
    "valorTotalEstimado": 1_250_000.5,
    "dataAberturaProposta": "2026-11-01T08:00:00",
    "dataEncerramentoProposta": "2026-11-20T10:00:00",
    "linkSistemaOrigem": None,
}


def resposta(status=200, json=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.headers = headers or {}
    r.json.return_value = json
    if status >= 400:
        r.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
    return r


@pytest.fixture
def esperas(monkeypatch):
    """Registra as pausas em vez de dormir de verdade."""
    registradas = []
    monkeypatch.setattr("licitacoes.pncp.time.sleep", registradas.append)
    return registradas


def test_licitacao_from_api_converte_campos():
    lic = Licitacao.from_api(ITEM_API)
    assert lic.objeto == "Construção de creche"
    assert lic.uf == "SP"
    assert lic.valor_estimado == 1_250_000.5
    assert lic.encerramento_propostas.day == 20
    # sem link de origem, monta o link do próprio PNCP
    assert lic.link == "https://pncp.gov.br/app/editais/12345678000199/2026/42"


def test_licitacao_from_api_tolera_campos_ausentes():
    lic = Licitacao.from_api({"numeroControlePNCP": "x"})
    assert lic.objeto == ""
    assert lic.encerramento_propostas is None


def test_percorre_todas_as_paginas(esperas):
    sessao = MagicMock()
    sessao.headers = {}
    sessao.get.side_effect = [
        resposta(json={"data": [ITEM_API], "totalPaginas": 2}),
        resposta(json={"data": [ITEM_API], "totalPaginas": 2}),
    ]
    cliente = ClientePNCP(sessao=sessao)
    assert len(list(cliente.propostas_abertas(modalidade=4))) == 2
    assert sessao.get.call_args_list[1].kwargs["params"]["pagina"] == 2
    assert esperas == [1.0]  # pausa entre as páginas


def test_limite_de_requisicoes_respeita_retry_after(esperas):
    sessao = MagicMock()
    sessao.headers = {}
    sessao.get.side_effect = [
        resposta(status=429, headers={"Retry-After": "30"}),
        resposta(json={"data": [ITEM_API], "totalPaginas": 1}),
    ]
    assert len(list(ClientePNCP(sessao=sessao).propostas_abertas(modalidade=4))) == 1
    assert esperas == [30.0]


def test_limite_de_requisicoes_sem_retry_after_espera_mais(esperas):
    sessao = MagicMock()
    sessao.headers = {}
    sessao.get.side_effect = [
        resposta(status=503),
        resposta(status=429),
        resposta(json={"data": [ITEM_API], "totalPaginas": 1}),
    ]
    list(ClientePNCP(sessao=sessao, espera_s=2).propostas_abertas(modalidade=4))
    assert esperas == [2, 20]  # falha comum: 2s; 429 na 2ª tentativa: 4s x 5


def test_204_significa_sem_resultados():
    sessao = MagicMock()
    sessao.headers = {}
    sessao.get.return_value = resposta(status=204)
    assert list(ClientePNCP(sessao=sessao).propostas_abertas(modalidade=6)) == []


def test_repete_apos_falha_temporaria(esperas):
    sessao = MagicMock()
    sessao.headers = {}
    sessao.get.side_effect = [
        resposta(status=503),
        resposta(json={"data": [ITEM_API], "totalPaginas": 1}),
    ]
    cliente = ClientePNCP(sessao=sessao)
    assert len(list(cliente.propostas_abertas(modalidade=4))) == 1
    assert sessao.get.call_count == 2


def test_desiste_apos_esgotar_tentativas(esperas):
    sessao = MagicMock()
    sessao.headers = {}
    sessao.get.return_value = resposta(status=500)
    cliente = ClientePNCP(sessao=sessao, tentativas=2)
    with pytest.raises(requests.HTTPError):
        list(cliente.propostas_abertas(modalidade=4))
