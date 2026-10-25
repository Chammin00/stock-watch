from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AccountInfo:
    cash: float
    buying_power: float
    portfolio_value: float
    currency: str = "USD"


@dataclass
class Position:
    ticker: str
    shares: int
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class OrderResult:
    order_id: str
    ticker: str
    shares: int
    side: str  # "buy" or "sell"
    order_type: str  # "market" or "limit"
    status: str
    filled_price: float
    message: str


class BaseBroker(ABC):
    """Abstract interface for brokerage execution."""

    @abstractmethod
    def get_account(self) -> AccountInfo:
        pass

    @abstractmethod
    def get_positions(self) -> list[Position]:
        pass

    @abstractmethod
    def submit_order(
        self,
        ticker: str,
        shares: int,
        side: str,
        order_type: str = "market",
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> OrderResult:
        pass

    @abstractmethod
    def close_position(self, ticker: str) -> OrderResult:
        pass
