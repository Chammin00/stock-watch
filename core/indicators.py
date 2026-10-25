import numpy as np
import pandas as pd


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder's Smoothing."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).astype(float)
    loss = (-delta.where(delta < 0, 0)).astype(float)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Moving Average Convergence Divergence."""
    fast_ema = calculate_ema(series, fast)
    slow_ema = calculate_ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (ATR)."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return atr


def calculate_bollinger_bands(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands: Upper, Middle (SMA), Lower, BandWidth."""
    mid = calculate_sma(series, period)
    std = series.rolling(window=period).std()
    upper = mid + (std * num_std)
    lower = mid - (std * num_std)
    bandwidth = (upper - lower) / (mid + 1e-9)
    return upper, mid, lower, bandwidth


def calculate_keltner_channels(
    df: pd.DataFrame, period: int = 20, multiplier: float = 1.5, atr_period: int = 10
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Keltner Channels: Upper, Middle (EMA), Lower."""
    mid = calculate_ema(df["Close"], period)
    atr = calculate_atr(df, atr_period)
    upper = mid + (multiplier * atr)
    lower = mid - (multiplier * atr)
    return upper, mid, lower


def detect_volatility_squeeze(
    df: pd.DataFrame,
    bb_period: int = 20,
    bb_std: float = 2.0,
    kc_period: int = 20,
    kc_mult: float = 1.5,
) -> pd.DataFrame:
    """
    Detects John Carter's Volatility Squeeze (Bollinger Bands inside Keltner Channels).
    When BB Upper < KC Upper and BB Lower > KC Lower, the market is coiled in a squeeze.
    """
    df = df.copy()
    bb_upper, bb_mid, bb_lower, bb_width = calculate_bollinger_bands(df["Close"], bb_period, bb_std)
    kc_upper, kc_mid, kc_lower = calculate_keltner_channels(df, kc_period, kc_mult)

    # In Squeeze: Bollinger Bands are completely inside Keltner Channels
    df["in_squeeze"] = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    df["squeeze_fired"] = (~df["in_squeeze"]) & (df["in_squeeze"].shift(1) == True)
    df["bb_width"] = bb_width
    df["bb_upper"] = bb_upper
    df["bb_lower"] = bb_lower
    df["bb_mid"] = bb_mid
    df["kc_upper"] = kc_upper
    df["kc_lower"] = kc_lower

    return df


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price (Cumulative for given session/window)."""
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    cum_vol_price = (typical_price * df["Volume"]).cumsum()
    cum_vol = df["Volume"].cumsum()
    return cum_vol_price / (cum_vol + 1e-9)


def attach_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich dataframe with full suite of technical indicators."""
    df = df.copy()
    df["sma_20"] = calculate_sma(df["Close"], 20)
    df["sma_50"] = calculate_sma(df["Close"], 50)
    df["sma_200"] = calculate_sma(df["Close"], 200)

    df["ema_9"] = calculate_ema(df["Close"], 9)
    df["ema_21"] = calculate_ema(df["Close"], 21)

    df["rsi"] = calculate_rsi(df["Close"], 14)
    df["macd"], df["macd_signal"], df["macd_hist"] = calculate_macd(df["Close"])
    df["atr"] = calculate_atr(df, 14)

    # Volatility Squeeze
    df = detect_volatility_squeeze(df)

    # Volume dynamics
    df["vol_sma20"] = calculate_sma(df["Volume"], 20)
    df["vol_surge"] = df["Volume"] / (df["vol_sma20"] + 1e-9)

    return df
