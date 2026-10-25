import json
import logging
import requests
from rich.console import Console
from rich.table import Table
from config import DISCORD_WEBHOOK_URL
from screener.scanner import ScanResult

logger = logging.getLogger(__name__)
console = Console(force_terminal=True, legacy_windows=False)


def display_scan_results(results: list[ScanResult], title: str = "Market Scanner Results"):
    """Render scan results in a rich colored terminal table."""
    table = Table(title=f"📊 {title}", header_style="bold cyan", border_style="bright_blue")

    table.add_column("Ticker", style="bold white", justify="left")
    table.add_column("Price", justify="right")
    table.add_column("Change %", justify="right")
    table.add_column("RSI (14)", justify="right")
    table.add_column("Coiling?", justify="center")
    table.add_column("> 21 EMA", justify="center")
    table.add_column("> 50 SMA", justify="center")
    table.add_column("> 200 SMA", justify="center")
    table.add_column("Vol Surge", justify="right")
    table.add_column("Setup Signal", style="bold", justify="left")

    for r in results:
        chg_style = "green" if r.pct_change >= 0 else "red"
        chg_text = f"[{chg_style}]{r.pct_change:+.2f}%[/{chg_style}]"

        rsi_style = "red" if r.rsi >= 70 else ("green" if r.rsi <= 35 else "yellow")
        rsi_text = f"[{rsi_style}]{r.rsi:.1f}[/{rsi_style}]"

        squeeze_text = "[bold yellow]YES (Coiling)[/bold yellow]" if r.in_squeeze else (
            "[bold green]FIRED 🚀[/bold green]" if r.squeeze_fired else "[dim]No[/dim]"
        )

        ema_text = "[green]✓[/green]" if r.above_ema21 else "[red]✗[/red]"
        sma50_text = "[green]✓[/green]" if r.above_sma50 else "[red]✗[/red]"
        sma200_text = "[green]✓[/green]" if r.above_sma200 else "[red]✗[/red]"

        vol_style = "bold magenta" if r.volume_surge >= 2.0 else ("cyan" if r.volume_surge >= 1.2 else "dim")
        vol_text = f"[{vol_style}]{r.volume_surge:.2f}x[/{vol_style}]"

        table.add_row(
            r.ticker,
            f"${r.price:.2f}",
            chg_text,
            rsi_text,
            squeeze_text,
            ema_text,
            sma50_text,
            sma200_text,
            vol_text,
            r.status,
        )

    console.print(table)


def send_discord_alert(message: str, webhook_url: str | None = None) -> bool:
    """Send formatted alert to Discord webhook if configured."""
    url = webhook_url or DISCORD_WEBHOOK_URL
    if not url:
        return False

    payload = {"content": message}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.error(f"Failed to dispatch webhook alert: {e}")
        return False
