"""Juniper Junos command parser."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Interface:
    """Network interface information."""
    name: str
    admin_status: str  # up, down
    oper_status: str   # up, down
    addresses: list[str] = field(default_factory=list)
    description: str = ""
    speed: str = ""
    link_mode: str = ""


@dataclass
class Route:
    """Routing table entry."""
    destination: str
    next_hop: str
    interface: str
    protocol: str
    preference: int = 0
    metric: int = 0


@dataclass
class Vlan:
    """VLAN information."""
    vlan_id: int
    name: str
    interfaces: list[str] = field(default_factory=list)


class JuniperParser:
    """Parser for Juniper Junos commands."""

    @staticmethod
    def parse_version(output: str) -> dict:
        """Parse 'show version' output."""
        info = {}

        # Junos version
        match = re.search(r'JUNOS\s+Software Release\s+\[(\S+)\]', output)
        if match:
            info["junos_version"] = match.group(1)

        # Hostname
        match = re.search(r'Hostname:\s+(\S+)', output)
        if match:
            info["hostname"] = match.group(1)

        # Model
        match = re.search(r'Model:\s+(\S+)', output)
        if match:
            info["model"] = match.group(1)

        # Serial
        match = re.search(r'Serial number:\s+(\S+)', output)
        if match:
            info["serial"] = match.group(1)

        # Boot time
        match = re.search(r'System boot:\s+(.+)', output)
        if match:
            info["boot_time"] = match.group(1).strip()

        # Uptime
        match = re.search(r'Uptime:\s+(.+)', output)
        if match:
            info["uptime"] = match.group(1).strip()

        return info

    @staticmethod
    def parse_interfaces_terse(output: str) -> list[Interface]:
        """Parse 'show interfaces terse' output."""
        interfaces = []
        lines = output.strip().split("\n")

        current_iface = None
        for line in lines:
            # Match interface header like: ge-0/0/0               up    down
            match = re.match(r'^(\S+)\s+(up|down)\s+(up|down)', line)
            if match:
                current_iface = Interface(
                    name=match.group(1),
                    admin_status=match.group(2),
                    oper_status=match.group(3),
                )
                interfaces.append(current_iface)

            # Match IP address line
            elif current_iface and line.strip().startswith(current_iface.name):
                addr_match = re.search(r'(\d+\.\d+\.\d+\.\d+/\d+)', line)
                if addr_match:
                    current_iface.addresses.append(addr_match.group(1))

        return interfaces

    @staticmethod
    def parse_interfaces_detail(output: str) -> list[Interface]:
        """Parse 'show interfaces detail' output."""
        interfaces = []
        lines = output.strip().split("\n")

        current_iface = None
        for line in lines:
            # Match interface header
            match = re.match(r'^(\S+):\s+', line)
            if match:
                if current_iface:
                    interfaces.append(current_iface)
                current_iface = Interface(
                    name=match.group(1),
                    admin_status="unknown",
                    oper_status="unknown",
                )

            if current_iface:
                # Admin status
                if "Administrative state:" in line:
                    if "up" in line.lower():
                        current_iface.admin_status = "up"
                    else:
                        current_iface.admin_status = "down"

                # Operational status
                if "Physical link is" in line:
                    if "Up" in line:
                        current_iface.oper_status = "up"
                    else:
                        current_iface.oper_status = "down"

                # Speed
                speed_match = re.search(r'Speed:\s+(\S+)', line)
                if speed_match:
                    current_iface.speed = speed_match.group(1)

                # Description
                desc_match = re.search(r'Description:\s+(.+)', line)
                if desc_match:
                    current_iface.description = desc_match.group(1).strip()

        if current_iface:
            interfaces.append(current_iface)

        return interfaces

    @staticmethod
    def parse_routes(output: str) -> list[Route]:
        """Parse 'show route' output."""
        routes = []
        lines = output.strip().split("\n")

        current_dest = None
        for line in lines:
            # Match destination like: 192.168.1.0/24
            dest_match = re.match(r'^(\d+\.\d+\.\d+\.\d+/\d+)', line)
            if dest_match:
                current_dest = dest_match.group(1)

            # Match next hop
            if current_dest:
                hop_match = re.search(r'via\s+(\S+)', line)
                if hop_match:
                    routes.append(Route(
                        destination=current_dest,
                        next_hop=hop_match.group(1),
                        interface="",
                        protocol="",
                    ))
                    current_dest = None

        return routes

    @staticmethod
    def parse_vlans(output: str) -> list[Vlan]:
        """Parse 'show vlans' output."""
        vlans = []
        lines = output.strip().split("\n")

        current_vlan = None
        for line in lines:
            # Match VLAN header like: VLAN ID: 100
            vlan_match = re.search(r'VLAN ID:\s+(\d+)', line)
            if vlan_match:
                if current_vlan:
                    vlans.append(current_vlan)
                current_vlan = Vlan(
                    vlan_id=int(vlan_match.group(1)),
                    name="",
                )

            if current_vlan:
                # Name
                name_match = re.search(r'VLAN Name:\s+(\S+)', line)
                if name_match:
                    current_vlan.name = name_match.group(1)

                # Interfaces
                iface_match = re.search(r'Interfaces:\s+(.+)', line)
                if iface_match:
                    ifaces = [i.strip() for i in iface_match.group(1).split(",")]
                    current_vlan.interfaces.extend(ifaces)

        if current_vlan:
            vlans.append(current_vlan)

        return vlans

    @staticmethod
    def parse_chassis_hardware(output: str) -> dict:
        """Parse 'show chassis hardware' output."""
        hardware = {
            "chassis": {},
            "modules": [],
        }

        lines = output.strip().split("\n")

        for line in lines:
            # Chassis serial
            match = re.search(r'Chassis\s+(\S+)\s+(\S+)', line)
            if match:
                hardware["chassis"]["model"] = match.group(1)
                hardware["chassis"]["serial"] = match.group(2)

            # Modules
            match = re.search(r'^\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', line)
            if match:
                hardware["modules"].append({
                    "name": match.group(1),
                    "model": match.group(2),
                    "serial": match.group(3),
                    "version": match.group(4),
                })

        return hardware
