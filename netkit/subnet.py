"""Subnet calculator & scanner — CIDR info, host enumeration."""

import ipaddress
from typing import Optional

from netkit.output import (
    console,
    print_subnet_info,
    set_output_mode,
    is_json_mode,
    print_json,
)
from netkit.utils import parse_targets


def subnet_calc(cidr: str) -> dict:
    """Calculate subnet information from a CIDR notation."""
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError as e:
        return {"error": str(e)}

    hosts = list(net.hosts()) if net.num_addresses > 2 else []
    info = {
        "network": str(net),
        "netmask": str(net.netmask),
        "wildcard_mask": str(net.hostmask),
        "cidr_prefix": net.prefixlen,
        "address_count": net.num_addresses,
        "usable_hosts": len(hosts),
        "first_host": str(hosts[0]) if hosts else "—",
        "last_host": str(hosts[-1]) if hosts else "—",
        "broadcast": str(net.broadcast_address) if net.broadcast_address else "—",
        "is_private": net.is_private,
        "is_loopback": net.is_loopback,
        "ip_version": net.version,
    }

    if is_json_mode():
        print_json(info)
    else:
        print_subnet_info(info)

    return info


async def subnet_scan(
    cidr: str,
    output: str = "rich",
) -> list[dict]:
    """Scan a subnet for live hosts via ping."""
    set_output_mode(output)

    # Reuse the ping sweep logic
    from netkit.ping import ping_sweep

    if not is_json_mode():
        console.print(f"[bold]Scanning subnet:[/] [cyan]{cidr}[/]")
    results = await ping_sweep(
        targets=[cidr],
        count=2,
        timeout=1.5,
        output=output,
    )

    return results
