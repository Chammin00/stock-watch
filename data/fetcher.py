import logging
import warnings
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


class DataFetcher:
    """Robust market data fetcher with yfinance support."""

    @staticmethod
    def get_history(
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a ticker.
        Returns cleaned DataFrame with columns: [Open, High, Low, Close, Volume].
        """
        ticker = ticker.upper().strip()
        try:
            t = yf.Ticker(ticker)
            if start and end:
                df = t.history(start=start, end=end, interval=interval, auto_adjust=True)
            else:
                df = t.history(period=period, interval=interval, auto_adjust=True)

            if df.empty:
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            # Ensure columns are standard
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.dropna(inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_latest_quote(ticker: str) -> dict:
        """Fetch latest market snapshot for a ticker."""
        df = DataFetcher.get_history(ticker, period="5d", interval="1d")
        if df.empty:
            return {}
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else last_row

        change = last_row["Close"] - prev_row["Close"]
        pct_change = (change / prev_row["Close"]) * 100.0

        return {
            "ticker": ticker.upper(),
            "price": float(last_row["Close"]),
            "open": float(last_row["Open"]),
            "high": float(last_row["High"]),
            "low": float(last_row["Low"]),
            "volume": int(last_row["Volume"]),
            "change": round(float(change), 2),
            "pct_change": round(float(pct_change), 2),
            "date": str(df.index[-1].date()),
        }
