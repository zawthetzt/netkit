"""Rich output helpers: tables, panels, progress bars, colors."""

import json
from datetime import datetime

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

console = Console()

_output_mode: str = "rich"  # "rich" or "json"


def set_output_mode(mode: str) -> None:
    global _output_mode
    _output_mode = mode


def get_output_mode() -> str:
    return _output_mode


def is_json_mode() -> bool:
    return _output_mode == "json"


def print_json(data) -> None:
    """Print data as JSON with indentation."""
    json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    console.print(json_str)


def maybe_print(data, table_builder=None):
    """Route output: if JSON mode, print JSON; else build and print a Rich table."""
    if is_json_mode():
        print_json(data)
    elif table_builder:
        table_builder(data)
    else:
        print_json(data)


def result_panel(title: str, content: str, style: str = "cyan") -> Panel:
    return Panel(content, title=title, border_style=style)


def scan_progress(description: str = "Scanning...", transient: bool = True):
    """Return a Progress context manager for scans."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=transient,
    )


def host_result_table(title: str, results: list[dict], columns: list[str] | None = None) -> Table:
    """Build a table from a list of dicts. Each dict key becomes a column."""
    if not results:
        table = Table(title=title, box=box.SIMPLE)
        table.add_column("No results")
        return table

    if columns is None:
        columns = list(results[0].keys())

    table = Table(title=title, box=box.ROUNDED, header_style="bold cyan")
    for col in columns:
        table.add_column(col.replace("_", " ").title())

    for row in results:
        vals = []
        for col in columns:
            v = row.get(col)
            if v is None:
                vals.append("—")
            elif isinstance(v, bool):
                vals.append("[green]✓[/]" if v else "[red]✗[/]")
            else:
                vals.append(str(v))
        table.add_row(*vals)

    return table


def print_host_table(title: str, results: list[dict], columns: list[str] | None = None) -> None:
    """Print a table from scan results."""
    table = host_result_table(title, results, columns)
    console.print(table)


def print_open_ports(host: str, ports: list[dict]) -> None:
    """Pretty-print a port scan result."""
    if not ports:
        console.print(f"[yellow]{host}:[/] no open ports found")
        return

    table = Table(title=f"Open Ports — {host}", box=box.ROUNDED, header_style="bold green")
    table.add_column("Port", style="cyan")
    table.add_column("Protocol", style="blue")
    table.add_column("State", style="green")
    table.add_column("Service")
    table.add_column("Banner")

    for p in ports:
        table.add_row(
            str(p["port"]),
            p.get("protocol", "tcp"),
            p.get("state", "open"),
            p.get("service", "unknown"),
            (p.get("banner", "") or "")[:60],
        )
    console.print(table)


def print_ping_result(host: str, ip: str, rtt_ms: float | None, success: bool) -> None:
    """Print a single ping result line."""
    if success:
        console.print(f"[green]{host}[/] ([cyan]{ip}[/]) — {rtt_ms:.1f} ms")
    else:
        console.print(f"[red]{host}[/] ([cyan]{ip}[/]) — [red]timeout[/]")


def print_trace_hop(hop: int, ip: str | None, hostname: str | None, rtt_ms: float | None) -> None:
    """Print a single traceroute hop."""
    if ip:
        rtt = f"{rtt_ms:.1f} ms" if rtt_ms else "*"
        name = f" ({hostname})" if hostname else ""
        console.print(f"  {hop:>2}.  {ip:<15}{name}  {rtt}")
    else:
        console.print(f"  {hop:>2}.  [dim]* * *[/]")


def print_dns_record(record_type: str, answers: list[dict]) -> None:
    """Print DNS records in a table."""
    if not answers:
        console.print(f"[yellow]No {record_type} records found[/]")
        return

    table = Table(title=f"{record_type} Records", box=box.SIMPLE, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("TTL")
    table.add_column("Value")

    for ans in answers:
        table.add_row(ans.get("name", ""), str(ans.get("ttl", "")), ans.get("value", ""))
    console.print(table)


def print_interface_info(interfaces: list[dict]) -> None:
    """Print network interface info in a table."""
    table = Table(title="Network Interfaces", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Interface")
    table.add_column("MAC Address")
    table.add_column("IP Address")
    table.add_column("Netmask")
    table.add_column("Status")
    table.add_column("Speed")

    for iface in interfaces:
        status_style = "green" if iface.get("is_up") else "red"
        table.add_row(
            iface.get("name", ""),
            iface.get("mac", ""),
            iface.get("ip", ""),
            iface.get("netmask", ""),
            f"[{status_style}]{'UP' if iface.get('is_up') else 'DOWN'}[/]",
            iface.get("speed", ""),
        )
    console.print(table)


def print_subnet_info(info: dict) -> None:
    """Display subnet calculation results."""
    layout = Layout()
    layout.split_column(
        Layout(Panel(f"[bold]Network:[/] {info.get('network')}", title="Subnet Info")),
    )

    table = Table(box=box.SIMPLE, header_style="bold cyan")
    table.add_column("Property")
    table.add_column("Value")

    for key, val in info.items():
        if key == "network":
            continue
        table.add_row(key.replace("_", " ").title(), str(val))

    console.print(table)


def print_http_result(result: dict) -> None:
    """Display HTTP probe result."""
    if "error" in result:
        console.print(f"[red]Error:[/] {result['error']}")
        return

    console.print(Panel(
        f"[bold]URL:[/]       {result.get('url', '')}\n"
        f"[bold]Status:[/]    [{'green' if result.get('status', 0) < 400 else 'yellow'}]{result.get('status')}[/]\n"
        f"[bold]Server:[/]    {result.get('server', '—')}\n"
        f"[bold]Title:[/]     {result.get('title', '—')}\n"
        f"[bold]Content-Type:[/] {result.get('content_type', '—')}\n"
        f"[bold]TLS:[/]      {'[green]✓[/]' if result.get('tls') else '[yellow]✗[/]'}\n"
        f"[bold]HSTS:[/]     {'[green]✓[/]' if result.get('hsts') else '[yellow]✗[/]'}",
        title="HTTP Probe",
        border_style="cyan",
    ))
