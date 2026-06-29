"""iftop-style network traffic monitor — live bandwidth per connection."""

import asyncio
import json
import os
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


@dataclass
class Connection:
    """Represents a network connection with traffic stats."""
    local_addr: str
    local_port: int
    remote_addr: str
    remote_port: int
    protocol: str
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class TrafficStats:
    """Traffic statistics for a connection."""
    connection: str  # "local -> remote"
    rate_up: float = 0.0      # bytes/sec
    rate_down: float = 0.0    # bytes/sec
    total_up: int = 0
    total_down: int = 0
    peak_up: float = 0.0
    peak_down: float = 0.0


def format_bytes(bytes_val: float) -> str:
    """Format bytes to human readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def format_rate(bytes_per_sec: float) -> str:
    """Format bytes/sec to human readable rate."""
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    elif bytes_per_sec < 1024 * 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024 * 1024):.1f} GB/s"


class IftopMonitor:
    """Interactive network traffic monitor."""

    def __init__(self, interface: Optional[str] = None):
        self.interface = interface
        self.connections: dict[str, TrafficStats] = {}
        self.running = False
        self._prev_stats: dict[str, tuple[int, int, float]] = {}

    def _get_connections(self) -> list[dict]:
        """Get current network connections using ss."""
        try:
            cmd = ["ss", "-tunp"]
            if self.interface:
                cmd.extend(["-i", self.interface])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return self._parse_ss_output(result.stdout)
        except:
            pass
        return []

    def _parse_ss_output(self, output: str) -> list[dict]:
        """Parse ss output to extract connections."""
        connections = []
        for line in output.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue

            proto = parts[0].lower()
            state = parts[1]

            # Only interested in established connections
            if state not in ("ESTAB", "ESTABLISHED"):
                continue

            local = parts[3] if len(parts) > 3 else ""
            remote = parts[4] if len(parts) > 4 else ""

            # Parse addresses
            local_parts = local.rsplit(":", 1)
            remote_parts = remote.rsplit(":", 1)

            if len(local_parts) == 2 and len(remote_parts) == 2:
                connections.append({
                    "proto": proto,
                    "local_addr": local_parts[0],
                    "local_port": local_parts[1],
                    "remote_addr": remote_parts[0],
                    "remote_port": remote_parts[1],
                })

        return connections

    def _get_traffic_stats(self) -> dict[str, tuple[int, int]]:
        """Get traffic statistics per connection from /proc/net/tcp or netstat."""
        stats = {}
        try:
            # Read /proc/net/tcp for byte counts (simplified)
            result = subprocess.run(
                ["cat", "/proc/net/tcp"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                for line in result.strip().split("\n")[1:]:
                    parts = line.split()
                    if len(parts) >= 10:
                        local = parts[1]
                        remote = parts[2]
                        tx_queue = int(parts[4], 16)
                        rx_queue = int(parts[5], 16)
                        key = f"{local}->{remote}"
                        stats[key] = (tx_queue, rx_queue)
        except:
            pass
        return stats

    def update_stats(self):
        """Update traffic statistics."""
        current_time = time.time()
        connections = self._get_connections()
        current_stats = self._get_traffic_stats()

        # Calculate rates
        for conn in connections:
            key = f"{conn['local_addr']}:{conn['local_port']} -> {conn['remote_addr']}:{conn['remote_port']}"

            if key not in self.connections:
                self.connections[key] = TrafficStats(connection=key)

            stats = self.connections[key]

            # Calculate rate from queue changes
            stat_key = f"{conn['local_addr']}:{conn['local_port']}->{conn['remote_addr']}:{conn['remote_port']}"
            if stat_key in current_stats and stat_key in self._prev_stats:
                prev_tx, prev_rx, prev_time = self._prev_stats[stat_key]
                curr_tx, curr_rx = current_stats[stat_key]
                time_diff = current_time - prev_time

                if time_diff > 0:
                    stats.rate_up = max(0, (curr_tx - prev_tx) / time_diff)
                    stats.rate_down = max(0, (curr_rx - prev_rx) / time_diff)
                    stats.peak_up = max(stats.peak_up, stats.rate_up)
                    stats.peak_down = max(stats.peak_down, stats.rate_down)

            stats.total_up += int(stats.rate_up)
            stats.total_down += int(stats.rate_down)

            # Store for next calculation
            if stat_key in current_stats:
                self._prev_stats[stat_key] = (
                    current_stats[stat_key][0],
                    current_stats[stat_key][1],
                    current_time
                )

    def create_display(self) -> Table:
        """Create the traffic display table."""
        table = Table(title="📊 Network Traffic Monitor (iftop)")
        table.add_column("CONNECTION", style="cyan", min_width=30)
        table.add_column("PROTO", style="green", min_width=5)
        table.add_column("↑ RATE", justify="right", min_width=10)
        table.add_column("↓ RATE", justify="right", min_width=10)
        table.add_column("↑ TOTAL", justify="right", min_width=10)
        table.add_column("↓ TOTAL", justify="right", min_width=10)
        table.add_column("↑ PEAK", justify="right", min_width=10)

        # Sort by total traffic
        sorted_conns = sorted(
            self.connections.values(),
            key=lambda c: c.rate_up + c.rate_down,
            reverse=True
        )

        for stats in sorted_conns[:20]:  # Show top 20
            # Color based on activity
            if stats.rate_up > 1_000_000 or stats.rate_down > 1_000_000:
                rate_style = "bold red"
            elif stats.rate_up > 100_000 or stats.rate_down > 100_000:
                rate_style = "yellow"
            else:
                rate_style = "green"

            table.add_row(
                stats.connection,
                "TCP",
                f"[{rate_style}]{format_rate(stats.rate_up)}[/{rate_style}]",
                f"[{rate_style}]{format_rate(stats.rate_down)}[/{rate_style}]",
                format_bytes(stats.total_up),
                format_bytes(stats.total_down),
                format_rate(stats.peak_up)
            )

        if not sorted_conns:
            table.add_row("[dim]No active connections...[/dim]", "", "", "", "", "")

        return table

    def create_summary(self) -> Panel:
        """Create summary panel."""
        total_up = sum(c.rate_up for c in self.connections.values())
        total_down = sum(c.rate_down for c in self.connections.values())
        conn_count = len(self.connections)

        return Panel(
            f"[cyan]Connections:[/cyan] {conn_count}  |  "
            f"[green]↑ {format_rate(total_up)}[/green]  |  "
            f"[blue]↓ {format_rate(total_down)}[/blue]",
            title="Summary",
            border_style="blue"
        )


async def run_iftop(interface: Optional[str] = None, duration: int = 60):
    """Run the iftop monitor."""
    monitor = IftopMonitor(interface)

    console.print("[bold]Starting network traffic monitor...[/bold]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    with Live(console=console, refresh_per_second=2) as live:
        try:
            for _ in range(duration * 2):  # 2 updates per second
                monitor.update_stats()

                layout = Layout()
                layout.split_column(
                    Layout(monitor.create_display()),
                    Layout(monitor.create_summary())
                )

                live.update(layout)
                await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitor stopped.[/yellow]")


async def iftop_async(interface: Optional[str] = None) -> dict:
    """Async wrapper for iftop (single snapshot)."""
    monitor = IftopMonitor(interface)
    monitor.update_stats()

    connections = []
    for stats in monitor.connections.values():
        connections.append({
            "connection": stats.connection,
            "rate_up": stats.rate_up,
            "rate_down": stats.rate_down,
            "total_up": stats.total_up,
            "total_down": stats.total_down,
        })

    return {
        "connections": connections,
        "total_up": sum(c.rate_up for c in monitor.connections.values()),
        "total_down": sum(c.rate_down for c in monitor.connections.values()),
    }
