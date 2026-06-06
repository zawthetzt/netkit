"""ICMP ping sweep — single host or subnet scan."""

import asyncio
import time
from typing import Optional

from netkit.output import (
    console,
    print_ping_result,
    host_result_table,
    set_output_mode,
    is_json_mode,
    print_json,
)
from netkit.utils import parse_targets, resolve_host


async def _ping_host(host: str, count: int = 3, timeout: float = 2.0) -> dict:
    """Ping a single host using Scapy's ICMP echo request."""
    try:
        from scapy.all import IP, ICMP, sr1, conf

        conf.verb = 0  # suppress scapy output

        ip = resolve_host(host) or host
        rtts = []
        successes = 0

        for _ in range(count):
            pkt = IP(dst=ip) / ICMP()
            start = time.time()
            reply = sr1(pkt, timeout=timeout, verbose=0)
            elapsed = (time.time() - start) * 1000

            if reply is not None:
                rtts.append(elapsed)
                successes += 1

        avg_rtt = sum(rtts) / len(rtts) if rtts else None
        loss_pct = ((count - successes) / count) * 100

        return {
            "host": host,
            "ip": ip,
            "sent": count,
            "received": successes,
            "loss_pct": loss_pct,
            "avg_rtt_ms": round(avg_rtt, 1) if avg_rtt else None,
            "min_rtt_ms": round(min(rtts), 1) if rtts else None,
            "max_rtt_ms": round(max(rtts), 1) if rtts else None,
            "alive": successes > 0,
        }
    except ImportError:
        return await _ping_host_subprocess(host, count, timeout)
    except PermissionError:
        return await _ping_host_subprocess(host, count, timeout)


async def _ping_host_subprocess(host: str, count: int = 3, timeout: float = 2.0) -> dict:
    """Fallback: use system ping command."""
    import subprocess

    ip = resolve_host(host) or host
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", str(count), "-W", str(int(timeout)), ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)
        text = stdout.decode()

        received = 0
        avg_rtt = None
        for line in text.splitlines():
            if "bytes from" in line:
                received += 1
            if "avg" in line or "mdev" in line:
                import re
                m = re.search(r"([\d.]+)/([\d.]+)/([\d.]+)", line)
                if m:
                    avg_rtt = float(m.group(2))

        loss_pct = ((count - received) / count) * 100
        return {
            "host": host,
            "ip": ip,
            "sent": count,
            "received": received,
            "loss_pct": loss_pct,
            "avg_rtt_ms": round(avg_rtt, 1) if avg_rtt else None,
            "min_rtt_ms": None,
            "max_rtt_ms": None,
            "alive": received > 0,
        }
    except Exception:
        return {
            "host": host,
            "ip": ip,
            "sent": count,
            "received": 0,
            "loss_pct": 100.0,
            "avg_rtt_ms": None,
            "min_rtt_ms": None,
            "max_rtt_ms": None,
            "alive": False,
        }


async def ping_sweep(
    targets: list[str],
    count: int = 3,
    timeout: float = 2.0,
    concurrency: int = 20,
    output: str = "rich",
) -> list[dict]:
    """Ping sweep across multiple targets."""
    set_output_mode(output)

    ips = parse_targets(targets)
    if not ips:
        console.print("[red]No valid targets specified.[/]")
        return []

    sem = asyncio.Semaphore(concurrency)

    async def _ping(host: str) -> dict:
        async with sem:
            return await _ping_host(host, count, timeout)

    results = await asyncio.gather(*[_ping(h) for h in ips])

    if is_json_mode():
        print_json(results)
    else:
        for r in results:
            print_ping_result(
                r["host"], r["ip"], r["avg_rtt_ms"], r["alive"]
            )

        alive = [r for r in results if r["alive"]]
        console.print(
            f"\n[bold]Results:[/] {len(alive)}/{len(results)} hosts alive"
        )

    return results
