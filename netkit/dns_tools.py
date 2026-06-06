"""DNS toolkit — lookups, reverse DNS, zone transfer attempts."""

import asyncio
from typing import Optional

from netkit.output import (
    console,
    print_dns_record,
    set_output_mode,
    is_json_mode,
    print_json,
)
from netkit.utils import resolve_host


async def _query(domain: str, record_type: str, nameserver: str | None = None) -> list[dict]:
    """Async DNS query using dnspython. Returns list of {name, ttl, value} dicts."""
    import dns.resolver
    import dns.rdatatype

    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 3.0
        resolver.lifetime = 5.0
        if nameserver:
            resolver.nameservers = [nameserver]

        answers = resolver.resolve(domain, record_type, raise_on_no_answer=False)
        records = []
        if answers.rrset:
            for rdata in answers.rrset:
                records.append({
                    "name": str(answers.rrset.name).rstrip("."),
                    "ttl": answers.rrset.ttl,
                    "type": record_type,
                    "value": rdata.to_text() if hasattr(rdata, "to_text") else str(rdata),
                })
        return records
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return []
    except Exception:
        return []


async def _query_text(domain: str, record_type: str, nameserver: str | None = None) -> list[str]:
    """Generic query returning string values."""
    answers = await _query(domain, record_type, nameserver)
    return [a["value"] for a in answers]


async def _query_text(domain: str, record_type: str, nameserver: str | None = None) -> list[str]:
    """Generic query returning string values."""
    answers = await _query(domain, record_type, nameserver)
    return [str(a) for a in answers]


async def dns_lookup(
    domain: str,
    types: list[str] | None = None,
    nameserver: str | None = None,
    output: str = "rich",
) -> dict:
    """Perform DNS lookups for a domain."""
    set_output_mode(output)

    if types is None:
        types = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CAA", "CNAME"]

    if not is_json_mode():
        console.print(f"[bold]DNS Lookup for[/] [cyan]{domain}[/]")
    if not is_json_mode() and nameserver:
        console.print(f"  Nameserver: {nameserver}")

    results: dict = {"domain": domain, "records": {}}

    for rtype in types:
        answers = await _query(domain, rtype, nameserver)
        results["records"][rtype] = [a["value"] for a in answers]

        if not is_json_mode():
            print_dns_record(rtype, answers)

    if is_json_mode():
        print_json(results)

    # Resolve A record for human-friendly summary
    ip = resolve_host(domain)
    if ip and not is_json_mode():
        console.print(f"\n[dim]Resolved IP: {ip}[/]")

    return results


async def reverse_dns(ip: str, output: str = "rich") -> dict | None:
    """Reverse DNS lookup for an IP address."""
    set_output_mode(output)

    try:
        from netkit.utils import resolve_hostname

        hostname = resolve_hostname(ip)
        result = {"ip": ip, "hostname": hostname}

        if is_json_mode():
            print_json(result)
        else:
            if hostname:
                console.print(f"[green]{ip}[/] → [cyan]{hostname}[/]")
            else:
                console.print(f"[yellow]{ip}[/] → [dim]no PTR record[/]")

        return result
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        return None


async def zone_transfer(domain: str, nameserver: str | None = None, output: str = "rich") -> dict:
    """Attempt DNS zone transfer (AXFR)."""
    set_output_mode(output)

    import dns.zone
    import dns.query

    console.print(f"[bold]Attempting zone transfer for[/] [cyan]{domain}[/]")

    # If no nameserver given, find NS records
    ns_servers = [nameserver] if nameserver else await _query_text(domain, "NS")
    if not ns_servers:
        console.print("[red]No nameservers found for zone transfer attempt.[/]")
        return {"domain": domain, "success": False, "error": "No nameservers", "records": []}

    results = {"domain": domain, "success": False, "nameservers_tried": [], "records": []}

    for ns in ns_servers:
        console.print(f"  Trying nameserver: {ns}")
        try:
            zone = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: dns.zone.from_xfr(dns.query.xfr(str(ns), domain, timeout=5)),
            )
            if zone:
                records = []
                for name, node in zone.nodes.items():
                    for rdataset in node.rdatasets:
                        for rdata in rdataset:
                            records.append({
                                "name": str(name) + "." + domain,
                                "ttl": rdataset.ttl,
                                "type": dns.rdatatype.to_text(rdataset.rdtype),
                                "value": str(rdata),
                            })

                results["success"] = True
                results["nameservers_tried"].append(str(ns))
                results["records"] = records

                if is_json_mode():
                    continue

                console.print(f"[green]Zone transfer successful from {ns}![/]")
                from netkit.output import print_host_table
                print_host_table(
                    f"Zone Transfer Results — {domain}",
                    records,
                    columns=["name", "type", "ttl", "value"],
                )
                return results
            else:
                console.print(f"  [yellow]Empty zone from {ns}[/]")
        except Exception as e:
            console.print(f"  [red]Failed: {e}[/]")
            results["nameservers_tried"].append(str(ns))

    if not results["success"] and not is_json_mode():
        console.print("[red]Zone transfer denied by all nameservers.[/]")

    if is_json_mode():
        print_json(results)

    return results
