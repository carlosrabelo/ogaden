# Ogaden

Bot de trading avançado para mercados spot da Binance com múltiplos indicadores, modos de estratégia e mecanismos de segurança integrados.

## Destaques

- EMA crossover, RSI, MACD, Bandas de Bollinger, Oscilador Estocástico e análise de volume como fontes de sinal coordenadas
- Três modos de estratégia (conservador, balanceado, agressivo) com perfis de risco aplicados
- Stop loss e take profit dinâmicos baseados em ATR com ratio 2:1
- Circuit breaker para trading automaticamente ao atingir limites de drawdown ou perdas consecutivas
- Trailing stop por preço que sobe com o preço e nunca cai
- Volume SMA, Volume Ratio, OBV e VPT para validação de sinais
- Dashboard em tempo real via WebSocket com gráfico de preços e métricas de trades
- Simulação sandbox com execuções simuladas e taxa de 0,1% emulada

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

### Docker

```bash
make docker-start
```

Constrói as imagens do engine e do dashboard e inicia o stack completo com Memcached.

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

### Web Dashboard

```bash
make run-dashboard
```

Inicia o dashboard na porta **3501** com:
- **Dados de Trading em Tempo Real**: Posição, sinais, saldos, P&L
- **Gráfico de Preços ao Vivo**: Chart.js com atualizações em tempo real
- **Métricas Essenciais**: Status do circuit breaker, drawdown, perdas consecutivas, histórico de trades

### Stack Docker

```bash
make docker-start    # Constrói e inicia todos os containers
make docker-stop     # Para tudo e remove orphans
make docker-restart  # docker-stop + docker-start
```

O Docker stack inclui:
- **Engine Container**: Processo de trading
- **Dashboard Container**: Interface web com chart e métricas em tempo real
- **Memcached**: Compartilhamento de estado entre processos

Porta padrão:
- **Dashboard**: `http://localhost:3501`

## Arquitetura

```
+-------------------------------------------------------------+
|                    Ogaden Trading Bot                       |
+-------------------------------------------------------------+
|                                                             |
|  +-------------+    +------------------+    +---------+    |
|  |  Trading    |    |                  |    |         |    |
|  |  Engine     |<-->|    Memcached     |<-->| Dashboard|   |
|  |  (Python)   |    |   (State Mgmt)   |    |   (Web) |   |
|  +-------------+    +------------------+    +---------+    |
|                                                             |
+-------------------------------------------------------------+
```

### 2 Processos Independentes

1. **Engine** (`make run-engine`): Loop infinito de trading
2. **Dashboard** (`make run-dashboard`): Interface web com visualização em tempo real

### Comunicação

- **Memcached**: Compartilhamento de estado entre engine e dashboard
- **WebSocket**: Atualizações em tempo real no dashboard

> Operar com fundos reais é arriscado. Teste com `SANDBOX=true` e valores pequenos antes de ir ao vivo.

## Estratégia de Trading

### Indicadores Técnicos

O bot usa um conjunto abrangente de indicadores técnicos:

1. **Indicadores de Tendência**
   - Cruzamento de EMA (Rápida/Lenta)
   - Confirmação de Tendência EMA
   - MACD (Moving Average Convergence Divergence)

2. **Indicadores de Momento**
   - RSI (Relative Strength Index)
   - Oscilador Estocástico

3. **Indicadores de Volatilidade**
   - Bandas de Bollinger (com detecção de squeeze)
   - ATR (Average True Range)

4. **Indicadores de Volume**
   - Volume SMA
   - Volume Ratio
   - OBV (On-Balance Volume)
   - VPT (Volume Price Trend)

### Modos de Estratégia

#### Modo Conservador
- **Requisito**: 2 confirmações necessárias
- **Volume**: Obrigatório para confirmação
- **Limiares RSI**: 35 (compra) / 65 (venda)
- **Perfil de Risco**: Baixo risco, menos trades

