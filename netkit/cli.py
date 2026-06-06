"""netkit CLI — Typer application with all subcommands."""

import asyncio
from typing import Optional, List

import typer
from rich import print as rprint

from netkit import __version__
from netkit.output import console, set_output_mode

app = typer.Typer(
    name="netkit",
    help="🧰 A full network engineer's CLI toolkit",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

VERSION_HELP = "Show the version and exit."
VERBOSE_HELP = "Enable verbose output."
OUTPUT_HELP = "Output mode: [green]rich[/] (default) or [green]json[/]."


def version_callback(value: bool):
    if value:
        rprint(f"[bold cyan]netkit[/] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-V", help=VERSION_HELP, callback=version_callback),
    verbose: bool = typer.Option(False, "--verbose", "-v", help=VERBOSE_HELP),
):
    """[bold cyan]netkit[/] — Network toolkit for engineers 🔧

    Use [bold]netkit COMMAND --help[/] for command-specific help.
    """
    pass


# ─── Ping ────────────────────────────────────────────────────────────────


@app.command()
def ping(
    targets: List[str] = typer.Argument(..., help="Target host(s), IP(s), or CIDR range(s)"),
    count: int = typer.Option(3, "--count", "-c", help="Number of echo requests per host"),
    timeout: float = typer.Option(2.0, "--timeout", "-t", help="Timeout per host in seconds"),
    concurrency: int = typer.Option(20, "--concurrency", "-j", help="Max concurrent hosts"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]ICMP ping sweep[/green] — single host or subnet scan.

    Examples:

        netkit ping 8.8.8.8

        netkit ping 192.168.1.0/24

        netkit ping 192.168.1.1-20 --count 1
    """
    from netkit.ping import ping_sweep

    asyncio.run(ping_sweep(targets, count, timeout, concurrency, output))


# ─── Port Scan ───────────────────────────────────────────────────────────


@app.command()
def scan(
    targets: List[str] = typer.Argument(..., help="Target host(s), IP(s), or CIDR range(s)"),
    ports: str = typer.Option(None, "--ports", "-p", help="Port(s) to scan. E.g. '22,80,443' or '1-1024'"),
    timeout: float = typer.Option(1.0, "--timeout", "-t", help="Timeout per port in seconds"),
    concurrency: int = typer.Option(100, "--concurrency", "-j", help="Max concurrent ports"),
    syn: bool = typer.Option(False, "--syn", "-s", help="Use SYN scan (requires root)"),
    udp: bool = typer.Option(False, "--udp", "-u", help="Also scan UDP ports"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]Port scanner[/green] — TCP connect, SYN, and UDP scanning.

    Examples:

        netkit scan 192.168.1.1

        netkit scan 10.0.0.1 --ports 22,80,443

        netkit scan 10.0.0.1 -p 1-1000 --syn

        netkit scan 192.168.1.0/24 -p 22,80 --udp
    """
    from netkit.port_scanner import port_scan

    scan_type = "syn" if syn else "connect"
    asyncio.run(port_scan(targets, ports, timeout, concurrency, scan_type, output, udp))


# ─── Service Detection ───────────────────────────────────────────────────


@app.command()
def service(
    hosts: List[str] = typer.Argument(..., help="Host(s) to probe"),
    ports: str = typer.Option("22,80,443,8080,8443", "--ports", "-p", help="Port(s) to probe for banners"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="Timeout per port in seconds"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]Service & banner detection[/green] — grab banners from open ports.

    Examples:

        netkit service 192.168.1.1

        netkit service example.com -p 22,80,443,3306
    """
    from netkit.service_detect import detect_services_multi
    from netkit.utils import parse_ports

    port_list = parse_ports(ports)
    asyncio.run(detect_services_multi(hosts, port_list, timeout, output))


# ─── Traceroute ──────────────────────────────────────────────────────────


@app.command()
def trace(
    target: str = typer.Argument(..., help="Target hostname or IP"),
    max_hops: int = typer.Option(30, "--max-hops", "-m", help="Maximum number of hops"),
    timeout: float = typer.Option(2.0, "--timeout", "-t", help="Timeout per hop in seconds"),
    udp: bool = typer.Option(False, "--udp", "-u", help="Use UDP instead of ICMP"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]Traceroute[/green] — trace the path to a network host.

    Examples:

        netkit trace 8.8.8.8

        netkit trace example.com --max-hops 20
    """
    from netkit.traceroute import traceroute

    asyncio.run(traceroute(target, max_hops, timeout, udp, output))


# ─── DNS ─────────────────────────────────────────────────────────────────


@app.command()
def dns(
    domain: str = typer.Argument(..., help="Domain to query"),
    types: str = typer.Option(
        "A,AAAA,MX,NS,TXT,SOA,CAA,CNAME",
        "--types", "-t",
        help="Record types to query (comma-separated)",
    ),
    nameserver: str = typer.Option(None, "--nameserver", "-n", help="Specific nameserver to query"),
    reverse: bool = typer.Option(False, "--reverse", "-r", help="Reverse DNS lookup (pass IP as domain)"),
    zone: bool = typer.Option(False, "--zone", "-z", help="Attempt zone transfer (AXFR)"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]DNS toolkit[/green] — lookups, reverse DNS, zone transfers.

    Examples:

        netkit dns example.com

        netkit dns example.com --types A,MX,NS

        netkit dns 8.8.8.8 --reverse

        netkit dns example.com --zone
    """
    from netkit.dns_tools import dns_lookup, reverse_dns, zone_transfer

    if zone:
        asyncio.run(zone_transfer(domain, nameserver, output))
    elif reverse:
        asyncio.run(reverse_dns(domain, output))
    else:
        type_list = [t.strip().upper() for t in types.split(",")]
        asyncio.run(dns_lookup(domain, type_list, nameserver, output))


# ─── Whois ───────────────────────────────────────────────────────────────


@app.command()
def whois(
    query: str = typer.Argument(..., help="Domain name or IP address to look up"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]Whois lookup[/green] — domain & IP registration information.

    Examples:

        netkit whois example.com

        netkit whois 8.8.8.8
    """
    from netkit.whois_lookup import whois_lookup

    asyncio.run(whois_lookup(query, output))


# ─── HTTP Probe ──────────────────────────────────────────────────────────


@app.command()
def http(
    urls: List[str] = typer.Argument(..., help="URL(s) to probe"),
    method: str = typer.Option("GET", "--method", "-X", help="HTTP method (GET or HEAD)"),
    no_follow: bool = typer.Option(False, "--no-follow", help="Do not follow redirects"),
    timeout: float = typer.Option(10.0, "--timeout", "-t", help="Request timeout in seconds"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]HTTP probe[/green] — check web server status, headers, and TLS.

    Examples:

        netkit http example.com

        netkit http https://example.com/api --method HEAD

        netkit http example.com google.com --no-follow
    """
    from netkit.http_probe import http_probe_multi

    asyncio.run(http_probe_multi(urls, method, not no_follow, timeout, output=output))


# ─── Subnet ──────────────────────────────────────────────────────────────


@app.command()
def subnet(
    cidr: str = typer.Argument(..., help="CIDR notation (e.g., 192.168.1.0/24)"),
    scan: bool = typer.Option(False, "--scan", "-s", help="Scan subnet for live hosts"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]Subnet calculator[/green] — calculate subnet details and scan for live hosts.

    Examples:

        netkit subnet 192.168.1.0/24

        netkit subnet 10.0.0.0/8 --scan
    """
    from netkit.subnet import subnet_calc, subnet_scan

    if scan:
        asyncio.run(subnet_scan(cidr, output))
    else:
        set_output_mode(output)
        subnet_calc(cidr)


# ─── Packet Capture ──────────────────────────────────────────────────────


@app.command()
def capture(
    count: int = typer.Option(10, "--count", "-c", help="Number of packets to capture"),
    interface: str = typer.Option(None, "--interface", "-i", help="Network interface (auto-detect if omitted)"),
    filter_expr: str = typer.Option("", "--filter", "-f", help="BPF filter expression (e.g., 'tcp port 80')"),
    timeout: float = typer.Option(10.0, "--timeout", "-t", help="Capture timeout in seconds"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]Packet capture[/green] — live capture with BPF filter.

    Examples:

        netkit capture -c 20

        netkit capture -i eth0 -f "tcp port 80" -c 50

        netkit capture -f "icmp" -c 5
    """
    from netkit.packet_capture import packet_capture

    asyncio.run(packet_capture(interface, count, filter_expr, timeout, output))


# ─── Interfaces ──────────────────────────────────────────────────────────


@app.command()
def interfaces(
    name: str = typer.Argument(None, help="Interface name to show details for"),
    output: str = typer.Option("rich", "--output", "-o", help=OUTPUT_HELP),
):
    """[green]Network interfaces[/green] — show local interface information.

    Examples:

        netkit interfaces

        netkit interfaces eth0
    """
    from netkit.interface import list_interfaces, interface_detail

    if name:
        asyncio.run(interface_detail(name, output))
    else:
        asyncio.run(list_interfaces(output))


if __name__ == "__main__":
    app()
