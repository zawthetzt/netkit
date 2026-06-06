"""Network interface information — list local interfaces, IPs, MAC, status."""

import asyncio
from typing import Optional

from netkit.output import (
    console,
    print_interface_info,
    set_output_mode,
    is_json_mode,
    print_json,
)


async def list_interfaces(output: str = "rich") -> list[dict]:
    """List all available network interfaces with details."""
    set_output_mode(output)

    interfaces = []

    try:
        import netifaces

        for iface_name in netifaces.interfaces():
            info = {"name": iface_name}
            addrs = netifaces.ifaddresses(iface_name)
            details = netifaces.ifdetails(iface_name)

            # MAC address
            if netifaces.AF_LINK in addrs:
                info["mac"] = addrs[netifaces.AF_LINK][0].get("addr", "")

            # IPv4
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr.get("addr", "")
                    if ip and not ip.startswith("127."):
                        info["ip"] = ip
                        info["netmask"] = addr.get("netmask", "")
                        info["broadcast"] = addr.get("broadcast", "")
                        break
                if "ip" not in info and addrs[netifaces.AF_INET]:
                    info["ip"] = addrs[netifaces.AF_INET][0].get("addr", "")
                    info["netmask"] = addrs[netifaces.AF_INET][0].get("netmask", "")

            # IPv6
            if netifaces.AF_INET6 in addrs:
                for addr in addrs[netifaces.AF_INET6]:
                    ip6 = addr.get("addr", "")
                    if ip6 and not ip6.startswith("fe80::") and not ip6 == "::1":
                        info["ipv6"] = ip6.split("%")[0]
                        break
                if "ipv6" not in info:
                    for addr in addrs[netifaces.AF_INET6]:
                        ip6 = addr.get("addr", "")
                        if ip6 and ip6.startswith("fe80::"):
                            info["ipv6"] = ip6.split("%")[0]
                            break

            # Status
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect((info.get("ip", "8.8.8.8"), 80))
                info["is_up"] = True
                s.close()
            except Exception:
                info["is_up"] = False

            # Speed (from netifaces)
            speed = ""
            try:
                if isinstance(details, dict) and "speed" in details:
                    speed = str(details["speed"])
            except Exception:
                pass
            info["speed"] = speed

            # Extra details
            info["mtu"] = ""
            try:
                if isinstance(details, dict) and "mtu" in details:
                    info["mtu"] = str(details["mtu"])
            except Exception:
                pass

            if "ip" in info or "ipv6" in info:
                interfaces.append(info)

    except ImportError:
        # Fallback: use /sys/class/net and socket
        import os
        import glob
        import fcntl
        import struct
        import socket

        sys_net = "/sys/class/net/*"
        for path in glob.glob(sys_net):
            iface_name = os.path.basename(path)
            info = {"name": iface_name}

            # Status
            try:
                with open(f"{path}/operstate") as f:
                    state = f.read().strip()
                    info["is_up"] = state in ("up", "unknown")
            except Exception:
                info["is_up"] = False

            # MAC
            try:
                with open(f"{path}/address") as f:
                    info["mac"] = f.read().strip()
            except Exception:
                pass

            # Speed
            try:
                with open(f"{path}/speed") as f:
                    speed = f.read().strip()
                    info["speed"] = f"{speed} Mbps" if speed and speed != "-1" else ""
            except Exception:
                pass

            # MTU
            try:
                with open(f"{path}/mtu") as f:
                    info["mtu"] = f.read().strip()
            except Exception:
                pass

            # IP address via ip addr (most reliable)
            try:
                import subprocess
                result = subprocess.run(
                    ["ip", "-4", "addr", "show", iface_name],
                    capture_output=True, text=True, timeout=3
                )
                for line in result.stdout.splitlines():
                    if "inet " in line:
                        parts = line.strip().split()
                        for i, p in enumerate(parts):
                            if p == "inet":
                                info["ip"] = parts[i + 1].split("/")[0]
                                info["netmask"] = parts[i + 1].split("/")[1] if "/" in parts[i + 1] else ""
                                break
                        if "ip" in info:
                            break
            except Exception:
                pass

            if "ip" not in info:
                # Fallback to socket ioctl
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    import fcntl
                    import struct
                    SIOCGIFADDR = 0x8915
                    try:
                        ifr = struct.pack("16sI", iface_name.encode()[:15], 0)
                        result = fcntl.ioctl(s.fileno(), SIOCGIFADDR, ifr)
                        ip = socket.inet_ntoa(result[20:24])
                        if ip:
                            info["ip"] = ip
                    except Exception:
                        pass
                    s.close()
                except Exception:
                    pass

            if "ip" in info or info.get("is_up"):
                interfaces.append(info)

    if is_json_mode():
        print_json(interfaces)
    else:
        print_interface_info(interfaces)

    return interfaces


async def interface_detail(iface: str, output: str = "rich") -> dict | None:
    """Show detailed info for a specific interface."""
    set_output_mode(output)

    interfaces = await list_interfaces(output="json" if is_json_mode() else "rich")
    for iface_info in interfaces:
        if iface_info.get("name") == iface:
            return iface_info

    console.print(f"[red]Interface '{iface}' not found.[/]")
    return None
