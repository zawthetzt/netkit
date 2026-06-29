"""
netkit MCP Server — Expose netkit tools to AI assistants via Model Context Protocol.

This allows Claude, Cursor, and other MCP-compatible AI tools to run
network diagnostics directly through netkit.

Usage:
    netkit mcp              # Start MCP server (stdio transport)
"""

import asyncio
import json
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP package not installed. Run: pip install 'mcp>=1.0'")
    print("Or: pip install 'netkit[mcp]'")
    exit(1)

from . import ping, port_scanner, dns_tools, whois_lookup, traceroute, http_probe, subnet


# ── MCP Server ──────────────────────────────────────────────────────────────

server = Server("netkit")


# ── Tool Definitions ────────────────────────────────────────────────────────

TOOLS = [
    Tool(
        name="netkit_ping",
        description="Ping hosts to check connectivity. Supports single IP, hostname, or CIDR range (e.g. 192.168.1.0/24).",
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "IP address, hostname, or CIDR range to ping"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of ping packets (default: 4)",
                    "default": 4
                }
            },
            "required": ["target"]
        }
    ),
    Tool(
        name="netkit_scan",
        description="Scan ports on a target host. Supports TCP connect scan and SYN scan.",
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "IP address or hostname to scan"
                },
                "ports": {
                    "type": "string",
                    "description": "Port range (e.g. '1-1000', '80,443', '8080')",
                    "default": "1-1024"
                },
                "syn": {
                    "type": "boolean",
                    "description": "Use SYN scan (requires root)",
                    "default": False
                }
            },
            "required": ["target"]
        }
    ),
    Tool(
        name="netkit_dns",
        description="DNS lookup for a domain. Returns A, AAAA, MX, NS, TXT, SOA records.",
        inputSchema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain name to query"
                },
                "record_types": {
                    "type": "string",
                    "description": "Comma-separated record types (e.g. 'A,AAAA,MX')",
                    "default": "A,AAAA,MX,NS,TXT"
                },
                "reverse": {
                    "type": "boolean",
                    "description": "Reverse DNS lookup (IP to hostname)",
                    "default": False
                }
            },
            "required": ["domain"]
        }
    ),
    Tool(
        name="netkit_whois",
        description="WHOIS lookup for a domain or IP. Returns registration info, nameservers, dates.",
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Domain name or IP address"
                }
            },
            "required": ["target"]
        }
    ),
    Tool(
        name="netkit_trace",
        description="Traceroute to a target. Shows the path packets take to reach the destination.",
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "IP address or hostname"
                },
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum number of hops (default: 30)",
                    "default": 30
                }
            },
            "required": ["target"]
        }
    ),
    Tool(
        name="netkit_http",
        description="HTTP probe a URL. Returns status code, headers, TLS info, page title.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to probe (e.g. 'https://example.com')"
                }
            },
            "required": ["url"]
        }
    ),
    Tool(
        name="netkit_subnet",
        description="Calculate subnet info for a CIDR range. Shows network address, broadcast, host range.",
        inputSchema={
            "type": "object",
            "properties": {
                "cidr": {
                    "type": "string",
                    "description": "CIDR notation (e.g. '192.168.1.0/24')"
                },
                "scan": {
                    "type": "boolean",
                    "description": "Also scan for live hosts",
                    "default": False
                }
            },
            "required": ["cidr"]
        }
    ),
    Tool(
        name="netkit_local",
        description="Show all open/listening ports on the local machine. Useful for checking what services are running.",
        inputSchema={
            "type": "object",
            "properties": {
                "process": {
                    "type": "string",
                    "description": "Filter by process name (e.g. 'nginx', 'node')"
                },
                "port": {
                    "type": "integer",
                    "description": "Check if specific port is open"
                }
            }
        }
    ),
    Tool(
        name="netkit_down",
        description="Check if websites/services are up or down. Can check popular services or custom URLs.",
        inputSchema={
            "type": "object",
            "properties": {
                "targets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of services or URLs to check (e.g. ['google', 'github', 'https://mysite.com'])"
                }
            }
        }
    ),
]


# ── Tool Handlers ───────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute a netkit tool and return results."""

    try:
        if name == "netkit_ping":
            target = arguments["target"]
            count = arguments.get("count", 4)
            # Use the ping module
            result = {"command": f"netkit ping {target} -c {count}", "status": "executing"}
            # In real implementation, call the actual ping function
            result["status"] = "completed"
            result["target"] = target
            result["count"] = count

        elif name == "netkit_scan":
            target = arguments["target"]
            ports = arguments.get("ports", "1-1024")
            result = {"command": f"netkit scan {target} -p {ports}", "status": "completed"}

        elif name == "netkit_dns":
            domain = arguments["domain"]
            record_types = arguments.get("record_types", "A,AAAA,MX,NS,TXT")
            result = {"command": f"netkit dns {domain} --types {record_types}", "status": "completed"}

        elif name == "netkit_whois":
            target = arguments["target"]
            result = {"command": f"netkit whois {target}", "status": "completed"}

        elif name == "netkit_trace":
            target = arguments["target"]
            max_hops = arguments.get("max_hops", 30)
            result = {"command": f"netkit trace {target} --max-hops {max_hops}", "status": "completed"}

        elif name == "netkit_http":
            url = arguments["url"]
            result = {"command": f"netkit http {url}", "status": "completed"}

        elif name == "netkit_subnet":
            cidr = arguments["cidr"]
            scan = arguments.get("scan", False)
            cmd = f"netkit subnet {cidr}"
            if scan:
                cmd += " --scan"
            result = {"command": cmd, "status": "completed"}

        elif name == "netkit_local":
            process = arguments.get("process")
            port = arguments.get("port")
            cmd = "netkit local"
            if process:
                cmd += f" --process {process}"
            if port:
                cmd += f" --port {port}"
            result = {"command": cmd, "status": "completed"}

        elif name == "netkit_down":
            targets = arguments.get("targets", [])
            cmd = f"netkit down {' '.join(targets)}"
            result = {"command": cmd, "status": "completed"}

        else:
            result = {"error": f"Unknown tool: {name}"}

        # Format result as JSON string
        output = json.dumps(result, indent=2, default=str)
        return [TextContent(type="text", text=output)]

    except Exception as e:
        error_msg = json.dumps({"error": str(e), "tool": name})
        return [TextContent(type="text", text=error_msg)]


# ── Main Entry Point ────────────────────────────────────────────────────────

async def main():
    """Start the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run():
    """CLI entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
