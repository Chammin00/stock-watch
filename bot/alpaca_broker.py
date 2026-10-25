import logging
from bot.broker_base import AccountInfo, BaseBroker, OrderResult, Position
from config import ALPACA_API_KEY, ALPACA_PAPER, ALPACA_SECRET_KEY

logger = logging.getLogger(__name__)


class AlpacaBroker(BaseBroker):
    """Alpaca paper or live brokerage integration."""

    def __init__(self, api_key: str | None = None, secret_key: str | None = None, paper: bool | None = None):
        self.api_key = api_key or ALPACA_API_KEY
        self.secret_key = secret_key or ALPACA_SECRET_KEY
        self.paper = paper if paper is not None else ALPACA_PAPER
        self.client = None

        if not self.api_key or not self.secret_key:
            logger.warning("Alpaca API credentials missing. Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env.")
            return

        try:
            from alpaca.trading.client import TradingClient
            self.client = TradingClient(self.api_key, self.secret_key, paper=self.paper)
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca TradingClient: {e}")

    def get_account(self) -> AccountInfo:
        if not self.client:
            raise ConnectionError("Alpaca credentials not configured.")
        acct = self.client.get_account()
        return AccountInfo(
            cash=float(acct.cash),
            buying_power=float(acct.buying_power),
            portfolio_value=float(acct.portfolio_value),
            currency=acct.currency,
        )

    def get_positions(self) -> list[Position]:
        if not self.client:
            return []
        positions = self.client.get_all_positions()
        res = []
        for p in positions:
            res.append(
                Position(
                    ticker=p.symbol,
                    shares=int(p.qty),
                    avg_entry_price=float(p.avg_entry_price),
                    current_price=float(p.current_price),
                    market_value=float(p.market_value),
                    unrealized_pnl=float(p.unrealized_pl),
                    unrealized_pnl_pct=float(p.unrealized_plpc) * 100.0,
                )
            )
        return res

    def submit_order(
        self,
        ticker: str,
        shares: int,
        side: str,
        order_type: str = "market",
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> OrderResult:
        if not self.client:
            raise ConnectionError("Alpaca credentials not configured.")

        from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
        from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        try:
            if order_type.lower() == "market":
                req = MarketOrderRequest(
                    symbol=ticker.upper(),
                    qty=shares,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                )
            elif order_type.lower() == "limit" and limit_price:
                req = LimitOrderRequest(
                    symbol=ticker.upper(),
                    qty=shares,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=limit_price,
                )
            else:
                raise ValueError("Unsupported order type or missing limit price.")

            order = self.client.submit_order(order_data=req)
            return OrderResult(
                order_id=str(order.id),
                ticker=ticker.upper(),
                shares=shares,
                side=side,
                order_type=order_type,
                status=str(order.status),
                filled_price=float(order.filled_avg_price or 0.0),
                message=f"Order submitted: {order.status}",
            )
        except Exception as e:
            return OrderResult(
                order_id="",
                ticker=ticker.upper(),
                shares=shares,
                side=side,
                order_type=order_type,
                status="failed",
                filled_price=0.0,
                message=f"Order error: {e}",
            )

    def close_position(self, ticker: str) -> OrderResult:
        if not self.client:
            raise ConnectionError("Alpaca credentials not configured.")
        try:
            self.client.close_position(ticker.upper())
            return OrderResult(
                order_id="",
                ticker=ticker.upper(),
                shares=0,
                side="sell",
                order_type="market",
                status="closed",
                filled_price=0.0,
                message=f"Closed position in {ticker.upper()}",
            )
        except Exception as e:
            return OrderResult(
                order_id="",
                ticker=ticker.upper(),
                shares=0,
                side="sell",
                order_type="market",
                status="failed",
                filled_price=0.0,
                message=f"Error closing position: {e}",
            )
