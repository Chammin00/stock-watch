import argparse
import sys
import warnings

# Suppress library deprecation warnings and ensure UTF-8 on Windows
warnings.filterwarnings("ignore")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backtesting.engine import BacktestEngine
from backtesting.strategies import TrendPullbackStrategy, VolatilitySqueezeStrategy, WyckoffSpringStrategy
from bot.alpaca_broker import AlpacaBroker
from bot.simulated_broker import SimulatedBroker
from bot.trader import AutoTrader
from config import DEFAULT_ACCOUNT_SIZE, DEFAULT_RISK_PER_TRADE, PRESET_WATCHLISTS
from core.indicators import attach_all_indicators
from core.risk_manager import RiskManager
from data.fetcher import DataFetcher
from screener.alerts import display_scan_results
from screener.scanner import MarketScanner

console = Console(force_terminal=True, legacy_windows=False)


def handle_plan(args):
    """Handle technical analysis & trade planning calculator."""
    ticker = args.ticker.upper()
    quote = DataFetcher.get_latest_quote(ticker)
    curr_price = quote.get("price")

    if not curr_price:
        console.print(f"[bold red]Error: Could not retrieve market data for {ticker}[/bold red]")
        sys.exit(1)

    entry = args.entry if args.entry else curr_price

    # Fetch ATR if stop/target not provided
    df = DataFetcher.get_history(ticker, period="3mo")
    atr = 1.0
    if not df.empty and len(df) >= 14:
        df_ind = attach_all_indicators(df)
        atr = float(df_ind["atr"].iloc[-1])

    if args.stop:
        stop = args.stop
    else:
        stop, def_t1, def_t2 = RiskManager.calculate_atr_stops(entry, atr, multiplier=1.5)

    if args.target:
        t1 = args.target
        t2 = args.target2
    else:
        _, t1, t2 = RiskManager.calculate_atr_stops(entry, atr, multiplier=1.5)

    rm = RiskManager(account_size=args.account, default_risk_pct=args.risk / 100.0)
    plan = rm.calculate_plan(
        ticker=ticker,
        entry_price=entry,
        stop_loss=stop,
        target_1=t1,
        target_2=t2,
    )

    table = Table(title=f"🎯 Trade Blueprint: {plan.ticker} ({plan.direction})", border_style="cyan")
    table.add_column("Parameter", style="bold white")
    table.add_column("Value", style="bold green", justify="right")
    table.add_column("Notes / Rationale", style="dim")

    table.add_row("Account Equity", f"${plan.account_size:,.2f}", "Total portfolio capital")
    table.add_row("Risk Budget", f"{plan.risk_percent:.2f}% (${plan.dollar_risk:,.2f})", "Maximum allowable dollar loss")
    table.add_row("Entry Price", f"${plan.entry_price:.2f}", "Current / Planned execution point")
    table.add_row("Stop Loss", f"${plan.stop_loss:.2f}", f"Risk per share: ${plan.risk_per_share:.2f}")
    table.add_row("Shares to Buy", f"{plan.shares:,} shares", "Derived dynamically from risk per share")
    table.add_row("Capital Allocated", f"${plan.capital_required:,.2f}", f"{(plan.capital_required / plan.account_size) * 100:.1f}% of portfolio")
    table.add_row("Primary Target (T1)", f"${plan.target_1:.2f}", f"Reward: +${plan.reward_target_1:.2f} | R:R = {plan.rr_ratio_1:.2f}R")

    if plan.target_2:
        table.add_row("Secondary Target (T2)", f"${plan.target_2:.2f}", f"Reward: +${plan.reward_target_2:.2f} | R:R = {plan.rr_ratio_2:.2f}R")

    table.add_row("Half-Kelly Sizing", f"{plan.kelly_fraction * 100:.1f}%", "Max optimal capital exposure")

    console.print(table)


def handle_scan(args):
    """Handle market scanner execution."""
    tickers = []
    if args.preset:
        tickers = PRESET_WATCHLISTS.get(args.preset.lower(), [])
        if not tickers:
            console.print(f"[bold red]Unknown preset '{args.preset}'. Available: {list(PRESET_WATCHLISTS.keys())}[/bold red]")
            sys.exit(1)
        title = f"Preset Watchlist: {args.preset.upper()}"
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
        title = f"Custom Watchlist ({len(tickers)} tickers)"
    else:
        tickers = ["TDOC", "BMNR", "AAPL", "NVDA", "TSLA", "COIN", "MSTR", "AMD"]
        title = "Default Focus Watchlist"

    console.print(f"[cyan]Scanning {len(tickers)} tickers for volatility coils, volume surges, and springs...[/cyan]")
    scanner = MarketScanner()
    results = scanner.scan_watchlist(tickers)
    display_scan_results(results, title=title)


