"""Packet capture — live capture with BPF filter and basic analysis."""

import asyncio
from typing import Optional

from netkit.output import console, set_output_mode, is_json_mode, print_json, print_host_table


async def packet_capture(
    interface: str | None = None,
    count: int = 10,
    filter_expr: str = "",
    timeout: float = 10.0,
    output: str = "rich",
) -> list[dict]:
    """Capture packets on an interface."""
    set_output_mode(output)

    try:
        from scapy.all import sniff, conf
        conf.verb = 0
    except ImportError:
        console.print("[red]Scapy is required for packet capture. Install: pip install scapy[/]")
        return []

    try:
        # Auto-detect interface
        if not interface:
            import netifaces
            gateways = netifaces.gateways()
            default = gateways.get("default", {})
            if default:
                iface_name = list(default.values())[0][1]
                interface = iface_name

        console.print(
            f"[bold]Capturing[/] {count} packet{'s' if count > 1 else ''}"
            f" on [cyan]{interface or conf.iface}[/]"
            f"{' with filter: ' + filter_expr if filter_expr else ''}"
        )

        loop = asyncio.get_event_loop()
        packets = await loop.run_in_executor(
            None,
            lambda: sniff(
                iface=interface,
                count=count,
                filter=filter_expr if filter_expr else None,
                timeout=timeout,
            ),
        )

        results = []
        for pkt in packets:
            pkt_info = _summarize_packet(pkt)
            if pkt_info:
                results.append(pkt_info)
                if not is_json_mode():
                    _print_packet_summary(pkt_info)

        summary = {
            "interface": interface or str(conf.iface),
            "count": len(results),
            "packets": results,
        }

        if is_json_mode():
            print_json(summary)
        else:
            console.print(f"\n[bold]Captured {len(results)} packets[/]")

        return results

    except ImportError:
        console.print("[red]Install netifaces for auto-detect: pip install netifaces[/]")
        return []
    except PermissionError:
        console.print("[red]Packet capture requires root/admin privileges.[/]")
        return []
    except Exception as e:
        console.print(f"[red]Capture failed: {e}[/]")
        return []


def _summarize_packet(pkt) -> dict | None:
    """Extract human-readable summary from a packet."""
    from scapy.all import IP, IPv6, TCP, UDP, ICMP, ARP, DNS, Ether

    info = {
        "length": len(pkt),
        "time": pkt.time,
    }

    if pkt.haslayer(Ether):
        info["src_mac"] = pkt[Ether].src
        info["dst_mac"] = pkt[Ether].dst

    if pkt.haslayer(IP):
        info["src_ip"] = pkt[IP].src
        info["dst_ip"] = pkt[IP].dst
        info["proto"] = pkt[IP].proto
    elif pkt.haslayer(IPv6):
        info["src_ip"] = pkt[IPv6].src
        info["dst_ip"] = pkt[IPv6].dst
        info["proto"] = pkt[IPv6].nh
    elif pkt.haslayer(ARP):
        info["src_ip"] = pkt[ARP].psrc
        info["dst_ip"] = pkt[ARP].pdst
        info["proto"] = "ARP"
        info["summary"] = f"ARP: {pkt[ARP].psrc} → {pkt[ARP].pdst}"
        return info
    else:
        info["summary"] = pkt.summary()[:80]
        return info

    if pkt.haslayer(TCP):
        tcp = pkt[TCP]
        info["sport"] = tcp.sport
        info["dport"] = tcp.dport
        flags = ""
        if tcp.flags & 0x02: flags += "SYN "
        if tcp.flags & 0x10: flags += "ACK "
        if tcp.flags & 0x04: flags += "RST "
        if tcp.flags & 0x08: flags += "PSH "
        if tcp.flags & 0x01: flags += "FIN "
        info["flags"] = flags.strip()
        info["summary"] = f"TCP {info.get('src_ip','?')}:{tcp.sport} → {info.get('dst_ip','?')}:{tcp.dport} [{flags.strip()}]"
        info["protocol"] = "TCP"
    elif pkt.haslayer(UDP):
        udp = pkt[UDP]
        info["sport"] = udp.sport
        info["dport"] = udp.dport
        info["summary"] = f"UDP {info.get('src_ip','?')}:{udp.sport} → {info.get('dst_ip','?')}:{udp.dport}"
        info["protocol"] = "UDP"
    elif pkt.haslayer(ICMP):
        icmp = pkt[ICMP]
        info["summary"] = f"ICMP {info.get('src_ip','?')} → {info.get('dst_ip','?')} type={icmp.type} code={icmp.code}"
        info["protocol"] = "ICMP"
        info["icmp_type"] = icmp.type
        info["icmp_code"] = icmp.code
    else:
        info["summary"] = f"IP {info.get('src_ip','?')} → {info.get('dst_ip','?')}"
        info["protocol"] = "IP"

    return info


def _print_packet_summary(pkt: dict) -> None:
    """Print a single packet line."""
    summary = pkt.get("summary", "")
    proto = pkt.get("protocol", "")
    length = pkt.get("length", 0)

    color = "cyan"
    if proto == "TCP":
        color = "green"
    elif proto == "UDP":
        color = "blue"
    elif proto == "ICMP":
        color = "yellow"
    elif proto == "ARP":
        color = "magenta"

    console.print(f"  [{color}]{summary:<65}[/] [dim]{length} B[/]")
