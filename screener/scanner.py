from dataclasses import dataclass
import pandas as pd
from core.indicators import attach_all_indicators
from data.fetcher import DataFetcher


@dataclass
class ScanResult:
    ticker: str
    price: float
    pct_change: float
    rsi: float
    in_squeeze: bool
    squeeze_fired: bool
    above_ema21: bool
    above_sma50: bool
    above_sma200: bool
    volume_surge: float
    macd_hist: float
    is_spring: bool
    status: str


class MarketScanner:
    """Multi-criteria technical scanner for volatility coils, breakouts, and springs."""

    def __init__(self, fetcher: DataFetcher | None = None):
        self.fetcher = fetcher or DataFetcher()

    def scan_ticker(self, ticker: str, period: str = "6mo") -> ScanResult | None:
        try:
            df = self.fetcher.get_history(ticker, period=period)
            if df.empty or len(df) < 30:
                return None

            data = attach_all_indicators(df)
            last = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else last

            # Wyckoff spring detection on last 3 bars
            prior_low = data["Low"].iloc[:-3].tail(20).min() if len(data) > 23 else data["Low"].min()
            recent_low = data["Low"].tail(3).min()
            is_spring = (recent_low < prior_low) and (last["Close"] > prior_low) and (last["vol_surge"] > 1.1)

            pct_change = ((last["Close"] - prev["Close"]) / prev["Close"]) * 100.0

            # Determine dominant status tag
            if bool(last.get("squeeze_fired", False)):
                status = "🔥 SQUEEZE FIRED"
            elif bool(last.get("in_squeeze", False)):
                status = "🌀 COILING (SQUEEZE ON)"
            elif is_spring:
                status = "🌱 WYCKOFF SPRING"
            elif float(last["vol_surge"]) > 2.0:
                status = "⚡ VOLUME SURGE"
            elif float(last["rsi"]) < 30:
                status = "❄️ OVERSOLD"
            elif float(last["rsi"]) > 70:
                status = "🔥 OVERBOUGHT"
            elif last["Close"] > last["ema_21"] and last["macd_hist"] > 0:
                status = "📈 BULLISH MOMENTUM"
            else:
                status = "⚖️ NEUTRAL / CHOP"

            return ScanResult(
                ticker=ticker.upper(),
                price=round(float(last["Close"]), 2),
                pct_change=round(float(pct_change), 2),
                rsi=round(float(last["rsi"]), 1),
                in_squeeze=bool(last.get("in_squeeze", False)),
                squeeze_fired=bool(last.get("squeeze_fired", False)),
                above_ema21=bool(last["Close"] > last["ema_21"]),
                above_sma50=bool(last["Close"] > last["sma_50"]),
                above_sma200=bool(last["Close"] > last["sma_200"]),
                volume_surge=round(float(last["vol_surge"]), 2),
                macd_hist=round(float(last["macd_hist"]), 3),
                is_spring=bool(is_spring),
                status=status,
            )
        except Exception:
            return None

    def scan_watchlist(self, tickers: list[str]) -> list[ScanResult]:
        results = []
        for t in tickers:
            res = self.scan_ticker(t)
            if res is not None:
                results.append(res)
        return results
