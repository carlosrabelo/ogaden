# Ogaden

Bot de trading automatizado para mercados spot da Binance com lógica de sinais EMA/RSI e dashboard em tempo real no navegador.

## Destaques

- Executa trades spot automatizados na Binance usando cruzamento de EMA e sinais RSI
- Simula execuções no modo sandbox com taxa de 0,1% antes de arriscar fundos reais
- Transmite o estado de trading em tempo real para um dashboard no navegador via Socket.IO
- Ajusta a quantidade das ordens à precisão da Binance (MIN_NOTIONAL, STEP_SIZE, MIN_QUANTITY)
- Alvos configuráveis de lucro, limite de perda e trailing stop
- Roda como stack Docker Compose: engine, dashboard e Memcached

## Pré-requisitos

- **Python 3.12+** — necessário para rodar localmente; [download](https://www.python.org/downloads/)
- **Docker e Docker Compose** — necessário para o stack completo
- **Chave e segredo da API da Binance** — acesso a trading spot necessário

## Instalação

### Local

```bash
git clone https://github.com/username/ogaden.git
cd ogaden
make setup
```

Instalar entry points em `~/.local/bin`:

```bash
make install
```

### Docker

```bash
make start
```

Constrói as imagens do engine e do dashboard e inicia o stack completo com o Memcached.

## Uso

### Loop de trading

```bash
make run-engine
```

Inicia o loop infinito de trading localmente. O engine busca candles a cada 60 segundos, calcula indicadores e executa ordens de compra/venda quando as condições se alinham.

### Análise avulsa

```bash
ogaden-analysis
```

Busca os dados de candles atuais e exibe todos os valores dos indicadores sem realizar nenhuma ordem.

### Web dashboard

```bash
make run-dashboard
```

Inicia o servidor de desenvolvimento local Flask e Socket.IO.

### Stack Docker

```bash
make start    # Constrói e inicia engine, dashboard e Memcached
make stop     # Para tudo e remove orphans
make restart  # Reconstrói e reinicia
```

Acesse `http://localhost:3502` para ver o dashboard ao vivo. Ele atualiza a cada 10 segundos com o snapshot mais recente do Memcached e exibe: estado da posição, sinais EMA/RSI/tendência, saldos base e quote, e delta de lucro atual.

> Operar com fundos reais é arriscado. Teste com `SANDBOX=true` e valores pequenos antes de ir ao vivo.

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```
API_KEY=your_key_here
API_SECRET=your_secret_here
SANDBOX=true
TIMEZONE=America/Cuiaba
BASE_ASSET=BTC
QUOTE_ASSET=USDT
INTERVAL=15m
LIMIT=500
FAST_EMA=7
SLOW_EMA=14
TREND_EMA=50
RSI_PERIOD=14
RSI_BUY_THRESHOLD=40
RSI_SELL_THRESHOLD=60
PROFIT_THRESHOLD=0.0
LOSS_THRESHOLD=0.0
TRAILING_THRESHOLD=0.0
MEMCACHED_HOST=localhost
MEMCACHED_PORT=11211
BASE_BALANCE=0.0
QUOTE_BALANCE=10.0
HTTP_PORT=3502
```

Defina `SANDBOX=true` para simular execuções sem acessar o livro de ordens real. Todos os thresholds usam a unidade do ativo quote.

## Estrutura do Projeto

```
ogaden/          # Pacote Python: engine, analysis, lógica de trading, dashboard
docker/          # Dockerfiles para os containers engine e dashboard
make/            # Scripts de build e instalação
tests/           # Suite de testes
```

## Desenvolvimento

```bash
make setup      # Cria o .venv e instala as dependências (apenas na primeira vez)
make test       # Executa todos os testes
make quality    # Formatação, lint e verificação de tipos
make install    # Instala os entry points em ~/.local/bin
```

## Licença

Este projeto está licenciado sob a Licença MIT — veja [LICENSE](LICENSE) para mais detalhes.
