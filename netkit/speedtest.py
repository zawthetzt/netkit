"""Network speed test — measure download and upload speeds."""

import asyncio
import json
import time
import httpx
from dataclasses import dataclass, asdict

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.live import Live
from rich.table import Table

console = Console()

# Speed test servers (public CDN files for testing)
DOWNLOAD_URLS = [
    "https://speed.cloudflare.com/__down?bytes=25000000",  # 25MB
    "https://proof.ovh.net/files/10Mb.dat",
    "https://speed.hetzner.de/10MB.bin",
]

UPLOAD_URL = "https://speed.cloudflare.com/__up"


@dataclass
class SpeedResult:
    download_mbps: float
    upload_mbps: float
    ping_ms: float
    server: str
    timestamp: str


async def measure_ping(host: str = "1.1.1.1") -> float:
    """Measure ping latency to a host."""
    import subprocess
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["ping", "-c", "3", "-W", "2", host],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Parse avg ping from output
            for line in result.stdout.split("\n"):
                if "avg" in line:
                    # Format: rtt min/avg/max/mdev = 1.234/2.345/3.456/0.123 ms
                    parts = line.split("=")[-1].strip().split("/")
                    if len(parts) >= 2:
                        return float(parts[1])
    except:
        pass
    return -1.0


async def measure_download(url: str, timeout: float = 30.0) -> float:
    """Measure download speed in Mbps."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            start = time.monotonic()
            total_bytes = 0

            async with client.stream("GET", url) as response:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    total_bytes += len(chunk)

            elapsed = time.monotonic() - start
            if elapsed > 0:
                # Convert bytes/sec to Mbps
                mbps = (total_bytes * 8) / (elapsed * 1_000_000)
                return round(mbps, 2)
    except:
        pass
    return 0.0


async def measure_upload(size_bytes: int = 5_000_000, timeout: float = 30.0) -> float:
    """Measure upload speed in Mbps."""
    try:
        data = b"0" * size_bytes
        async with httpx.AsyncClient(timeout=timeout) as client:
            start = time.monotonic()
            await client.post(UPLOAD_URL, content=data)
            elapsed = time.monotonic() - start

            if elapsed > 0:
                mbps = (size_bytes * 8) / (elapsed * 1_000_000)
                return round(mbps, 2)
    except:
        pass
    return 0.0


async def run_speedtest() -> SpeedResult:
    """Run a complete speed test."""
    from datetime import datetime

    # Measure ping
    console.print("[dim]Measuring ping...[/dim]")
    ping = await measure_ping()

    # Measure download
    console.print("[dim]Testing download speed...[/dim]")
    download_speed = 0.0
    for url in DOWNLOAD_URLS:
        speed = await measure_download(url)
        if speed > 0:
            download_speed = speed
            break

    # Measure upload
    console.print("[dim]Testing upload speed...[/dim]")
    upload_speed = await measure_upload()

    return SpeedResult(
        download_mbps=download_speed,
        upload_mbps=upload_speed,
        ping_ms=ping,
        server="Cloudflare",
        timestamp=datetime.now().isoformat()
    )


def display_result(result: SpeedResult, output_json: bool = False):
    """Display speed test results."""
    if output_json:
        print(json.dumps(asdict(result), indent=2))
        return

    # Speed rating
    def rate_speed(mbps: float) -> str:
        if mbps >= 100:
            return "[green]Excellent[/green]"
        elif mbps >= 50:
            return "[green]Good[/green]"
        elif mbps >= 25:
            return "[yellow]Fair[/yellow]"
        elif mbps >= 10:
            return "[yellow]Basic[/yellow]"
        else:
            return "[red]Slow[/red]"

    def rate_ping(ms: float) -> str:
        if ms < 10:
            return "[green]Excellent[/green]"
        elif ms < 30:
            return "[green]Good[/green]"
        elif ms < 100:
            return "[yellow]Fair[/yellow]"
        else:
            return "[red]High[/red]"

    panel = Panel(
        f"""[bold cyan]Download:[/bold cyan]  {result.download_mbps:>8.2f} Mbps  {rate_speed(result.download_mbps)}
[bold cyan]Upload:[/bold cyan]    {result.upload_mbps:>8.2f} Mbps  {rate_speed(result.upload_mbps)}
[bold cyan]Ping:[/bold cyan]      {result.ping_ms:>8.1f} ms    {rate_ping(result.ping_ms)}

[dim]Server: {result.server}[/dim]
[dim]Time: {result.timestamp}[/dim]""",
        title="🚀 Speed Test Results",
        border_style="cyan"
    )
    console.print(panel)


async def speedtest_async() -> dict:
    """Async wrapper for speed test."""
    result = await run_speedtest()
    return asdict(result)
