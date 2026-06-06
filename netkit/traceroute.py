"""Traceroute — ICMP and UDP traceroute."""

import asyncio
import time
from typing import Optional

from netkit.output import console, print_trace_hop, set_output_mode, is_json_mode, print_json
from netkit.utils import resolve_hostname


async def traceroute(
    target: str,
    max_hops: int = 30,
    timeout: float = 2.0,
    udp: bool = False,
    output: str = "rich",
) -> list[dict]:
    """Perform traceroute to a target host.

    Uses ICMP echo by default (requires root/Scapy for raw sockets).
    Falls back to UDP traceroute when udp=True or ICMP fails.
    """
    set_output_mode(output)

    if not is_json_mode():
        console.print(f"[bold]Traceroute to[/] [cyan]{target}[/] (max {max_hops} hops)")

    try:
        return await _traceroute_scapy(target, max_hops, timeout, udp)
    except (ImportError, PermissionError):
        console.print("[yellow]Scapy unavailable or no raw socket permission. Trying system traceroute.[/]")
        return await _traceroute_system(target, max_hops, timeout, udp)


async def _traceroute_scapy(
    target: str,
    max_hops: int = 30,
    timeout: float = 2.0,
    udp: bool = False,
) -> list[dict]:
    """Traceroute using Scapy (raw packets)."""
    from scapy.all import IP, ICMP, UDP, sr1, conf

    conf.verb = 0
    results = []

    for ttl in range(1, max_hops + 1):
        if udp:
            pkt = IP(dst=target, ttl=ttl) / UDP(dport=33434 + ttl)
        else:
            pkt = IP(dst=target, ttl=ttl) / ICMP()

        start = time.time()
        reply = sr1(pkt, timeout=timeout, verbose=0)
        rtt = (time.time() - start) * 1000

        if reply is None:
            results.append({"hop": ttl, "ip": None, "hostname": None, "rtt_ms": None})
            print_trace_hop(ttl, None, None, None)
            continue

        src_ip = reply.src
        hostname = resolve_hostname(src_ip)
        results.append({
            "hop": ttl,
            "ip": src_ip,
            "hostname": hostname,
            "rtt_ms": round(rtt, 1),
        })
        print_trace_hop(ttl, src_ip, hostname, round(rtt, 1))

        # Check if we reached the target
        if reply.haslayer(ICMP):
            icmp = reply.getlayer(ICMP)
            if icmp.type == 0 or (icmp.type == 3 and icmp.code == 3):
                console.print(f"\n[green]Reached target {target} in {ttl} hops.[/]")
                break
        elif reply.haslayer(UDP) and src_ip == target:
            console.print(f"\n[green]Reached target {target} in {ttl} hops.[/]")
            break

    if is_json_mode():
        print_json(results)

    return results


async def _traceroute_system(
    target: str,
    max_hops: int = 30,
    timeout: float = 2.0,
    udp: bool = False,
) -> list[dict]:
    """Fallback traceroute using system traceroute command."""
    import subprocess
    import re

    cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", str(int(timeout))]
    if udp:
        cmd += ["-T"]
    cmd.append(target)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=max_hops * timeout + 10)
        results = []
        for line in stdout.decode().splitlines():
            m = re.match(r"\s*(\d+)\s+(\S+)", line)
            if not m:
                continue
            hop = int(m.group(1))
            ip = m.group(2) if m.group(2) != "*" else None
            rtt_match = re.findall(r"(\d+\.?\d*)\s*ms", line)

            # Parse RTTs from multiple probes
            rtts = [float(x) for x in rtt_match] if rtt_match else None
            hostname = resolve_hostname(ip) if ip else None

            results.append({
                "hop": hop,
                "ip": ip,
                "hostname": hostname,
                "rtt_ms": round(sum(rtts) / len(rtts), 1) if rtts else None,
            })
            print_trace_hop(hop, ip, hostname, round(sum(rtts) / len(rtts), 1) if rtts else None)

        if is_json_mode():
            print_json(results)
        return results
    except (FileNotFoundError, asyncio.TimeoutError) as e:
        console.print(f"[red]Traceroute failed: {e}[/]")
        return []
