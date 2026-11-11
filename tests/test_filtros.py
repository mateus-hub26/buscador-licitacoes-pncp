from licitacoes.filtros import Filtro, filtrar, normalizar


def test_normalizar_remove_acentos_caixa_e_espacos():
    assert normalizar("  CONSTRUÇÃO   de  Edificação ") == "construcao de edificacao"


def test_palavra_chave_ignora_acento_e_caixa(nova_licitacao):
    filtro = Filtro(palavras_chave=["construção"])
    assert filtro.aceita(nova_licitacao("CONSTRUCAO DE UNIDADE BASICA DE SAUDE"))


def test_palavra_chave_casa_palavra_inteira(nova_licitacao):
    filtro = Filtro(palavras_chave=["obra"])
    assert not filtro.aceita(nova_licitacao("Serviço de manobra de veículos"))
    assert filtro.aceita(nova_licitacao("Obra de ampliação da escola"))


def test_termo_excluido_descarta(nova_licitacao):
    filtro = Filtro(palavras_chave=["reforma"], excluir=["material de expediente"])
    assert not filtro.aceita(nova_licitacao("Reforma e aquisição de material de expediente"))


def test_filtro_por_uf(nova_licitacao):
    filtro = Filtro(palavras_chave=["reforma"], ufs=["sp", "MG"])
    assert filtro.aceita(nova_licitacao(uf="SP"))
    assert not filtro.aceita(nova_licitacao(uf="RJ"))


def test_faixa_de_valor(nova_licitacao):
    filtro = Filtro(palavras_chave=["reforma"], valor_min=100_000, valor_max=1_000_000)
    assert filtro.aceita(nova_licitacao(valor=500_000))
    assert not filtro.aceita(nova_licitacao(valor=50_000))
    assert not filtro.aceita(nova_licitacao(valor=5_000_000))


def test_valor_desconhecido_nao_e_descartado(nova_licitacao):
    filtro = Filtro(palavras_chave=["reforma"], valor_min=100_000)
    assert filtro.aceita(nova_licitacao(valor=None))


def test_pontuacao_favorece_mais_palavras_e_prazo_longo(nova_licitacao, agora):
    filtro = Filtro(palavras_chave=["reforma", "laboratorio"])
    completa = filtro.pontuar(nova_licitacao("Reforma de laboratório", dias=10), agora)
    parcial = filtro.pontuar(nova_licitacao("Reforma de escola", dias=10), agora)
    urgente = filtro.pontuar(nova_licitacao("Reforma de laboratório", dias=1), agora)
    assert completa == 80  # 2 palavras (40) + valor (20) + prazo >= 7 dias (20)
    assert completa > parcial
    assert completa > urgente


def test_filtrar_remove_duplicadas_e_ordena(nova_licitacao):
    filtro = Filtro(palavras_chave=["reforma", "laboratorio"])
    a = nova_licitacao("Reforma de escola", id_pncp="A")
    b = nova_licitacao("Reforma de laboratório", id_pncp="B")
    resultado = filtrar([a, b, b], filtro)
    assert [lic.id_pncp for lic, _ in resultado] == ["B", "A"]
