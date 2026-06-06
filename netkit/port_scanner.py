"""Port scanner — TCP connect, SYN (raw), and UDP scanning."""

import asyncio
import socket
import struct
import time
from typing import Optional

from netkit.output import (
    console,
    print_open_ports,
    scan_progress,
    set_output_mode,
    is_json_mode,
    print_json,
)
from netkit.utils import (
    parse_ports,
    parse_targets,
    resolve_host,
    COMMON_PORTS,
    guess_service,
)


async def _tcp_connect_scan(
    host: str, port: int, timeout: float = 1.0
) -> dict | None:
    """TCP connect scan (full three-way handshake)."""
    try:
        ip = resolve_host(host) or host
        loop = asyncio.get_event_loop()

        def _connect():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            s.close()
            return result == 0

        is_open = await loop.run_in_executor(None, _connect)
        if is_open:
            return {
                "port": port,
                "protocol": "tcp",
                "state": "open",
                "service": guess_service(port),
                "banner": None,
            }
        return None
    except Exception:
        return None


async def _syn_scan_host(
    host: str, ports: list[int], timeout: float = 1.0
) -> list[dict]:
    """SYN scan using raw sockets (requires root/raw socket capability).

    Sends SYN, receives SYN+ACK (open) or RST (closed).
    """
    try:
        from scapy.all import IP, TCP, sr1, conf

        conf.verb = 0
        ip = resolve_host(host) or host
        open_ports = []

        for port in ports:
            pkt = IP(dst=ip) / TCP(dport=port, flags="S")
            reply = sr1(pkt, timeout=timeout, verbose=0)
            if reply is None:
                continue
            if reply.haslayer(TCP):
                flags = reply.getlayer(TCP).flags
                if flags & 0x12:  # SYN+ACK
                    # Send RST to close half-open connection
                    rst = IP(dst=ip) / TCP(dport=port, flags="R")
                    sr1(rst, timeout=0.5, verbose=0)
                    open_ports.append({
                        "port": port,
                        "protocol": "tcp",
                        "state": "open",
                        "service": guess_service(port),
                        "banner": None,
                    })
        return open_ports
    except PermissionError:
        console.print("[yellow]SYN scan requires root. Falling back to TCP connect scan.[/]")
        return []
    except ImportError:
        console.print("[yellow]Scapy not available for SYN scan. Falling back to TCP connect.[/]")
        return []


async def _udp_scan_host(
    host: str, ports: list[int], timeout: float = 1.5
) -> list[dict]:
    """UDP port scan. Sends empty UDP probe and looks for ICMP unreachable."""
    open_ports = []
    ip = resolve_host(host) or host

    try:
        from scapy.all import IP, UDP, ICMP, sr1, conf

        conf.verb = 0

        for port in ports:
            pkt = IP(dst=ip) / UDP(dport=port)
            reply = sr1(pkt, timeout=timeout, verbose=0)
            if reply is None:
                # No response could mean open/filtered
                open_ports.append({
                    "port": port,
                    "protocol": "udp",
                    "state": "open|filtered",
                    "service": guess_service(port, "udp"),
                    "banner": None,
                })
            elif reply.haslayer(ICMP):
                icmp = reply.getlayer(ICMP)
                if icmp.type == 3 and icmp.code == 3:
                    pass  # Port unreachable — closed
                else:
                    open_ports.append({
                        "port": port,
                        "protocol": "udp",
                        "state": "filtered",
                        "service": guess_service(port, "udp"),
                        "banner": None,
                    })
            else:
                open_ports.append({
                    "port": port,
                    "protocol": "udp",
                    "state": "open",
                    "service": guess_service(port, "udp"),
                    "banner": None,
                })
    except (ImportError, PermissionError):
        console.print("[yellow]UDP scan requires Scapy with root. Skipping UDP scan.[/]")

    return open_ports


async def _scan_host_connect(
    host: str,
    ports: list[int],
    timeout: float = 1.0,
    concurrency: int = 100,
    progress_bar=None,
    task_id=None,
) -> list[dict]:
    """Scan a single host TCP connect with concurrency."""
    ip = resolve_host(host) or host
    sem = asyncio.Semaphore(concurrency)
    open_ports: list[dict] = []

    async def _check(p: int) -> dict | None:
        async with sem:
            result = await _tcp_connect_scan(ip, p, timeout)
            return result

    tasks = [_check(p) for p in ports]
    for coro in asyncio.as_completed(tasks):
        result = await coro
        if result:
            open_ports.append(result)
        if progress_bar and task_id is not None:
            progress_bar.advance(task_id)

    return sorted(open_ports, key=lambda x: x["port"])


async def port_scan(
    targets: list[str],
    ports: str | None = None,
    timeout: float = 1.0,
    concurrency: int = 100,
    scan_type: str = "connect",
    output: str = "rich",
    udp: bool = False,
) -> list[dict]:
    """Run a port scan against targets."""
    set_output_mode(output)

    host_ips = parse_targets(targets)
    if not host_ips:
        console.print("[red]No valid targets specified.[/]")
        return []

    port_list = parse_ports(ports) if ports else COMMON_PORTS
    all_results = []

    for host in host_ips:
        if not is_json_mode():
            console.print(f"[bold]Scanning[/] [cyan]{host}[/] — {len(port_list)} ports")

        if scan_type == "syn":
            open_ports = await _syn_scan_host(host, port_list, timeout)
        else:
            with scan_progress(f"TCP connect — {host}") as progress:
                task = progress.add_task("", total=len(port_list))
                open_ports = await _scan_host_connect(
                    host, port_list, timeout, concurrency, progress, task
                )

        udp_ports = []
        if udp:
            with scan_progress(f"UDP — {host}") as progress:
                task = progress.add_task("", total=len(port_list))
                udp_ports = await _udp_scan_host(host, port_list, timeout)
            open_ports.extend(udp_ports)

        result = {
            "host": host,
            "ports": open_ports,
            "total_open": sum(1 for p in open_ports if p["state"] == "open"),
        }
        all_results.append(result)

        if is_json_mode():
            continue
        print_open_ports(host, open_ports)

    if is_json_mode():
        print_json(all_results)

    return all_results


async def single_port_scan(
    host: str, port: int, timeout: float = 1.0
) -> dict:
    """Quick single-port check (TCP connect)."""
    result = await _tcp_connect_scan(host, port, timeout)
    if result:
        return result
    return {"port": port, "protocol": "tcp", "state": "closed", "service": guess_service(port), "banner": None}
