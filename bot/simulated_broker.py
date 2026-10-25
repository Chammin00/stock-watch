import json
import uuid
from pathlib import Path
from bot.broker_base import AccountInfo, BaseBroker, OrderResult, Position
from data.fetcher import DataFetcher


class SimulatedBroker(BaseBroker):
    """Local, file-persisted paper trading broker."""

    def __init__(self, state_file: str = "paper_portfolio.json", initial_cash: float = 100000.0):
        self.state_file = Path(state_file)
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, dict] = {}  # {ticker: {"shares": int, "avg_entry": float}}
        self.order_history: list[dict] = []
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.cash = float(data.get("cash", self.initial_cash))
                    self.positions = data.get("positions", {})
                    self.order_history = data.get("order_history", [])
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_file, "w") as f:
                json.dump(
                    {
                        "cash": self.cash,
                        "positions": self.positions,
                        "order_history": self.order_history,
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    def get_account(self) -> AccountInfo:
        positions = self.get_positions()
        pos_value = sum(p.market_value for p in positions)
        total_value = self.cash + pos_value
        return AccountInfo(
            cash=round(self.cash, 2),
            buying_power=round(self.cash, 2),
            portfolio_value=round(total_value, 2),
        )

    def get_positions(self) -> list[Position]:
        result = []
        for ticker, data in list(self.positions.items()):
            shares = data["shares"]
            if shares <= 0:
                continue
            avg_entry = data["avg_entry"]
            quote = DataFetcher.get_latest_quote(ticker)
            curr_price = quote.get("price", avg_entry)
            market_val = shares * curr_price
            pnl = (curr_price - avg_entry) * shares
            pnl_pct = ((curr_price - avg_entry) / avg_entry) * 100.0

            result.append(
                Position(
                    ticker=ticker,
                    shares=shares,
                    avg_entry_price=round(avg_entry, 2),
                    current_price=round(curr_price, 2),
                    market_value=round(market_val, 2),
                    unrealized_pnl=round(pnl, 2),
                    unrealized_pnl_pct=round(pnl_pct, 2),
                )
            )
        return result

    def submit_order(
        self,
        ticker: str,
        shares: int,
        side: str,
        order_type: str = "market",
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> OrderResult:
        ticker = ticker.upper()
        side = side.lower()
        quote = DataFetcher.get_latest_quote(ticker)
        current_price = quote.get("price")

        if not current_price:
            return OrderResult(
                order_id=str(uuid.uuid4())[:8],
                ticker=ticker,
                shares=shares,
                side=side,
                order_type=order_type,
                status="rejected",
                filled_price=0.0,
                message="Unable to fetch current market quote.",
            )

        fill_price = limit_price if (order_type == "limit" and limit_price) else current_price

        if side == "buy":
            cost = shares * fill_price
            if cost > self.cash:
                return OrderResult(
                    order_id=str(uuid.uuid4())[:8],
                    ticker=ticker,
                    shares=shares,
                    side=side,
                    order_type=order_type,
                    status="rejected",
                    filled_price=0.0,
                    message=f"Insufficient buying power (${self.cash:.2f} available, ${cost:.2f} required).",
                )

            self.cash -= cost
            existing = self.positions.get(ticker, {"shares": 0, "avg_entry": 0.0})
            new_shares = existing["shares"] + shares
            new_avg = ((existing["shares"] * existing["avg_entry"]) + cost) / new_shares
            self.positions[ticker] = {"shares": new_shares, "avg_entry": new_avg}

        elif side == "sell":
            existing = self.positions.get(ticker, {"shares": 0, "avg_entry": 0.0})
            if existing["shares"] < shares:
                return OrderResult(
                    order_id=str(uuid.uuid4())[:8],
                    ticker=ticker,
                    shares=shares,
                    side=side,
                    order_type=order_type,
                    status="rejected",
                    filled_price=0.0,
                    message=f"Cannot sell {shares} shares; only {existing['shares']} shares owned.",
                )

            revenue = shares * fill_price
            self.cash += revenue
            remaining_shares = existing["shares"] - shares
            if remaining_shares == 0:
                del self.positions[ticker]
            else:
                self.positions[ticker]["shares"] = remaining_shares

        order_id = str(uuid.uuid4())[:8]
        order_record = {
            "order_id": order_id,
            "ticker": ticker,
            "shares": shares,
            "side": side,
            "price": round(fill_price, 2),
            "status": "filled",
        }
        self.order_history.append(order_record)
        self._save_state()

        return OrderResult(
            order_id=order_id,
            ticker=ticker,
            shares=shares,
            side=side,
            order_type=order_type,
            status="filled",
            filled_price=round(fill_price, 2),
            message=f"Successfully filled {side.upper()} {shares} {ticker} @ ${fill_price:.2f}",
        )

    def close_position(self, ticker: str) -> OrderResult:
        ticker = ticker.upper()
        if ticker not in self.positions:
            return OrderResult(
                order_id=str(uuid.uuid4())[:8],
                ticker=ticker,
                shares=0,
                side="sell",
                order_type="market",
                status="rejected",
                filled_price=0.0,
                message=f"No open position in {ticker}.",
            )
        shares = self.positions[ticker]["shares"]
        return self.submit_order(ticker, shares=shares, side="sell", order_type="market")
