"""Down detector — check if websites/services are up or down."""

import asyncio
import json
import time
from dataclasses import dataclass, asdict
from typing import Optional

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


# Popular services to check
POPULAR_SERVICES = {
    "google": "https://www.google.com",
    "github": "https://github.com",
    "cloudflare": "https://www.cloudflare.com",
    "aws": "https://aws.amazon.com",
    "azure": "https://azure.microsoft.com",
    "gcp": "https://cloud.google.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://twitter.com",
    "instagram": "https://www.instagram.com",
    "youtube": "https://www.youtube.com",
    "netflix": "https://www.netflix.com",
    "discord": "https://discord.com",
    "slack": "https://slack.com",
    "spotify": "https://www.spotify.com",
    "reddit": "https://www.reddit.com",
    "amazon": "https://www.amazon.com",
    "microsoft": "https://www.microsoft.com",
    "apple": "https://www.apple.com",
    "cloudflare-dns": "https://1.1.1.1",
    "google-dns": "https://8.8.8.8",
}


@dataclass
class ServiceStatus:
    name: str
    url: str
    status_code: Optional[int]
    response_ms: Optional[float]
    is_up: bool
    error: Optional[str] = None


async def check_service(client: httpx.AsyncClient, name: str, url: str) -> ServiceStatus:
    """Check if a single service is up."""
    try:
        start = time.monotonic()
        response = await client.get(url, follow_redirects=True, timeout=10)
        elapsed = (time.monotonic() - start) * 1000

        return ServiceStatus(
            name=name,
            url=url,
            status_code=response.status_code,
            response_ms=round(elapsed, 1),
            is_up=200 <= response.status_code < 500
        )
    except httpx.TimeoutException:
        return ServiceStatus(
            name=name, url=url, status_code=None,
            response_ms=None, is_up=False, error="Timeout"
        )
    except httpx.ConnectError:
        return ServiceStatus(
            name=name, url=url, status_code=None,
            response_ms=None, is_up=False, error="Connection refused"
        )
    except Exception as e:
        return ServiceStatus(
            name=name, url=url, status_code=None,
            response_ms=None, is_up=False, error=str(e)[:50]
        )


async def check_services(targets: Optional[list[str]] = None) -> list[ServiceStatus]:
    """Check status of multiple services."""
    if targets is None:
        # Check popular services
        services = POPULAR_SERVICES
    else:
        # Parse custom targets
        services = {}
        for t in targets:
            if t.lower() in POPULAR_SERVICES:
                services[t.lower()] = POPULAR_SERVICES[t.lower()]
            elif t.startswith("http"):
                # Use domain as name
                name = t.split("//")[1].split("/")[0].replace("www.", "")
                services[name] = t
            else:
                services[t] = f"https://{t}"

    async with httpx.AsyncClient(
        timeout=15,
        headers={"User-Agent": "netkit/0.1 (down-detector)"},
        verify=False
    ) as client:
        tasks = [check_service(client, name, url) for name, url in services.items()]
        results = await asyncio.gather(*tasks)

    return sorted(results, key=lambda r: (not r.is_up, r.name))


def display_results(results: list[ServiceStatus], output_json: bool = False):
    """Display service status results."""
    if output_json:
        print(json.dumps([asdict(r) for r in results], indent=2))
        return

    up_count = sum(1 for r in results if r.is_up)
    down_count = len(results) - up_count

    table = Table(title="🔍 Service Status — Down Detector")
    table.add_column("SERVICE", style="cyan", min_width=15)
    table.add_column("STATUS", justify="center", min_width=10)
    table.add_column("CODE", justify="center", min_width=6)
    table.add_column("RESPONSE", justify="right", min_width=10)
    table.add_column("URL", style="dim")

    for r in results:
        if r.is_up:
            status = "[green]✅ UP[/green]"
            code = str(r.status_code) if r.status_code else "-"
            response = f"{r.response_ms:.0f}ms" if r.response_ms else "-"
        else:
            status = "[red]❌ DOWN[/red]"
            code = str(r.status_code) if r.status_code else "-"
            response = r.error if r.error else "-"

        table.add_row(r.name, status, code, response, r.url)

    console.print(table)

    # Summary
    summary = Panel(
        f"[green]✅ Up: {up_count}[/green]  |  [red]❌ Down: {down_count}[/red]  |  Total: {len(results)}",
        border_style="green" if down_count == 0 else "red"
    )
    console.print(summary)


async def downdetector_async(targets: Optional[list[str]] = None) -> list[dict]:
    """Async wrapper for down detector."""
    results = await check_services(targets)
    return [asdict(r) for r in results]
