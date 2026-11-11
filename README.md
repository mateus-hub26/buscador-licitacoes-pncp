# Buscador de Licitações PNCP

![testes](https://github.com/mateus-hub26/buscador-licitacoes-pncp/actions/workflows/testes.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![licença](https://img.shields.io/badge/licença-MIT-green)

Ferramenta em Python que consulta a **API pública do [PNCP](https://pncp.gov.br)** (Portal Nacional de Contratações Públicas), encontra licitações com **propostas em aberto**, filtra pelo perfil da empresa e entrega uma **planilha Excel priorizada** — opcionalmente enviada por e-mail.

## O problema

Empresas que vendem para o governo precisam acompanhar centenas de editais publicados todos os dias em todo o país. Fazer isso à mão significa abrir portal por portal, ler objeto por objeto e copiar os relevantes para uma planilha. Com isso, oportunidades boas passam despercebidas ou são encontradas tarde demais para montar a proposta.

Desde a Lei 14.133/2021, os órgãos públicos são obrigados a publicar suas contratações no PNCP, que oferece uma API aberta. Este projeto automatiza a triagem a partir dela.

## Como funciona

```
API do PNCP ──► coleta paginada ──► filtros ──► pontuação ──► planilha Excel ──► e-mail (opcional)
                (por modalidade,     (palavras,    (0 a 100)    (formatada,
                 com nova tentativa   exclusões,                 com links)
                 em caso de falha)    UF, valor)
```

1. **Coleta** (`pncp.py`): percorre todas as páginas do endpoint `/contratacoes/proposta` para cada modalidade escolhida, repetindo a requisição com espera crescente quando a API falha.
2. **Filtro** (`filtros.py`): normaliza o texto (sem acentos, caixa ou espaços duplicados) e busca **palavras inteiras**, para que `obra` não case com `manobra`. Depois aplica termos de exclusão, UF e faixa de valor, e remove duplicadas.
3. **Priorização**: cada licitação recebe de 0 a 100 pontos, conforme quantas palavras-chave aparecem, se o valor estimado é conhecido e quanto tempo falta para o fim das propostas. Prazos de menos de 3 dias valem menos, porque não dá tempo de preparar a proposta.
4. **Saída** (`exportar.py`): gera um Excel com cabeçalho fixo, filtros, valores formatados e link clicável para cada edital.
5. **Alerta** (`notificar.py`): opcionalmente, envia por e-mail um resumo das 10 melhores, com a planilha em anexo.

## Como usar

Requer Python 3.11+.

```bash
git clone https://github.com/mateus-hub26/buscador-licitacoes-pncp.git
cd buscador-licitacoes-pncp
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"

cp config.exemplo.toml config.toml   # ajuste palavras-chave, UFs, valores e modalidades
licitacoes                           # gera resultados/licitacoes_AAAAMMDD_HHMM.xlsx
```

Opções úteis:

| Opção | Efeito |
|---|---|
| `-c arquivo.toml` | usa outro arquivo de configuração |
| `-o pasta/` | muda a pasta de saída |
| `--max-paginas 2` | limita a coleta (teste rápido) |
| `--email` | envia a planilha para `[email].destinatarios` |

### Alerta por e-mail

As credenciais ficam em variáveis de ambiente, nunca no código ou no arquivo de configuração:

```bash
set SMTP_HOST=smtp.gmail.com
set SMTP_USUARIO=seu_email@gmail.com
set SMTP_SENHA=senha_de_app
licitacoes --email
```

Para rodar todo dia, agende o comando no Agendador de Tarefas do Windows ou no `cron`.

## Exemplo de execução

Execução real em 11/11/2026, com a configuração de exemplo (SP, MG e RJ; obras e engenharia; de R$ 100 mil a R$ 20 milhões), limitada a 2 páginas por consulta:

```
$ licitacoes --max-paginas 2
11:09:37 INFO Buscando propostas que encerram até 11/12/2026 (30 dias)
11:09:56 INFO Concorrência - Eletrônica      300 licitações abertas
11:10:14 INFO Concorrência - Presencial       49 licitações abertas
11:10:46 INFO Pregão - Eletrônico            300 licitações abertas
11:10:46 INFO 194 de 649 passaram nos filtros
11:10:46 INFO Planilha salva em resultados/licitacoes_20261111_1110.xlsx
```

As primeiras da planilha, todas com 100 pontos, são obras de engenharia, como a construção de uma delegacia (MG, R$ 2,2 mi) e a elaboração do projeto executivo de uma obra (RJ, R$ 12,2 mi).

### Detalhes da API que o código trata

- **`dataFinal` é o limite máximo do encerramento das propostas.** Passar a data de hoje traz só o que encerra hoje (181 pregões contra 8.441 na semana seguinte, no teste). Por isso o programa usa um horizonte configurável (`horizonte_dias`).
- **A API limita a taxa de requisições (HTTP 429).** O cliente faz uma pausa entre páginas, respeita o cabeçalho `Retry-After` e, se ele não vier, espera mais a cada nova tentativa.
- **Filtrar por UF na própria API**, com uma consulta por estado, reduz muito o volume baixado em relação a filtrar depois.

## Testes

```bash
pytest -v
```

Os testes cobrem a normalização de texto, todas as regras de filtro e pontuação, a paginação, o tratamento de respostas vazias (HTTP 204), as novas tentativas após falha e a geração da planilha. Eles rodam no GitHub Actions a cada push, em Python 3.11 e 3.13, sem acessar a rede: a API é simulada com mocks.

## Estrutura

```
src/licitacoes/
├── pncp.py        # cliente da API: paginação, novas tentativas, modelo Licitacao
├── filtros.py     # normalização, filtros e pontuação
├── exportar.py    # DataFrame e Excel formatado
├── notificar.py   # e-mail via SMTP
└── cli.py         # linha de comando
tests/             # pytest, sem acesso à rede
```

## Próximos passos

- [ ] Guardar o histórico em SQLite para alertar só sobre licitações **novas**
- [ ] Baixar e ler os PDFs dos editais para extrair exigências de habilitação
- [ ] Painel web simples para acompanhar o status de cada oportunidade

## Licença

MIT. Os dados vêm do PNCP e são públicos.
