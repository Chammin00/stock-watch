# Institutional Stock Analysis & Algorithmic Trading Suite

A comprehensive quantitative trading, technical analysis, and automated execution framework in Python.

---

## 🚀 Features

1. **Trade Planning & Position Sizing Calculator (`plan`):**
   * Computes dynamic share sizing derived from **dollar risk to invalidation** (never arbitrary lot sizes).
   * Calculates exact R-multiples, reward-to-risk ratios, and Half-Kelly sizing fractions.
   * Auto-calculates ATR-based stops if manual levels aren't specified.

2. **Market Screener & Coiling Detector (`scan`):**
   * Multi-criteria technical scanner for **Volatility Squeezes / Coils** (Bollinger Bands inside Keltner Channels).
   * Detects **Squeeze Fired** breakouts, **Wyckoff Springs** (liquidity sweeps), and **Volume Surges** (> 2x 20-day volume).
   * Includes preset watchlists (`tech`, `growth_turnaround`, `crypto_proxies`, `biotech_health`, `index_etfs`).

3. **Quantitative Strategy Backtesting Engine (`backtest`):**
   * Event-driven backtester with realistic slippage modeling and dynamic position sizing.
   * Built-in strategies:
     * `squeeze`: John Carter's Volatility Squeeze Breakout with MACD confirmation.
     * `spring`: Wyckoff false breakdown reclaim with volume confirmation.
     * `pullback`: 21 EMA pullback in Stage-2 trend with RSI reset.
   * Comprehensive metrics: Net P&L vs Buy & Hold, Win Rate %, Profit Factor, Max Drawdown %, and Sharpe Ratio.

4. **Automated Trading Bots & Broker APIs (`bot`):**
   * **Simulated Paper Broker:** Local, file-persisted paper trading simulator with $100,000 virtual balance.
   * **Alpaca Broker Integration:** Direct connection to Alpaca's Paper or Live trading API via `alpaca-py`.
   * **AutoTrader:** Automated execution loop evaluating watchlists and executing risk-managed orders.

---

## 🛠️ Usage Examples

Run commands using `uv run python cli.py <subcommand>`:

### 1. Plan a Trade (e.g. TDOC)
```bash
# Plan TDOC with a $5.50 stop and $8.00 target
uv run python cli.py plan TDOC --stop 5.50 --target 8.00 --risk 1.0

# Plan BMNR with automatic ATR stop and targets
uv run python cli.py plan BMNR
```

### 2. Scan the Market for Coiling & Breakouts
```bash
# Scan preset watchlists
uv run python cli.py scan --preset growth_turnaround
uv run python cli.py scan --preset crypto_proxies

# Scan custom tickers
uv run python cli.py scan --tickers TDOC,BMNR,NVDA,COIN,MSTR,AAPL
```

### 3. Backtest a Strategy
```bash
# Backtest the Volatility Squeeze Strategy on TDOC over 2 years
uv run python cli.py backtest TDOC --strategy squeeze --period 2y --show-trades

# Backtest the Wyckoff Spring Strategy on BMNR
uv run python cli.py backtest BMNR --strategy spring --period 1y
```

### 4. Paper Trade / Run the Bot
```bash
# Check current paper trading portfolio & positions
uv run python cli.py bot

# Evaluate strategy and auto-execute paper trades on TDOC & BMNR
uv run python cli.py bot --trade TDOC,BMNR
```
