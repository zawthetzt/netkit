"""
Device profiles — save and load device configurations.

Usage:
    netkit save nexus1 192.168.1.1 --cisco -u admin
    netkit nexus1 "show version"
    netkit devices
"""

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()

# Config file location
CONFIG_DIR = Path.home() / ".netkit"
CONFIG_FILE = CONFIG_DIR / "devices.json"


@dataclass
class DeviceProfile:
    """Saved device configuration."""
    name: str
    host: str
    vendor: str  # cisco, juniper
    username: str = "admin"
    password: str = ""
    port: int = 22
    console: bool = False
    baud: int = 9600
    secret: str = ""  # Enable password
    description: str = ""


class ProfileManager:
    """Manage device profiles."""

    def __init__(self):
        self.profiles: dict[str, DeviceProfile] = {}
        self._load()

    def _load(self):
        """Load profiles from config file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    for name, profile_data in data.items():
                        self.profiles[name] = DeviceProfile(**profile_data)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load profiles: {e}[/yellow]")

    def _save(self):
        """Save profiles to config file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {name: asdict(profile) for name, profile in self.profiles.items()}
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def save_profile(self, profile: DeviceProfile) -> bool:
        """Save a device profile."""
        self.profiles[profile.name] = profile
        self._save()
        return True

    def get_profile(self, name: str) -> Optional[DeviceProfile]:
        """Get a device profile by name."""
        return self.profiles.get(name)

    def delete_profile(self, name: str) -> bool:
        """Delete a device profile."""
        if name in self.profiles:
            del self.profiles[name]
            self._save()
            return True
        return False

    def list_profiles(self) -> list[DeviceProfile]:
        """List all saved profiles."""
        return list(self.profiles.values())

    def search_profiles(self, query: str) -> list[DeviceProfile]:
        """Search profiles by name, host, or vendor."""
        query = query.lower()
        results = []
        for profile in self.profiles.values():
            if (query in profile.name.lower() or
                query in profile.host.lower() or
                query in profile.vendor.lower()):
                results.append(profile)
        return results


def display_profiles(profiles: list[DeviceProfile], output_json: bool = False):
    """Display device profiles in a table."""
    if output_json:
        print(json.dumps([asdict(p) for p in profiles], indent=2))
        return

    if not profiles:
        console.print("[yellow]No saved devices. Use 'netkit save' to add one.[/yellow]")
        return

    table = Table(title="📱 Saved Devices")
    table.add_column("NAME", style="cyan", min_width=12)
    table.add_column("HOST", style="green", min_width=15)
    table.add_column("VENDOR", style="yellow", min_width=8)
    table.add_column("USER", style="blue", min_width=10)
    table.add_column("TYPE", style="magenta", min_width=8)
    table.add_column("DESCRIPTION", style="dim")

    for p in profiles:
        conn_type = "Console" if p.console else "SSH"
        table.add_row(
            p.name,
            p.host,
            p.vendor,
            p.username,
            conn_type,
            p.description or "-"
        )

    console.print(table)


def parse_vendor(vendor_str: str) -> str:
    """Parse vendor string to normalized form."""
    vendor_str = vendor_str.lower().strip()
    if vendor_str in ["cisco", "nxos", "nx-os", "nexus"]:
        return "cisco"
    elif vendor_str in ["juniper", "junos", "junos"]:
        return "juniper"
    return vendor_str


def detect_vendor_from_host(host: str) -> str:
    """Try to detect vendor from hostname patterns."""
    host_lower = host.lower()
    if any(x in host_lower for x in ["nexus", "nx", "cisco"]):
        return "cisco"
    elif any(x in host_lower for x in ["juniper", "jun", "srx", "ex", "qfx"]):
        return "juniper"
    return "unknown"