#### Modo Balanceado
- **Requisito**: 1 confirmação necessária
- **Volume**: Confirmação opcional
- **Limiares RSI**: 40 (compra) / 60 (sell)
- **Perfil de Risco**: Risco/retorno moderado

#### Modo Agressivo
- **Requisito**: 1 sinal primário + 1 confirmação (RSI ou MACD obrigatório)
- **Cooldown**: 2 ciclos após perda
- **Tamanho de posição**: 25% do saldo (teto rígido de 30%)
- **Volume**: Confirmação opcional
- **Limiares RSI**: 45 (compra) / 55 (venda)
- **Perfil de Risco**: Maior frequência, proteção mínima aplicada

### Gestão de Risco

- **Stop Loss Dinâmico**: Baseado em ATR com multiplicador configurável (padrão 2,0)
- **Take Profit**: Ratio 2:1 baseado em ATR
- **Trailing Stop por Preço**: `TRAILING_STOP_PCT` define a distância abaixo do pico de preço; sobe com o preço e nunca cai
- **Circuit Breaker**: Para compras quando o drawdown acumulado (últimas 20 trades) excede `MAX_DRAWDOWN_PCT` ou perdas consecutivas excedem `MAX_CONSECUTIVE_LOSSES`; persiste após reinicialização — requer reset manual em `data/state.json`
- **Cooldown Após Perda**: Ciclos de pausa configurável antes da próxima compra após trade perdedor
- **Margem Mínima de Trade**: Ignora trades onde o movimento esperado (baseado em ATR) está abaixo do limite de taxa
- **Dimensionamento de Posição**: Respeita filtros da Binance (MIN_NOTIONAL, STEP_SIZE, MIN_QUANTITY)

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```
# Credenciais live (obrigatórias quando SANDBOX=false)
API_KEY=sua_chave_aqui
API_SECRET=seu_segredo_aqui

# SANDBOX=true por padrão — defina false apenas para trading real
SANDBOX=true

BASE_ASSET=BTC
QUOTE_ASSET=USDT
INTERVAL=15m
LIMIT=500
TIMEZONE=America/Cuiaba

# Modo de estratégia: conservative | balanced | aggressive
STRATEGY_MODE=balanced

# Circuit breaker (defina 0 para desabilitar)
MAX_DRAWDOWN_PCT=15.0
MAX_CONSECUTIVE_LOSSES=5

# Trailing stop por preço (0 = desabilitado)
TRAILING_STOP_PCT=0.0

MEMCACHED_HOST=localhost
MEMCACHED_PORT=11211

# Saldos iniciais (apenas sandbox)
BASE_BALANCE=0.0
QUOTE_BALANCE=10.0
```

Consulte `.env.example` para a referência completa de parâmetros incluindo todos os overrides de gestão de risco.

## Estrutura do Projeto

```
ogaden/
├── trader.py       # Orquestração de trading e ciclo de execução
├── strategy.py     # Modos de estratégia e decisões baseadas em indicadores
├── broker.py       # Execução de ordens e integração Binance
├── indicators.py   # Cálculos de indicadores técnicos
├── exchange.py     # Abstração do protocolo de exchange
├── loader.py       # Configuração a partir de variáveis de ambiente
├── persistence.py  # Save/restore atômico de estado (data/state.json)
├── dashboard.py    # Servidor Flask + WebSocket
├── engine.py       # Entry point do loop de trading
├── errors.py       # Tipos de exceção customizados
├── retry.py        # Decorator de backoff exponencial
└── rate_limiter.py # Throttling de chamadas API
docker/             # Dockerfiles para engine e dashboard
tests/              # Suite de testes (~2.6k linhas)
```

## Desenvolvimento

```bash
make setup      # Cria o .venv e instala as dependências (apenas na primeira vez)
make test       # Executa todos os testes
make quality    # Formatação, lint e verificação de tipos
```

## Licença

Este projeto está licenciado sob a Licença MIT — veja [LICENSE](LICENSE) para mais detalhes.
