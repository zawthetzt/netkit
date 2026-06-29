"""Local ports scanner — show all open/listening ports on this machine."""

import asyncio
import json
import socket
import subprocess
from dataclasses import dataclass, asdict
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


console = Console()


@dataclass
class ListeningPort:
    port: int
    protocol: str
    state: str
    address: str
    process: str
    pid: Optional[int] = None


def get_listening_ports(process_filter: Optional[str] = None, port_filter: Optional[int] = None) -> list[ListeningPort]:
    """Get all listening ports on the local machine."""
    ports = []

    try:
        # Try ss first (modern Linux)
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return _parse_ss_output(result.stdout, process_filter, port_filter)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        # Fallback to netstat
        result = subprocess.run(
            ["netstat", "-tlnp"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return _parse_netstat_output(result.stdout, process_filter, port_filter)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: scan common ports with sockets
    return _scan_common_ports(process_filter, port_filter)


def _parse_ss_output(output: str, process_filter: Optional[str], port_filter: Optional[int]) -> list[ListeningPort]:
    """Parse ss -tlnp output."""
    ports = []
    for line in output.strip().split("\n")[1:]:  # Skip header
        parts = line.split()
        if len(parts) < 4:
            continue

        state = parts[0]
        if "LISTEN" not in state:
            continue

        local_addr = parts[3]
        # Extract port (last : after bracket handling for IPv6)
        if "[" in local_addr:  # IPv6
            addr_part = local_addr.rsplit(":", 1)
        else:
            addr_part = local_addr.rsplit(":", 1)

        if len(addr_part) != 2:
            continue

        addr = addr_part[0]
        try:
            port = int(addr_part[1])
        except ValueError:
            continue

        # Extract process info
        process = "unknown"
        pid = None
        for part in parts:
            if "pid=" in part:
                try:
                    pid = int(part.split("pid=")[1].split(",")[0])
                except (ValueError, IndexError):
                    pass
            if "users:" in part:
                try:
                    process = part.split('"')[1]
                except (IndexError, ValueError):
                    pass

        # Apply filters
        if process_filter and process_filter.lower() not in process.lower():
            continue
        if port_filter and port != port_filter:
            continue

        ports.append(ListeningPort(
            port=port,
            protocol="TCP",
            state="LISTEN",
            address=addr,
            process=process,
            pid=pid
        ))

    return sorted(ports, key=lambda p: p.port)


def _parse_netstat_output(output: str, process_filter: Optional[str], port_filter: Optional[int]) -> list[ListeningPort]:
    """Parse netstat -tlnp output."""
    ports = []
    for line in output.strip().split("\n")[2:]:  # Skip header
        parts = line.split()
        if len(parts) < 6:
            continue

        proto = parts[0]
        state = parts[5] if len(parts) > 5 else ""
        if "LISTEN" not in state:
            continue

        local_addr = parts[3]
        addr_part = local_addr.rsplit(":", 1)
        if len(addr_part) != 2:
            continue

        addr = addr_part[0] if addr_part[0] else "0.0.0.0"
        try:
            port = int(addr_part[1])
        except ValueError:
            continue

        # Process info
        process_info = parts[-1] if "/" in parts[-1] else "unknown"
        process = process_info.split("/")[-1] if "/" in process_info else "unknown"
        try:
            pid = int(process_info.split("/")[0]) if "/" in process_info else None
        except ValueError:
            pid = None

        if process_filter and process_filter.lower() not in process.lower():
            continue
        if port_filter and port != port_filter:
            continue

        ports.append(ListeningPort(
            port=port,
            protocol=proto.upper(),
            state="LISTEN",
            address=addr,
            process=process,
            pid=pid
        ))

    return sorted(ports, key=lambda p: p.port)


def _scan_common_ports(process_filter: Optional[str], port_filter: Optional[int]) -> list[ListeningPort]:
    """Fallback: scan common ports with sockets."""
    common_ports = [21, 22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995,
                    3306, 3389, 5432, 6379, 8080, 8443, 9090, 27017]
    ports = []

    for port in common_ports:
        if port_filter and port != port_filter:
            continue

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex(("127.0.0.1", port))
            if result == 0:
                ports.append(ListeningPort(
                    port=port,
                    protocol="TCP",
                    state="LISTEN",
                    address="0.0.0.0",
                    process="unknown"
                ))
            sock.close()
        except:
            pass

    return sorted(ports, key=lambda p: p.port)


def display_ports(ports: list[ListeningPort], output_json: bool = False):
    """Display listening ports in a table or JSON."""
    if output_json:
        print(json.dumps([asdict(p) for p in ports], indent=2))
        return

    if not ports:
        console.print("[yellow]No listening ports found.[/yellow]")
        return

    hostname = socket.gethostname()
    table = Table(title=f"🖥️  Local Open Ports — {hostname}")
    table.add_column("PORT", style="cyan", justify="right")
    table.add_column("PROTO", style="green")
    table.add_column("STATE", style="yellow")
    table.add_column("ADDRESS", style="blue")
    table.add_column("PROCESS", style="magenta")
    table.add_column("PID", style="dim")

    for p in ports:
        table.add_row(
            str(p.port),
            p.protocol,
            p.state,
            p.address,
            p.process,
            str(p.pid) if p.pid else "-"
        )

    console.print(table)
    console.print(f"\n[bold]Total: {len(ports)} open ports[/bold]")


async def local_async(process: Optional[str] = None, port: Optional[int] = None) -> list[dict]:
    """Async wrapper for local ports scan."""
    ports = await asyncio.to_thread(get_listening_ports, process, port)
    return [asdict(p) for p in ports]
