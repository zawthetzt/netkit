"""
netkit check — one command, full network report.

Usage:
    netkit check example.com
    netkit check 192.168.1.1 --quick
    netkit check example.com --deep
"""

import asyncio
import json
import socket
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console()


@dataclass
class CheckResult:
    """Result of a network check."""
    target: str
    ip: Optional[str] = None
    ping_ms: Optional[float] = None
    dns_records: dict = field(default_factory=dict)
    whois_info: dict = field(default_factory=dict)
    open_ports: list = field(default_factory=list)
    http_info: dict = field(default_factory=dict)
    ssl_info: dict = field(default_factory=dict)
    traceroute: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    health: str = "unknown"  # healthy, degraded, down, unknown


async def check_ping(host: str) -> Optional[float]:
    """Ping a host and return latency in ms."""
    import subprocess
    try:
        # Resolve hostname first
        ip = socket.gethostbyname(host)
        result = await asyncio.to_thread(
            subprocess.run,
            ["ping", "-c", "1", "-W", "2", ip],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse: time=12.3 ms
            import re
            match = re.search(r'time=(\d+\.?\d*)', result.stdout)
            if match:
                return float(match.group(1))
    except:
        pass
    return None


async def check_dns(host: str) -> dict:
    """Get DNS records for a host."""
    records = {}

    try:
        # A record
        ip = socket.gethostbyname(host)
        records["A"] = [ip]
    except:
        records["A"] = []

    try:
        # Get all addresses
        results = socket.getaddrinfo(host, None)
        ips = list(set(r[4][0] for r in results))
        if "A" in records:
            records["AAAA"] = [ip for ip in ips if ":" in ip]
    except:
        pass

    return records


async def check_ports(host: str, ports: list[int] = None) -> list[dict]:
    """Check if common ports are open."""
    if ports is None:
        ports = [22, 80, 443, 8080, 8443]

    open_ports = []
    ip = socket.gethostbyname(host)

    for port in ports:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=1.0
            )
            writer.close()
            await writer.wait_closed()

            # Try to get service name
            try:
                service = socket.getservbyport(port)
            except:
                service = "unknown"

            open_ports.append({
                "port": port,
                "state": "open",
                "service": service,
            })
        except:
            pass

    return open_ports


async def check_http(url: str) -> dict:
    """Check HTTP response."""
    info = {}

    if not url.startswith("http"):
        url = f"https://{url}"

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, verify=False) as client:
            start = time.monotonic()
            response = await client.get(url)
            elapsed = (time.monotonic() - start) * 1000

            info["status"] = response.status_code
            info["response_ms"] = round(elapsed, 1)
            info["server"] = response.headers.get("server", "")
            info["content_type"] = response.headers.get("content-type", "")

            # Extract title
            if "text/html" in info.get("content_type", ""):
                import re
                match = re.search(r'<title>(.*?)</title>', response.text[:5000], re.IGNORECASE)
                if match:
                    info["title"] = match.group(1).strip()

    except Exception as e:
        info["error"] = str(e)

    return info


async def check_ssl(host: str) -> dict:
    """Check SSL certificate."""
    import ssl

    info = {}

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(5)
            s.connect((host, 443))
            cert = s.getpeercert()

            if cert:
                info["issuer"] = dict(x[0] for x in cert.get("issuer", []))
                info["subject"] = dict(x[0] for x in cert.get("subject", []))
                info["not_before"] = cert.get("notBefore", "")
                info["not_after"] = cert.get("notAfter", "")
                info["serial"] = cert.get("serialNumber", "")
    except:
        pass

    return info


async def check_traceroute(host: str) -> list[dict]:
    """Run traceroute to host."""
    import subprocess

    hops = []

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            ["traceroute", "-n", "-m", "15", "-w", "2", host],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    hop_num = parts[0]
                    hop_ip = parts[1] if parts[1] != "*" else None
                    hop_ms = parts[2] if len(parts) > 2 and parts[2] != "*" else None

                    hops.append({
                        "hop": int(hop_num),
                        "ip": hop_ip,
                        "ms": float(hop_ms) if hop_ms else None,
                    })
    except:
        pass

    return hops


