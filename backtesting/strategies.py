from abc import ABC, abstractmethod
import pandas as pd
from core.indicators import attach_all_indicators


class BaseStrategy(ABC):
    """Abstract base class for quantitative trading strategies."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes raw OHLCV DataFrame, attaches indicators, and outputs:
        'signal': 1 for BUY, -1 for SELL / SHORT, 0 for HOLD
        'stop_loss': price level for stop
        'take_profit': price level for target
        """
        pass


class VolatilitySqueezeStrategy(BaseStrategy):
    """
    Carter's Squeeze Breakout Strategy:
    1. Stock enters volatility squeeze (BB inside Keltner).
    2. Squeeze fires (BB exits Keltner).
    3. Buy if close > 20 EMA and MACD histogram is positive and rising.
    4. Exit if MACD histogram turns negative or hits trailing ATR stop.
    """

    def __init__(self, atr_multiplier: float = 2.0):
        super().__init__("Volatility Squeeze Breakout")
        self.atr_multiplier = atr_multiplier

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = attach_all_indicators(df)
        data["signal"] = 0
        data["stop_loss"] = 0.0
        data["take_profit"] = 0.0

        # Conditions for entry:
        # Squeeze just fired, price > 20 EMA, momentum positive
        squeeze_fired = data["squeeze_fired"]
        bullish_momentum = data["macd_hist"] > 0
        above_ema = data["Close"] > data["ema_21"]

        buy_condition = squeeze_fired & bullish_momentum & above_ema
        exit_condition = data["macd_hist"] < 0

        data.loc[buy_condition, "signal"] = 1
        data.loc[exit_condition, "signal"] = -1

        # Dynamic stops
        data["stop_loss"] = data["Close"] - (self.atr_multiplier * data["atr"])
        data["take_profit"] = data["Close"] + (self.atr_multiplier * 2.0 * data["atr"])

        return data


class WyckoffSpringStrategy(BaseStrategy):
    """
    Wyckoff Spring (Failed Breakdown):
    1. Stock breaks below the 20-day lowest low.
    2. Reclaims that level within 1-3 bars on above-average volume.
    3. Buy on the reclaim candle close. Stop loss 1 ATR below the sweep low.
    """

    def __init__(self, lookback: int = 20, atr_multiplier: float = 1.5):
        super().__init__("Wyckoff Spring Reversal")
        self.lookback = lookback
        self.atr_multiplier = atr_multiplier

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = attach_all_indicators(df)
        data["signal"] = 0

        # Prior n-day support level
        data["prior_low"] = data["Low"].shift(1).rolling(self.lookback).min()

        # Sweep: Low went below prior low, but Close finished back ABOVE prior low
        swept_low = data["Low"] < data["prior_low"]
        reclaimed = data["Close"] > data["prior_low"]
        vol_confirmed = data["vol_surge"] > 1.2

        spring_trigger = swept_low & reclaimed & vol_confirmed
        data.loc[spring_trigger, "signal"] = 1

        # Exit when RSI becomes overbought (> 70) or crosses below 20 EMA
        exit_condition = (data["rsi"] > 70) | (data["Close"] < data["ema_21"])
        data.loc[exit_condition, "signal"] = -1

        data["stop_loss"] = data["Low"] - (self.atr_multiplier * data["atr"])
        data["take_profit"] = data["Close"] + (self.atr_multiplier * 2.5 * data["atr"])

        return data


class TrendPullbackStrategy(BaseStrategy):
    """
    Trend Following Pullback:
    1. Trend filter: Close > 50 SMA > 200 SMA (Strong Stage 2 uptrend).
    2. Pullback: Low touches or drops near 21 EMA.
    3. RSI between 40 and 55 (reset from overbought, not broken).
    4. Close rebounds above 9 EMA.
    """

    def __init__(self, atr_multiplier: float = 2.0):
        super().__init__("Trend Pullback to 21 EMA")
        self.atr_multiplier = atr_multiplier

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = attach_all_indicators(df)
        data["signal"] = 0

        uptrend = (data["Close"] > data["sma_50"]) & (data["sma_50"] > data["sma_200"])
        pullback = (data["Low"] <= data["ema_21"] * 1.01) & (data["Close"] >= data["ema_21"] * 0.98)
        rsi_healthy = (data["rsi"] >= 40) & (data["rsi"] <= 60)
        rebound = data["Close"] > data["ema_9"]

        entry = uptrend & pullback & rsi_healthy & rebound
        data.loc[entry, "signal"] = 1

        exit_cond = data["Close"] < data["sma_50"]
        data.loc[exit_cond, "signal"] = -1

        data["stop_loss"] = data["Close"] - (self.atr_multiplier * data["atr"])
        data["take_profit"] = data["Close"] + (self.atr_multiplier * 2.5 * data["atr"])

        return data
