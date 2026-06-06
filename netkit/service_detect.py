"""Service & banner detection — grab banners from open ports."""

import asyncio
import socket

from netkit.output import console, print_open_ports, set_output_mode, is_json_mode, print_json
from netkit.utils import resolve_host, guess_service

SERVICE_PROBES: dict[int, bytes] = {
    21: b"",                    # FTP — just connect
    22: b"",                    # SSH — server sends banner
    23: b"",                    # Telnet
    25: b"",                    # SMTP
    80: b"GET / HTTP/1.0\r\nHost: healthcheck\r\n\r\n",
    110: b"",                   # POP3
    143: b"",                   # IMAP
    443: b"",                   # HTTPS — handled via SSL
    445: b"",                   # SMB
    587: b"",                   # SMTP submission
    993: b"",                   # IMAPS
    995: b"",                   # POP3S
    3306: b"",                  # MySQL
    5432: b"",                  # PostgreSQL
    6379: b"PING\r\n",          # Redis
    8080: b"GET / HTTP/1.0\r\nHost: healthcheck\r\n\r\n",
    8443: b"",                  # HTTPS-alt
    27017: b"",                 # MongoDB
}

TLS_PORTS = {443, 8443, 993, 995, 465, 636, 5986}


async def _grab_banner(host: str, port: int, timeout: float = 3.0) -> str | None:
    """Connect to a port and read the initial banner / response."""
    ip = resolve_host(host) or host
    probe = SERVICE_PROBES.get(port, b"")

    try:
        if port in TLS_PORTS:
            return await _grab_tls_banner(ip, port, timeout)

        loop = asyncio.get_event_loop()

        def _do_grab():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((ip, port))
                if probe:
                    s.send(probe)
                banner = b""
                try:
                    banner = s.recv(2048)
                except (socket.timeout, ConnectionError, OSError):
                    pass
                s.close()
                if banner:
                    # Clean up banner
                    text = banner.decode("utf-8", errors="replace")
                    return text.replace("\r\n", " | ").replace("\n", " | ").strip()
                return None
            except Exception:
                return None

        return await loop.run_in_executor(None, _do_grab)
    except Exception:
        return None


async def _grab_tls_banner(host: str, port: int, timeout: float = 3.0) -> str | None:
    """Grab banner from TLS-enabled services."""
    try:
        import ssl as ssl_mod

        loop = asyncio.get_event_loop()

        def _do_tls_grab():
            try:
                ctx = ssl_mod.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl_mod.CERT_NONE
                ctx.set_ciphers("ALL:@SECLEVEL=0")

                raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                raw.settimeout(timeout)
                s = ctx.wrap_socket(raw, server_hostname=host)
                s.connect((host, port))
                s.send(b"GET / HTTP/1.0\r\nHost: healthcheck\r\n\r\n")
                banner = b""
                try:
                    banner = s.recv(4096)
                except (socket.timeout, ConnectionError, OSError):
                    pass
                s.close()
                if banner:
                    text = banner.decode("utf-8", errors="replace")
                    return text.replace("\r\n", " | ").replace("\n", " | ").strip()
                return "[TLS connection established]"
            except Exception:
                return None

        return await loop.run_in_executor(None, _do_tls_grab)
    except Exception:
        return None


async def detect_services(
    host: str,
    ports: list[int],
    timeout: float = 3.0,
    output: str = "rich",
) -> list[dict]:
    """Probe a list of ports for service banners."""
    set_output_mode(output)
    results = []

    for port in ports:
        banner = await _grab_banner(host, port, timeout)
        if banner:
            results.append({
                "port": port,
                "protocol": "tcp",
                "state": "open",
                "service": guess_service(port),
                "banner": banner[:120],
            })

    if is_json_mode():
        print_json(results)
    else:
        if results:
            print_open_ports(host, results)
        else:
            console.print(f"[yellow]No banners detected on {host}[/]")

    return results


async def detect_services_multi(
    targets: list[str],
    ports: list[int],
    timeout: float = 3.0,
    output: str = "rich",
) -> list[dict]:
    """Probe multiple hosts for service banners."""
    all_results = []
    for host in targets:
        console.print(f"\n[bold]Probing[/] [cyan]{host}[/]")
        results = await detect_services(host, ports, timeout, output)
        all_results.extend(results)
    return all_results