def handle_backtest(args):
    """Handle strategy backtesting."""
    ticker = args.ticker.upper()
    console.print(f"[cyan]Fetching {args.period} history for {ticker}...[/cyan]")
    df = DataFetcher.get_history(ticker, period=args.period)

    if df.empty:
        console.print(f"[bold red]Could not fetch historical data for {ticker}[/bold red]")
        sys.exit(1)

    strat_choice = args.strategy.lower()
    if strat_choice == "squeeze":
        strategy = VolatilitySqueezeStrategy()
    elif strat_choice == "spring":
        strategy = WyckoffSpringStrategy()
    elif strat_choice == "pullback":
        strategy = TrendPullbackStrategy()
    else:
        console.print(f"[bold red]Unknown strategy '{args.strategy}'. Choose: squeeze, spring, pullback[/bold red]")
        sys.exit(1)

    engine = BacktestEngine(initial_capital=args.capital, risk_per_trade=args.risk / 100.0)
    res = engine.run(df, strategy, ticker=ticker)

    table = Table(title=f"📈 Backtest Performance: {res.ticker} [{res.strategy_name}]", border_style="green")
    table.add_column("Metric", style="bold white")
    table.add_column("Result", justify="right")

    ret_style = "green" if res.total_return_pct >= 0 else "red"
    bh_style = "green" if res.buy_and_hold_return_pct >= 0 else "red"

    table.add_row("Initial Capital", f"${res.initial_capital:,.2f}")
    table.add_row("Final Equity", f"${res.final_equity:,.2f}")
    table.add_row("Strategy Net Return", f"[{ret_style}]{res.total_return_pct:+.2f}% (${res.net_profit:+,.2f})[/{ret_style}]")
    table.add_row("Buy & Hold Return", f"[{bh_style}]{res.buy_and_hold_return_pct:+.2f}%[/{bh_style}]")
    table.add_row("Total Trades", str(res.total_trades))
    table.add_row("Win Rate", f"{res.win_rate_pct:.1f}% ({res.winning_trades} W / {res.losing_trades} L)")
    table.add_row("Profit Factor", f"{res.profit_factor:.2f}")
    table.add_row("Max Drawdown", f"[red]-{res.max_drawdown_pct:.2f}%[/red]")
    table.add_row("Sharpe Ratio", f"{res.sharpe_ratio:.2f}")
    table.add_row("Average Win", f"${res.avg_win:,.2f}")
    table.add_row("Average Loss", f"-${res.avg_loss:,.2f}")

    console.print(table)

    if res.trades and args.show_trades:
        trade_table = Table(title="📜 Trade Execution Log", border_style="dim")
        trade_table.add_column("Entry Date", justify="center")
        trade_table.add_column("Entry ($)", justify="right")
        trade_table.add_column("Shares", justify="right")
        trade_table.add_column("Exit Date", justify="center")
        trade_table.add_column("Exit ($)", justify="right")
        trade_table.add_column("P&L ($)", justify="right")
        trade_table.add_column("Return %", justify="right")
        trade_table.add_column("Exit Reason", justify="left")

        for t in res.trades[-10:]:  # Show last 10 trades
            pnl_style = "green" if t.pnl >= 0 else "red"
            trade_table.add_row(
                t.entry_date,
                f"${t.entry_price:.2f}",
                f"{t.shares:,}",
                t.exit_date,
                f"${t.exit_price:.2f}",
                f"[{pnl_style}]${t.pnl:+,.2f}[/{pnl_style}]",
                f"[{pnl_style}]{t.return_pct:+.2f}%[/{pnl_style}]",
                t.exit_reason,
            )
        console.print(trade_table)


