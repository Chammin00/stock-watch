from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from backtesting.strategies import BaseStrategy


@dataclass
class Trade:
    ticker: str
    entry_date: str
    entry_price: float
    shares: int
    stop_loss: float
    take_profit: float
    exit_date: str = ""
    exit_price: float = 0.0
    pnl: float = 0.0
    return_pct: float = 0.0
    exit_reason: str = ""
    is_closed: bool = False


@dataclass
class BacktestResult:
    ticker: str
    strategy_name: str
    initial_capital: float
    final_equity: float
    net_profit: float
    total_return_pct: float
    buy_and_hold_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    avg_win: float
    avg_loss: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)


class BacktestEngine:
    """Event-driven simulation backtesting engine with risk management."""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        risk_per_trade: float = 0.01,
        slippage_pct: float = 0.0005,  # 5 bps slippage
    ):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.slippage_pct = slippage_pct

    def run(self, df: pd.DataFrame, strategy: BaseStrategy, ticker: str = "TICKER") -> BacktestResult:
        if df.empty or len(df) < 30:
            raise ValueError(f"Insufficient historical data for {ticker}")

        data = strategy.generate_signals(df)

        capital = self.initial_capital
        equity = capital
        open_trade: Trade | None = None
        closed_trades: list[Trade] = []
        equity_records = []

        buy_and_hold_start = data["Close"].iloc[0]
        buy_and_hold_end = data["Close"].iloc[-1]
        buy_and_hold_pct = ((buy_and_hold_end - buy_and_hold_start) / buy_and_hold_start) * 100.0

        for i in range(len(data)):
            row = data.iloc[i]
            date = str(data.index[i].date() if hasattr(data.index[i], "date") else data.index[i])
            close = float(row["Close"])
            high = float(row["High"])
            low = float(row["Low"])
            signal = int(row.get("signal", 0))

            # Check open trade exit conditions first
            if open_trade is not None:
                # 1. Stop loss hit
                if low <= open_trade.stop_loss:
                    exit_price = open_trade.stop_loss * (1.0 - self.slippage_pct)
                    pnl = (exit_price - open_trade.entry_price) * open_trade.shares
                    capital += (open_trade.shares * exit_price)
                    open_trade.exit_date = date
                    open_trade.exit_price = round(exit_price, 2)
                    open_trade.pnl = round(pnl, 2)
                    open_trade.return_pct = round(((exit_price - open_trade.entry_price) / open_trade.entry_price) * 100.0, 2)
                    open_trade.exit_reason = "Stop Loss Hit"
                    open_trade.is_closed = True
                    closed_trades.append(open_trade)
                    open_trade = None

                # 2. Take profit hit
                elif high >= open_trade.take_profit:
                    exit_price = open_trade.take_profit * (1.0 - self.slippage_pct)
                    pnl = (exit_price - open_trade.entry_price) * open_trade.shares
                    capital += (open_trade.shares * exit_price)
                    open_trade.exit_date = date
                    open_trade.exit_price = round(exit_price, 2)
                    open_trade.pnl = round(pnl, 2)
                    open_trade.return_pct = round(((exit_price - open_trade.entry_price) / open_trade.entry_price) * 100.0, 2)
                    open_trade.exit_reason = "Take Profit Hit"
                    open_trade.is_closed = True
                    closed_trades.append(open_trade)
                    open_trade = None

                # 3. Strategy Sell Signal
                elif signal == -1:
                    exit_price = close * (1.0 - self.slippage_pct)
                    pnl = (exit_price - open_trade.entry_price) * open_trade.shares
                    capital += (open_trade.shares * exit_price)
                    open_trade.exit_date = date
                    open_trade.exit_price = round(exit_price, 2)
                    open_trade.pnl = round(pnl, 2)
                    open_trade.return_pct = round(((exit_price - open_trade.entry_price) / open_trade.entry_price) * 100.0, 2)
                    open_trade.exit_reason = "Strategy Exit Signal"
                    open_trade.is_closed = True
                    closed_trades.append(open_trade)
                    open_trade = None

            # Check new entry condition if no open trade
            if open_trade is None and signal == 1:
                entry_price = close * (1.0 + self.slippage_pct)
                stop_loss = float(row.get("stop_loss", entry_price * 0.95))
                take_profit = float(row.get("take_profit", entry_price * 1.10))

                risk_per_share = entry_price - stop_loss
                if risk_per_share > 0:
                    dollar_risk = capital * self.risk_per_trade
                    shares = int(dollar_risk / risk_per_share)
                    max_shares = int(capital / entry_price)
                    shares = min(shares, max_shares)

                    if shares > 0:
                        cost = shares * entry_price
                        capital -= cost
                        open_trade = Trade(
                            ticker=ticker.upper(),
                            entry_date=date,
                            entry_price=round(entry_price, 2),
                            shares=shares,
                            stop_loss=round(stop_loss, 2),
                            take_profit=round(take_profit, 2),
                        )

            # Record current equity
            current_equity = capital
            if open_trade is not None:
                current_equity += open_trade.shares * close
            equity_records.append(current_equity)

        # Close any open trade at the end of the data
        if open_trade is not None:
            final_price = float(data["Close"].iloc[-1])
            pnl = (final_price - open_trade.entry_price) * open_trade.shares
            capital += open_trade.shares * final_price
            open_trade.exit_date = str(data.index[-1].date() if hasattr(data.index[-1], "date") else data.index[-1])
            open_trade.exit_price = round(final_price, 2)
            open_trade.pnl = round(pnl, 2)
            open_trade.return_pct = round(((final_price - open_trade.entry_price) / open_trade.entry_price) * 100.0, 2)
            open_trade.exit_reason = "End of Backtest Period"
            open_trade.is_closed = True
            closed_trades.append(open_trade)
            open_trade = None

        final_equity = equity_records[-1] if equity_records else self.initial_capital
        net_profit = final_equity - self.initial_capital
        total_return_pct = (net_profit / self.initial_capital) * 100.0

        # Performance analytics
        eq_series = pd.Series(equity_records, index=data.index)
        running_max = eq_series.cummax()
        drawdown = (eq_series - running_max) / running_max
        max_drawdown_pct = abs(float(drawdown.min())) * 100.0

        daily_returns = eq_series.pct_change().dropna()
        if daily_returns.std() > 0:
            sharpe_ratio = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252))
        else:
            sharpe_ratio = 0.0

        total_trades = len(closed_trades)
        wins = [t for t in closed_trades if t.pnl > 0]
        losses = [t for t in closed_trades if t.pnl <= 0]
        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

        avg_win = (gross_profit / len(wins)) if wins else 0.0
        avg_loss = (gross_loss / len(losses)) if losses else 0.0

        return BacktestResult(
            ticker=ticker.upper(),
            strategy_name=strategy.name,
            initial_capital=round(self.initial_capital, 2),
            final_equity=round(final_equity, 2),
            net_profit=round(net_profit, 2),
            total_return_pct=round(total_return_pct, 2),
            buy_and_hold_return_pct=round(buy_and_hold_pct, 2),
            total_trades=total_trades,
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate_pct=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            trades=closed_trades,
            equity_curve=eq_series,
        )
