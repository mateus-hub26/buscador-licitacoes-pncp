"""Filtragem e priorização das licitações encontradas."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

from .pncp import Licitacao


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e com espaços simples — para comparar textos do PNCP,
    que chegam com acentuação e caixa inconsistentes."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def _contem(texto_norm: str, termo: str) -> bool:
    """Busca o termo como palavra inteira (``obra`` não casa com ``manobra``)."""
    return re.search(rf"\b{re.escape(normalizar(termo))}\b", texto_norm) is not None


@dataclass
class Filtro:
    palavras_chave: list[str]
    excluir: list[str] = field(default_factory=list)
    ufs: list[str] = field(default_factory=list)
    valor_min: float | None = None
    valor_max: float | None = None

    def aceita(self, lic: Licitacao) -> bool:
        objeto = normalizar(lic.objeto)
        if not any(_contem(objeto, p) for p in self.palavras_chave):
            return False
        if any(_contem(objeto, p) for p in self.excluir):
            return False
        if self.ufs and lic.uf.upper() not in {u.upper() for u in self.ufs}:
            return False
        if lic.valor_estimado is not None:
            if self.valor_min is not None and lic.valor_estimado < self.valor_min:
                return False
            if self.valor_max is not None and lic.valor_estimado > self.valor_max:
                return False
        return True

    def pontuar(self, lic: Licitacao, agora: datetime | None = None) -> int:
        """Pontuação de 0 a 100 para ordenar o que analisar primeiro.

        - até 60 pontos pela quantidade de palavras-chave presentes no objeto;
        - 20 pontos se o valor estimado é conhecido (dá para avaliar porte);
        - até 20 pontos pelo tempo restante: prazos muito curtos (< 3 dias) valem menos,
          porque não dá tempo de montar a proposta.
        """
        objeto = normalizar(lic.objeto)
        acertos = sum(_contem(objeto, p) for p in self.palavras_chave)
        pontos = min(60, acertos * 20)

        if lic.valor_estimado:
            pontos += 20

        if lic.encerramento_propostas:
            dias = (lic.encerramento_propostas - (agora or datetime.now())).days
            if dias >= 7:
                pontos += 20
            elif dias >= 3:
                pontos += 10
        return pontos


def filtrar(licitacoes: list[Licitacao], filtro: Filtro) -> list[tuple[Licitacao, int]]:
    """Remove duplicadas, aplica o filtro e devolve (licitação, pontuação) em ordem decrescente."""
    vistos: set[str] = set()
    resultado = []
    for lic in licitacoes:
        if lic.id_pncp in vistos or not filtro.aceita(lic):
            continue
        vistos.add(lic.id_pncp)
        resultado.append((lic, filtro.pontuar(lic)))
    resultado.sort(key=lambda par: (-par[1], par[0].encerramento_propostas or datetime.max))
    return resultado
