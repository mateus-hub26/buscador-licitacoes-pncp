"""Cliente da API pública de consultas do PNCP (Portal Nacional de Contratações Públicas).

Documentação oficial: https://pncp.gov.br/api/consulta/swagger-ui/index.html
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterator

import requests

log = logging.getLogger(__name__)

URL_BASE = "https://pncp.gov.br/api/consulta/v1"

# Códigos de modalidade definidos pelo PNCP (Lei 14.133/2021).
MODALIDADES = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial",
}


@dataclass(frozen=True)
class Licitacao:
    """Uma contratação publicada no PNCP, com os campos relevantes para triagem."""

    id_pncp: str
    objeto: str
    orgao: str
    municipio: str
    uf: str
    modalidade: str
    valor_estimado: float | None
    abertura_propostas: datetime | None
    encerramento_propostas: datetime | None
    link: str

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> "Licitacao":
        unidade = item.get("unidadeOrgao") or {}
        orgao = item.get("orgaoEntidade") or {}
        id_pncp = item.get("numeroControlePNCP", "")
        return cls(
            id_pncp=id_pncp,
            objeto=(item.get("objetoCompra") or "").strip(),
            orgao=orgao.get("razaoSocial", ""),
            municipio=unidade.get("municipioNome", ""),
            uf=unidade.get("ufSigla", ""),
            modalidade=item.get("modalidadeNome", ""),
            valor_estimado=item.get("valorTotalEstimado"),
            abertura_propostas=_parse_data(item.get("dataAberturaProposta")),
            encerramento_propostas=_parse_data(item.get("dataEncerramentoProposta")),
            link=item.get("linkSistemaOrigem") or _link_pncp(id_pncp),
        )


def _parse_data(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


def _link_pncp(id_pncp: str) -> str:
    """Monta o link da página do edital no PNCP a partir do número de controle.

    Formato do número: ``{cnpj}-1-{sequencial}/{ano}``.
    """
    try:
        cnpj, _, resto = id_pncp.split("-", 2)
        sequencial, ano = resto.split("/")
        return f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{int(sequencial)}"
    except ValueError:
        return "https://pncp.gov.br/app/editais"


class ClientePNCP:
    """Busca contratações com propostas em aberto, paginando e repetindo em caso de falha."""

    def __init__(
        self,
        sessao: requests.Session | None = None,
        tentativas: int = 5,
        espera_s: float = 2.0,
        tamanho_pagina: int = 50,
        pausa_entre_paginas_s: float = 1.0,
    ) -> None:
        self.sessao = sessao or requests.Session()
        self.sessao.headers.setdefault("User-Agent", "buscador-licitacoes-pncp/0.1")
        self.tentativas = tentativas
        self.espera_s = espera_s
        self.tamanho_pagina = tamanho_pagina
        # A API pública limita a taxa de requisições; uma pausa curta evita o HTTP 429.
        self.pausa_entre_paginas_s = pausa_entre_paginas_s

    def propostas_abertas(
        self,
        modalidade: int,
        ate: date | None = None,
        uf: str | None = None,
        max_paginas: int | None = None,
    ) -> Iterator[Licitacao]:
        """Itera sobre as contratações com propostas em aberto que encerram até ``ate``.

        Atenção: ``dataFinal`` na API é o limite MÁXIMO do encerramento das propostas.
        Passar a data de hoje traz só o que encerra hoje — use um horizonte à frente.
        """
        params: dict[str, Any] = {
            "dataFinal": (ate or date.today()).strftime("%Y%m%d"),
            "codigoModalidadeContratacao": modalidade,
            "tamanhoPagina": self.tamanho_pagina,
        }
        if uf:
            params["uf"] = uf.upper()

        pagina = 1
        while True:
            dados = self._get("/contratacoes/proposta", {**params, "pagina": pagina})
            if not dados:
                return
            for item in dados.get("data") or []:
                yield Licitacao.from_api(item)

            total_paginas = dados.get("totalPaginas") or 1
            if pagina >= total_paginas or (max_paginas and pagina >= max_paginas):
                return
            pagina += 1
            time.sleep(self.pausa_entre_paginas_s)

    def _get(self, caminho: str, params: dict[str, Any]) -> dict[str, Any] | None:
        for tentativa in range(1, self.tentativas + 1):
            espera = self.espera_s * 2 ** (tentativa - 1)  # 2s, 4s, 8s, ...
            try:
                resp = self.sessao.get(URL_BASE + caminho, params=params, timeout=60)
                if resp.status_code == 204:  # sem resultados
                    return None
                if resp.status_code == 429:  # limite de requisições: espera mais
                    espera = _retry_after(resp) or espera * 5
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as erro:
                log.warning("Falha na tentativa %d/%d: %s", tentativa, self.tentativas, erro)
                if tentativa == self.tentativas:
                    raise
                time.sleep(espera)
        return None


def _retry_after(resp: requests.Response) -> float | None:
    """Segundos indicados pelo servidor no cabeçalho Retry-After, se houver."""
    try:
        return float(resp.headers.get("Retry-After", ""))
    except (TypeError, ValueError):
        return None
