import logging
from bot.broker_base import BaseBroker
from core.risk_manager import RiskManager
from data.fetcher import DataFetcher
from backtesting.strategies import BaseStrategy

logger = logging.getLogger(__name__)


class AutoTrader:
    """Executes trades across watchlists based on quantitative strategy signals and risk rules."""

    def __init__(self, broker: BaseBroker, strategy: BaseStrategy, risk_manager: RiskManager):
        self.broker = broker
        self.strategy = strategy
        self.risk_manager = risk_manager

    def evaluate_and_trade(self, tickers: list[str]) -> list[dict]:
        account = self.broker.get_account()
        positions = {p.ticker: p for p in self.broker.get_positions()}
        actions_taken = []

        for ticker in tickers:
            ticker = ticker.upper()
            df = DataFetcher.get_history(ticker, period="6mo")
            if df.empty or len(df) < 30:
                continue

            signals = self.strategy.generate_signals(df)
            last_row = signals.iloc[-1]
            signal = int(last_row.get("signal", 0))
            current_price = float(last_row["Close"])

            # 1. Exit logic: If we hold a position and sell signal is triggered
            if ticker in positions and signal == -1:
                result = self.broker.close_position(ticker)
                actions_taken.append({
                    "ticker": ticker,
                    "action": "CLOSE",
                    "reason": "Strategy Sell Signal",
                    "details": result.message,
                })

            # 2. Entry logic: If we do NOT hold a position and buy signal is triggered
            elif ticker not in positions and signal == 1:
                stop_loss = float(last_row.get("stop_loss", current_price * 0.95))
                take_profit = float(last_row.get("take_profit", current_price * 1.10))

                plan = self.risk_manager.calculate_plan(
                    ticker=ticker,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    target_1=take_profit,
                    account_size=account.portfolio_value,
                )

                if plan.shares > 0 and (plan.shares * current_price) <= account.buying_power:
                    order = self.broker.submit_order(
                        ticker=ticker,
                        shares=plan.shares,
                        side="buy",
                        order_type="market",
                    )
                    actions_taken.append({
                        "ticker": ticker,
                        "action": "BUY",
                        "shares": plan.shares,
                        "stop_loss": plan.stop_loss,
                        "target_1": plan.target_1,
                        "dollar_risk": plan.dollar_risk,
                        "details": order.message,
                    })

        return actions_taken
