import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER = os.getenv("ALPACA_PAPER", "true").lower() in ("true", "1", "yes")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

DEFAULT_ACCOUNT_SIZE = float(os.getenv("DEFAULT_ACCOUNT_SIZE", "100000.00"))
DEFAULT_RISK_PER_TRADE = float(os.getenv("DEFAULT_RISK_PER_TRADE", "0.01"))

# Watchlist presets for scanner
PRESET_WATCHLISTS = {
    "tech": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "PLTR", "AVGO"],
    "growth_turnaround": ["TDOC", "BMNR", "PYPL", "SQ", "ROKU", "SOFI", "AFRM", "PATH", "COIN"],
    "crypto_proxies": ["BMNR", "COIN", "MSTR", "MARA", "RIOT", "CLSK", "BITF", "HUT"],
    "biotech_health": ["TDOC", "MRNA", "BNTX", "CRSP", "VRTX", "ILMN", "EXAS", "PACB"],
    "index_etfs": ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "SMH"],
}
