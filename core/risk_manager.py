from dataclasses import dataclass
import math


@dataclass
class TradePlan:
    ticker: str
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float | None
    account_size: float
    risk_percent: float
    shares: int
    capital_required: float
    dollar_risk: float
    risk_per_share: float
    reward_target_1: float
    rr_ratio_1: float
    reward_target_2: float | None
    rr_ratio_2: float | None
    kelly_fraction: float | None


class RiskManager:
    """Institutional Risk Management and Position Sizing Calculator."""

    def __init__(self, account_size: float = 100000.0, default_risk_pct: float = 0.01):
        self.account_size = float(account_size)
        self.default_risk_pct = float(default_risk_pct)

    def calculate_plan(
        self,
        ticker: str,
        entry_price: float,
        stop_loss: float,
        target_1: float,
        target_2: float | None = None,
        risk_percent: float | None = None,
        account_size: float | None = None,
        win_rate: float = 0.50,
        win_loss_ratio: float = 2.0,
    ) -> TradePlan:
        acct = account_size if account_size is not None else self.account_size
        risk_pct = risk_percent if risk_percent is not None else self.default_risk_pct

        # Determine direction
        if entry_price > stop_loss:
            direction = "LONG"
            risk_per_share = entry_price - stop_loss
            reward_1 = target_1 - entry_price
            reward_2 = (target_2 - entry_price) if target_2 else None
        else:
            direction = "SHORT"
            risk_per_share = stop_loss - entry_price
            reward_1 = entry_price - target_1
            reward_2 = (entry_price - target_2) if target_2 else None

        if risk_per_share <= 0:
            raise ValueError("Invalid stop loss: Risk per share must be positive.")

        # Dollar risk allowed on this trade
        dollar_risk = acct * risk_pct

        # Maximum shares allowed by risk
        shares = int(dollar_risk / risk_per_share)
        if shares < 1:
            shares = 1

        capital_required = shares * entry_price

        # Actual dollar risk given discrete integer shares
        actual_dollar_risk = shares * risk_per_share

        rr_ratio_1 = reward_1 / risk_per_share
        rr_ratio_2 = (reward_2 / risk_per_share) if reward_2 else None

        # Kelly Criterion Calculation: K = W - (1 - W) / R
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        half_kelly = max(0.0, kelly / 2.0)

        return TradePlan(
            ticker=ticker.upper(),
            direction=direction,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            target_1=round(target_1, 2),
            target_2=round(target_2, 2) if target_2 else None,
            account_size=round(acct, 2),
            risk_percent=round(risk_pct * 100, 2),
            shares=shares,
            capital_required=round(capital_required, 2),
            dollar_risk=round(actual_dollar_risk, 2),
            risk_per_share=round(risk_per_share, 2),
            reward_target_1=round(reward_1, 2),
            rr_ratio_1=round(rr_ratio_1, 2),
            reward_target_2=round(reward_2, 2) if reward_2 else None,
            rr_ratio_2=round(rr_ratio_2, 2) if rr_ratio_2 else None,
            kelly_fraction=round(half_kelly, 4),
        )

    @staticmethod
    def calculate_atr_stops(
        entry_price: float, atr: float, multiplier: float = 1.5, direction: str = "LONG"
    ) -> tuple[float, float, float]:
        """Calculates dynamic stop loss and targets based on ATR multiples."""
        dist = atr * multiplier
        if direction.upper() == "LONG":
            stop = entry_price - dist
            t1 = entry_price + (dist * 1.5)  # 1.5R
            t2 = entry_price + (dist * 3.0)  # 3.0R
        else:
            stop = entry_price + dist
            t1 = entry_price - (dist * 1.5)
            t2 = entry_price - (dist * 3.0)
        return round(stop, 2), round(t1, 2), round(t2, 2)
