"""Whois lookup — domain and IP whois queries."""

import asyncio
from typing import Optional

from netkit.output import console, set_output_mode, is_json_mode, print_json, result_panel


async def whois_lookup(
    query: str,
    output: str = "rich",
) -> dict:
    """Perform whois lookup for a domain or IP address."""
    set_output_mode(output)

    import whois as whois_module

    if not is_json_mode():
        console.print(f"[bold]Whois lookup for[/] [cyan]{query}[/]")

    try:
        loop = asyncio.get_event_loop()

        def _do_whois():
            return whois_module.whois(query)

        w = await loop.run_in_executor(None, _do_whois)

        # Build structured result
        result: dict = {"query": query}
        if w.get("domain_name"):
            result["domain_name"] = w["domain_name"]
        if w.get("registrar"):
            result["registrar"] = w["registrar"]
        if w.get("whois_server"):
            result["whois_server"] = w["whois_server"]
        if w.get("creation_date"):
            result["creation_date"] = _fmt_date(w["creation_date"])
        if w.get("expiration_date"):
            result["expiration_date"] = _fmt_date(w["expiration_date"])
        if w.get("updated_date"):
            result["updated_date"] = _fmt_date(w["updated_date"])
        if w.get("name_servers"):
            result["name_servers"] = w["name_servers"]
        if w.get("status"):
            result["status"] = w["status"]
        if w.get("org"):
            result["organization"] = w["org"]
        if w.get("country"):
            result["country"] = w["country"]
        if w.get("city"):
            result["city"] = w["city"]
        if w.get("address"):
            result["address"] = w["address"]
        if w.get("netrange"):
            result["netrange"] = w["netrange"]
        if w.get("cidr"):
            result["cidr"] = w["cidr"]
        if w.get("netname"):
            result["netname"] = w["netname"]

        if is_json_mode():
            print_json(result)
        else:
            _print_whois(result)

        return result
    except ImportError:
        console.print("[red]python-whois not installed. Install with: pip install python-whois[/]")
        return {"query": query, "error": "python-whois not available"}
    except Exception as e:
        console.print(f"[red]Whois lookup failed: {e}[/]")
        return {"query": query, "error": str(e)}


def _fmt_date(d) -> str:
    """Format date value that could be a list or datetime."""
    if isinstance(d, list):
        return str(d[0]) if d else "—"
    return str(d) if d else "—"


def _print_whois(result: dict) -> None:
    """Pretty-print whois results."""
    from netkit.output import console

    lines = []
    for key, val in result.items():
        if key == "query":
            continue
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val[:5])
            if len(result.get(key, [])) > 5:
                val += f" ... (+{len(result[key]) - 5} more)"
        lines.append(f"[bold]{key.replace('_', ' ').title()}:[/]  {val}")

    if lines:
        console.print(result_panel(
            f"Whois — {result.get('query', '')}",
            "\n".join(lines),
            "green",
        ))
