"""Cisco NX-OS command parser."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Interface:
    """Network interface information."""
    name: str
    status: str  # up, down, admin-down
    vlan: str = ""
    mode: str = ""
    speed: str = ""
    type: str = ""
    ip_address: str = ""
    description: str = ""


@dataclass
class Route:
    """Routing table entry."""
    prefix: str
    next_hop: str
    interface: str
    protocol: str
    metric: int = 0
    admin_distance: int = 0


@dataclass
class Vlan:
    """VLAN information."""
    vlan_id: int
    name: str
    status: str
    ports: list[str]


class CiscoParser:
    """Parser for Cisco NX-OS commands."""

    @staticmethod
    def parse_version(output: str) -> dict:
        """Parse 'show version' output."""
        info = {}

        # NX-OS version
        match = re.search(r'NXOS:\s+version\s+(\S+)', output, re.IGNORECASE)
        if match:
            info["nxos_version"] = match.group(1)

        # System version
        match = re.search(r'system:\s+version\s+(\S+)', output, re.IGNORECASE)
        if match:
            info["system_version"] = match.group(1)

        # Hostname
        match = re.search(r'Device name:\s+(\S+)', output, re.IGNORECASE)
        if match:
            info["hostname"] = match.group(1)

        # Uptime
        match = re.search(r'Kernel uptime is:\s+(.+)', output, re.IGNORECASE)
        if match:
            info["uptime"] = match.group(1).strip()

        # Model
        match = re.search(r'cisco\s+(\S+)\s+', output, re.IGNORECASE)
        if match:
            info["model"] = match.group(1)

        # Serial
        match = re.search(r'serial number:\s+(\S+)', output, re.IGNORECASE)
        if match:
            info["serial"] = match.group(1)

        # Memory
        match = re.search(r'(\d+)\s+kB\s+memory', output, re.IGNORECASE)
        if match:
            info["memory_kb"] = int(match.group(1))

        return info

    @staticmethod
    def parse_interfaces_brief(output: str) -> list[Interface]:
        """Parse 'show interface brief' output."""
        interfaces = []
        lines = output.strip().split("\n")

        for line in lines:
            # Match interface lines
            # Example: Eth1/1      1     eth  access up      10G(D) --
            match = re.match(
                r'^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(up|down|admin-down)\s+(\S+)',
                line
            )
            if match:
                interfaces.append(Interface(
                    name=match.group(1),
                    vlan=match.group(2),
                    type=match.group(3),
                    mode=match.group(4),
                    status=match.group(5),
                    speed=match.group(6),
                ))

        return interfaces

    @staticmethod
    def parse_ip_interface_brief(output: str) -> list[Interface]:
        """Parse 'show ip interface brief' output."""
        interfaces = []
        lines = output.strip().split("\n")

        for line in lines:
            # Match: mgmt0       192.168.1.1     255.255.255.0   up      up
            match = re.match(
                r'^(\S+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+(up|down|admin-down)\s+(up|down)',
                line
            )
            if match:
                interfaces.append(Interface(
                    name=match.group(1),
                    ip_address=match.group(2),
                    status=match.group(4),
                ))

        return interfaces

    @staticmethod
    def parse_routes(output: str) -> list[Route]:
        """Parse 'show ip route' output."""
        routes = []
        lines = output.strip().split("\n")

        for line in lines:
            # Match: 192.168.1.0/24, ubest/mbest: 1/0
            match = re.match(r'^(\d+\.\d+\.\d+\.\d+/\d+)', line)
            if match:
                prefix = match.group(1)

                # Look for next hop in following lines
                next_line = lines[lines.index(line) + 1] if lines.index(line) + 1 < len(lines) else ""
                hop_match = re.search(r'via\s+(\d+\.\d+\.\d+\.\d+)', next_line)

                if hop_match:
                    routes.append(Route(
                        prefix=prefix,
                        next_hop=hop_match.group(1),
                        interface="",
                        protocol="",
                    ))

        return routes

    @staticmethod
    def parse_vlans(output: str) -> list[Vlan]:
        """Parse 'show vlan' output."""
        vlans = []
        lines = output.strip().split("\n")

        for line in lines:
            # Match: 100   VLAN0100                         active    Eth1/1, Eth1/2
            match = re.match(r'^(\d+)\s+(\S+)\s+(active|suspended)\s+(.*)', line)
            if match:
                vlan_id = int(match.group(1))
                name = match.group(2)
                status = match.group(3)
                ports = [p.strip() for p in match.group(4).split(",") if p.strip()]

                vlans.append(Vlan(
                    vlan_id=vlan_id,
                    name=name,
                    status=status,
                    ports=ports,
                ))

        return vlans

    @staticmethod
    def parse_inventory(output: str) -> list[dict]:
        """Parse 'show inventory' output."""
        inventory = []
        lines = output.strip().split("\n")

        current_item = {}
        for line in lines:
            if line.startswith("NAME:"):
                if current_item:
                    inventory.append(current_item)
                current_item = {"name": line.split('"')[1] if '"' in line else ""}
            elif "DESCR:" in line:
                current_item["description"] = line.split('"')[1] if '"' in line else ""
            elif "PID:" in line:
                match = re.search(r'PID:\s+(\S+)', line)
                if match:
                    current_item["pid"] = match.group(1)
            elif "SN:" in line:
                match = re.search(r'SN:\s+(\S+)', line)
                if match:
                    current_item["serial"] = match.group(1)

        if current_item:
            inventory.append(current_item)

        return inventory
