from datetime import datetime, timedelta

import pytest

from licitacoes.pncp import Licitacao


@pytest.fixture
def agora():
    return datetime(2026, 11, 10, 9, 0)


@pytest.fixture
def nova_licitacao(agora):
    def _criar(objeto="Reforma de laboratório", uf="SP", valor=500_000.0, dias=10, id_pncp=None):
        return Licitacao(
            id_pncp=id_pncp or f"00000000000100-1-{abs(hash(objeto)) % 99999:06d}/2026",
            objeto=objeto,
            orgao="Prefeitura Exemplo",
            municipio="Cidade Exemplo",
            uf=uf,
            modalidade="Concorrência - Eletrônica",
            valor_estimado=valor,
            abertura_propostas=agora,
            encerramento_propostas=agora + timedelta(days=dias),
            link="https://pncp.gov.br/app/editais",
        )

    return _criar