def handle_bot(args):
    """Handle paper/live bot trading execution."""
    if args.alpaca:
        console.print("[bold yellow]Connecting to Alpaca Broker...[/bold yellow]")
        broker = AlpacaBroker()
    else:
        console.print("[bold green]Connecting to Simulated Paper Broker...[/bold green]")
        broker = SimulatedBroker()

    acct = broker.get_account()
    pos_table = Table(title=f"💼 Portfolio Overview ({'Alpaca' if args.alpaca else 'Simulated'})", border_style="blue")
    pos_table.add_column("Cash Available", justify="right")
    pos_table.add_column("Buying Power", justify="right")
    pos_table.add_column("Total Portfolio Value", justify="right", style="bold green")
    pos_table.add_row(f"${acct.cash:,.2f}", f"${acct.buying_power:,.2f}", f"${acct.portfolio_value:,.2f}")
    console.print(pos_table)

    positions = broker.get_positions()
    if positions:
        pos_details = Table(title="Open Positions", border_style="cyan")
        pos_details.add_column("Ticker", style="bold")
        pos_details.add_column("Shares", justify="right")
        pos_details.add_column("Avg Entry", justify="right")
        pos_details.add_column("Current", justify="right")
        pos_details.add_column("Market Value", justify="right")
        pos_details.add_column("Unrealized P&L", justify="right")

        for p in positions:
            pnl_col = "green" if p.unrealized_pnl >= 0 else "red"
            pos_details.add_row(
                p.ticker,
                str(p.shares),
                f"${p.avg_entry_price:.2f}",
                f"${p.current_price:.2f}",
                f"${p.market_value:,.2f}",
                f"[{pnl_col}]${p.unrealized_pnl:+,.2f} ({p.unrealized_pnl_pct:+.2f}%)[/{pnl_col}]",
            )
        console.print(pos_details)
    else:
        console.print("[dim]No active open positions.[/dim]")

    if args.trade:
        tickers = [t.strip().upper() for t in args.trade.split(",")]
        strategy = VolatilitySqueezeStrategy()
        risk_mgr = RiskManager(account_size=acct.portfolio_value)
        trader = AutoTrader(broker, strategy, risk_mgr)

        console.print(f"[yellow]Evaluating trading strategy on: {tickers}...[/yellow]")
        actions = trader.evaluate_and_trade(tickers)
        if actions:
            for act in actions:
                console.print(f"[bold green]Action:[/bold green] {act}")
        else:
            console.print("[dim]No entry or exit triggers met for the selected tickers.[/dim]")


def main():
    parser = argparse.ArgumentParser(
        description="Institutional Trading & Chart Analysis Terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: plan
    p_plan = subparsers.add_parser("plan", help="Technical analysis & position sizing calculator")
    p_plan.add_argument("ticker", help="Stock ticker symbol (e.g. TDOC, BMNR)")
    p_plan.add_argument("--entry", type=float, help="Planned entry price (defaults to current live price)")
    p_plan.add_argument("--stop", type=float, help="Technical stop-loss price (defaults to 1.5 ATR)")
    p_plan.add_argument("--target", type=float, help="Target 1 price")
    p_plan.add_argument("--target2", type=float, help="Target 2 price")
    p_plan.add_argument("--account", type=float, default=DEFAULT_ACCOUNT_SIZE, help="Account size ($)")
    p_plan.add_argument("--risk", type=float, default=1.0, help="Account risk % per trade (e.g. 1.0 = 1%)")

    # Command: scan
    p_scan = subparsers.add_parser("scan", help="Scan watchlists for coiling, volume surges, and springs")
    p_scan.add_argument("--preset", help=f"Preset watchlist: {list(PRESET_WATCHLISTS.keys())}")
    p_scan.add_argument("--tickers", help="Comma-separated ticker list (e.g. TDOC,BMNR,NVDA,COIN)")

    # Command: backtest
    p_bt = subparsers.add_parser("backtest", help="Backtest quantitative strategies on historical data")
    p_bt.add_argument("ticker", help="Stock ticker symbol (e.g. TDOC)")
    p_bt.add_argument("--strategy", default="squeeze", help="Strategy to test: squeeze, spring, pullback")
    p_bt.add_argument("--period", default="2y", help="Historical period: 6mo, 1y, 2y, 5y")
    p_bt.add_argument("--capital", type=float, default=100000.0, help="Initial backtest capital ($)")
    p_bt.add_argument("--risk", type=float, default=1.0, help="Risk % per trade")
    p_bt.add_argument("--show-trades", action="store_true", help="Display trade execution history")

    # Command: bot
    p_bot = subparsers.add_parser("bot", help="Automated paper trading or Alpaca execution")
    p_bot.add_argument("--alpaca", action="store_true", help="Use Alpaca API instead of local paper broker")
    p_bot.add_argument("--trade", help="Comma-separated tickers to evaluate and execute trades on")

    args = parser.parse_args()

    if args.command == "plan":
        handle_plan(args)
    elif args.command == "scan":
        handle_scan(args)
    elif args.command == "backtest":
        handle_backtest(args)
    elif args.command == "bot":
        handle_bot(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
