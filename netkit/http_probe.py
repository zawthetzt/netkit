"""HTTP service probing — status, headers, server detection, TLS info."""

import asyncio
from typing import Optional

import httpx

from netkit.output import console, print_http_result, set_output_mode, is_json_mode, print_json


async def http_probe(
    url: str,
    method: str = "GET",
    follow_redirects: bool = True,
    timeout: float = 10.0,
    output: str = "rich",
    _suppress_print: bool = False,
) -> dict:
    """Probe an HTTP/HTTPS endpoint."""
    set_output_mode(output)

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
        if not is_json_mode() and not _suppress_print:
            console.print(f"[dim]→ Trying {url}[/]")

    if not is_json_mode() and not _suppress_print:
        console.print(f"[bold]HTTP Probe:[/] [cyan]{url}[/]")

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=follow_redirects,
            verify=False,
        ) as client:
            if method.upper() == "HEAD":
                resp = await client.head(url)
            else:
                resp = await client.get(url)

            # Extract title from HTML
            title = None
            content_type = resp.headers.get("content-type", "")
            if "text/html" in content_type and resp.text:
                import re
                m = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
                if m:
                    title = m.group(1).strip()[:120]

            result = {
                "url": str(resp.url),
                "status": resp.status_code,
                "method": method.upper(),
                "server": resp.headers.get("server", ""),
                "content_type": content_type,
                "content_length": resp.headers.get("content-length", ""),
                "title": title or "",
                "tls": resp.url.scheme == "https",
                "hsts": "strict-transport-security" in resp.headers,
                "headers": dict(resp.headers),
                "redirect_history": [str(h.url) for h in resp.history] if resp.history else [],
            }

            if not is_json_mode() and not _suppress_print:
                print_http_result(result)
                if resp.history:
                    console.print(f"\n[dim]Redirects:[/]")
                    for h in resp.history:
                        console.print(f"  [yellow]{h.status_code} →[/] {h.url}")

            return result

    except httpx.TimeoutException:
        result = {"url": url, "error": "Connection timed out"}
    except httpx.ConnectError as e:
        result = {"url": url, "error": f"Connection failed: {e}"}
    except Exception as e:
        result = {"url": url, "error": str(e)}

    if not _suppress_print:
        if is_json_mode():
            print_json(result)
        else:
            console.print(f"[red]Error:[/] {result['error']}")

    return result


async def http_probe_multi(
    urls: list[str],
    method: str = "GET",
    follow_redirects: bool = True,
    timeout: float = 10.0,
    concurrency: int = 10,
    output: str = "rich",
) -> list[dict]:
    """Probe multiple HTTP endpoints concurrently."""
    set_output_mode(output)
    sem = asyncio.Semaphore(concurrency)

    async def _probe(url: str) -> dict:
        async with sem:
            return await http_probe(url, method, follow_redirects, timeout, output, _suppress_print=True)

    results = await asyncio.gather(*[_probe(u) for u in urls])

    if is_json_mode():
        print_json(results)

    return results