async def run_check(target: str, quick: bool = False, deep: bool = False) -> CheckResult:
    """Run a comprehensive check on a target."""
    result = CheckResult(target=target)

    # Resolve IP
    try:
        result.ip = socket.gethostbyname(target)
    except:
        result.ip = None
        result.errors.append("Could not resolve hostname")
        result.health = "down"
        return result

    # Ping
    result.ping_ms = await check_ping(target)
    if result.ping_ms is not None:
        result.health = "healthy"

    # DNS
    if not quick:
        result.dns_records = await check_dns(target)

    # Ports
    result.open_ports = await check_ports(target)

    # HTTP & SSL (only for web targets)
    if not quick:
        # Check if port 80 or 443 is open
        port_nums = [p["port"] for p in result.open_ports]
        if 80 in port_nums or 443 in port_nums:
            result.http_info = await check_http(target)
            result.ssl_info = await check_ssl(target)

    # WHOIS (skip for now, requires python-whois)
    # if not quick:
    #     result.whois_info = await check_whois(target)

    # Traceroute (deep only)
    if deep:
        result.traceroute = await check_traceroute(target)

    # Determine health
    if result.ping_ms is None:
        result.health = "down"
    elif result.ping_ms > 100:
        result.health = "degraded"

    return result


def display_result(result: CheckResult, output_json: bool = False):
    """Display check result."""
    if output_json:
        print(json.dumps(asdict(result), indent=2, default=str))
        return

    # Health emoji
    health_emoji = {
        "healthy": "✅",
        "degraded": "⚠️",
        "down": "❌",
        "unknown": "❓",
    }

    # Build tree
    tree = Tree(f"[bold]🔍 netkit check — {result.target}[/]")

    # Connectivity
    conn = tree.add("[bold cyan]📡 Connectivity[/]")
    if result.ping_ms:
        conn.add(f"Ping: {result.ping_ms:.1f}ms {health_emoji.get(result.health, '')}")
    else:
        conn.add(f"Ping: [red]Failed[/] {health_emoji.get(result.health, '')}")
    if result.ip:
        conn.add(f"IP: {result.ip}")

    # DNS
    if result.dns_records:
        dns = tree.add("[bold cyan]🌐 DNS Records[/]")
        for rtype, values in result.dns_records.items():
            for val in values:
                dns.add(f"{rtype}: {val}")

    # Ports
    if result.open_ports:
        ports = tree.add("[bold cyan]🔓 Open Ports[/]")
        for p in result.open_ports:
            ports.add(f"{p['port']}/tcp  [green]{p['state']}[/]  {p['service']}")
    else:
        ports = tree.add("[bold cyan]🔓 Ports[/]")
        ports.add("[dim]No common ports open[/]")

    # HTTP
    if result.http_info:
        http = tree.add("[bold cyan]🖥️ HTTP Response[/]")
        if "status" in result.http_info:
            status_color = "green" if result.http_info["status"] == 200 else "yellow"
            http.add(f"Status: [{status_color}]{result.http_info['status']}[/]")
        if "response_ms" in result.http_info:
            http.add(f"Response: {result.http_info['response_ms']}ms")
        if "server" in result.http_info:
            http.add(f"Server: {result.http_info['server']}")
        if "title" in result.http_info:
            http.add(f"Title: \"{result.http_info['title']}\"")

    # SSL
    if result.ssl_info and "issuer" in result.ssl_info:
        ssl = tree.add("[bold cyan]🔒 SSL Certificate[/]")
        issuer = result.ssl_info.get("issuer", {})
        ssl.add(f"Issuer: {issuer.get('organizationName', 'Unknown')}")
        if "not_after" in result.ssl_info:
            ssl.add(f"Expires: {result.ssl_info['not_after']}")

    # Summary
    health_color = {"healthy": "green", "degraded": "yellow", "down": "red"}.get(result.health, "white")
    summary = tree.add(f"[bold]📊 Summary[/]")
    summary.add(f"Health: [{health_color}]{health_emoji.get(result.health, '')} {result.health.upper()}[/]")
    if result.ping_ms:
        summary.add(f"Response: {result.ping_ms:.1f}ms")

    console.print(tree)


async def check_async(target: str, quick: bool = False, deep: bool = False) -> dict:
    """Async wrapper for check."""
    result = await run_check(target, quick, deep)
    return asdict(result)
