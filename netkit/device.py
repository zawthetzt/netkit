"""
Network device connectivity — SSH and console connections to Cisco NX-OS and Juniper Junos.

Usage:
    netkit device 192.168.1.1 --vendor cisco --cmd "show version"
    netkit device /dev/ttyUSB0 --vendor juniper --console --interactive
"""

import asyncio
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

console = Console()


@dataclass
class DeviceConfig:
    """Configuration for device connection."""
    host: str
    vendor: str  # cisco, juniper
    username: str = "admin"
    password: str = ""
    port: int = 22
    console: bool = False
    baud: int = 9600
    timeout: int = 30
    secret: str = ""  # Enable password


@dataclass
class CommandResult:
    """Result of a command execution."""
    command: str
    output: str
    success: bool
    error: Optional[str] = None


def detect_vendor_from_prompt(prompt: str) -> str:
    """Detect vendor from CLI prompt."""
    prompt_lower = prompt.lower()
    if any(x in prompt_lower for x in ["nexus", "nx-os", "switch#"]):
        return "cisco"
    elif any(x in prompt_lower for x in ["juniper", "@", ">"]):
        return "juniper"
    return "unknown"


def parse_cisco_interfaces(output: str) -> list[dict]:
    """Parse Cisco 'show interface brief' output."""
    interfaces = []
    lines = output.strip().split("\n")

    for line in lines:
        # Match interface lines like: Eth1/1      1     eth  access up      10G(D) --
        match = re.match(
            r'^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(up|down|admin-down)\s+(\S+)',
            line
        )
        if match:
            interfaces.append({
                "interface": match.group(1),
                "vlan": match.group(2),
                "type": match.group(3),
                "mode": match.group(4),
                "status": match.group(5),
                "speed": match.group(6),
            })

    return interfaces


def parse_cisco_version(output: str) -> dict:
    """Parse Cisco 'show version' output."""
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

    return info


def parse_juniper_interfaces(output: str) -> list[dict]:
    """Parse Juniper 'show interfaces terse' output."""
    interfaces = []
    lines = output.strip().split("\n")

    current_iface = None
    for line in lines:
        # Match interface header like: ge-0/0/0               up    down
        match = re.match(r'^(\S+)\s+(up|down)\s+(up|down)', line)
        if match:
            current_iface = {
                "interface": match.group(1),
                "admin_status": match.group(2),
                "oper_status": match.group(3),
                "addresses": []
            }
            interfaces.append(current_iface)

        # Match IP address line like: ge-0/0/0.0     192.168.1.1/24
        elif current_iface and line.strip().startswith(current_iface["interface"]):
            addr_match = re.search(r'(\d+\.\d+\.\d+\.\d+/\d+)', line)
            if addr_match:
                current_iface["addresses"].append(addr_match.group(1))

    return interfaces


def parse_juniper_version(output: str) -> dict:
    """Parse Juniper 'show version' output."""
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

    # Uptime
    match = re.search(r'System boot:\s+(.+)', output)
    if match:
        info["boot_time"] = match.group(1).strip()

    return info


class SSHDevice:
    """SSH connection to network device."""

    def __init__(self, config: DeviceConfig):
        self.config = config
        self.connection = None

    async def connect(self) -> bool:
        """Establish SSH connection."""
        try:
            from netmiko import ConnectHandler

            device_type_map = {
                "cisco": "cisco_nxos",
                "juniper": "juniper_junos",
            }

            device_params = {
                "device_type": device_type_map.get(self.config.vendor, "cisco_ios"),
                "host": self.config.host,
                "username": self.config.username,
                "password": self.config.password,
                "port": self.config.port,
                "timeout": self.config.timeout,
            }

            if self.config.secret:
                device_params["secret"] = self.config.secret

            self.connection = await asyncio.to_thread(
                ConnectHandler, **device_params
            )
            return True

        except ImportError:
            console.print("[red]netmiko not installed. Run: pip install 'netkit[device]'[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Connection failed: {e}[/red]")
            return False

    async def execute(self, command: str) -> CommandResult:
        """Execute a command on the device."""
        if not self.connection:
            return CommandResult(
                command=command,
                output="",
                success=False,
                error="Not connected"
            )

        try:
            output = await asyncio.to_thread(
                self.connection.send_command, command
            )
            return CommandResult(
                command=command,
                output=output,
                success=True
            )
        except Exception as e:
            return CommandResult(
                command=command,
                output="",
                success=False,
                error=str(e)
            )

    def disconnect(self):
        """Close SSH connection."""
        if self.connection:
            self.connection.disconnect()


class ConsoleDevice:
    """Console (serial) connection to network device."""

    def __init__(self, config: DeviceConfig):
        self.config = config
        self.serial = None

    async def connect(self) -> bool:
        """Establish serial connection."""
        try:
            import serial_asyncio

            self.serial = await serial_asyncio.open_serial_connection(
                url=self.config.host,
                baudrate=self.config.baud
            )
            return True

        except ImportError:
            console.print("[red]pyserial not installed. Run: pip install 'netkit[device]'[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Console connection failed: {e}[/red]")
            return False

    async def execute(self, command: str) -> CommandResult:
        """Execute a command via console."""
        if not self.serial:
            return CommandResult(
                command=command,
                output="",
                success=False,
                error="Not connected"
            )

        try:
            # Send command
            self.serial.write(f"{command}\n".encode())
            await asyncio.sleep(0.5)

            # Read output
            output = ""
            while self.serial.in_waiting:
                data = await self.serial.read(1024)
                output += data.decode(errors="ignore")

            return CommandResult(
                command=command,
                output=output,
                success=True
            )
        except Exception as e:
            return CommandResult(
                command=command,
                output="",
                success=False,
                error=str(e)
            )

    def disconnect(self):
        """Close serial connection."""
        if self.serial:
            self.serial.close()


async def connect_device(config: DeviceConfig) -> SSHDevice | ConsoleDevice:
    """Connect to a network device."""
    if config.console:
        device = ConsoleDevice(config)
    else:
        device = SSHDevice(config)

    await device.connect()
    return device


async def run_command(device: SSHDevice | ConsoleDevice, command: str, vendor: str) -> dict:
    """Run a command and parse output."""
    result = await device.execute(command)

    if not result.success:
        return {
            "command": command,
            "error": result.error,
            "raw": result.output
        }

    # Parse based on vendor and command
    parsed = {"command": command, "raw": result.output}

    if vendor == "cisco":
        if "interface brief" in command.lower():
            parsed["interfaces"] = parse_cisco_interfaces(result.output)
        elif "version" in command.lower():
            parsed["version"] = parse_cisco_version(result.output)
    elif vendor == "juniper":
        if "interfaces terse" in command.lower():
            parsed["interfaces"] = parse_juniper_interfaces(result.output)
        elif "version" in command.lower():
            parsed["version"] = parse_juniper_version(result.output)

    return parsed


async def interactive_session(device: SSHDevice | ConsoleDevice, vendor: str):
    """Start interactive CLI session."""
    console.print(Panel(
        f"[bold cyan]Interactive {vendor.upper()} Session[/bold cyan]\n"
        f"Type 'exit' or 'quit' to disconnect",
        border_style="cyan"
    ))

    while True:
        try:
            command = Prompt.ask(f"[bold green]{vendor}[/]")

            if command.lower() in ["exit", "quit", "q"]:
                break

            if not command.strip():
                continue

            result = await run_command(device, command, vendor)

            if "error" in result:
                console.print(f"[red]Error: {result['error']}[/red]")
            else:
                console.print(result["raw"])

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    device.disconnect()
    console.print("[yellow]Disconnected.[/yellow]")


async def device_connect(
    host: str,
    vendor: str,
    username: str = "admin",
    password: str = "",
    port: int = 22,
    console_mode: bool = False,
    baud: int = 9600,
    command: Optional[str] = None,
    interactive: bool = False,
    output: str = "rich",
) -> dict:
    """Main device connection function."""
    config = DeviceConfig(
        host=host,
        vendor=vendor,
        username=username,
        password=password,
        port=port,
        console=console_mode,
        baud=baud,
    )

    console.print(f"[cyan]Connecting to {host} ({vendor})...[/cyan]")

    device = await connect_device(config)

    if interactive:
        await interactive_session(device, vendor)
        return {"status": "interactive_session_ended"}

    if command:
        result = await run_command(device, command, vendor)
        device.disconnect()

        if output == "json":
            print(json.dumps(result, indent=2))
        else:
            if "error" in result:
                console.print(f"[red]Error: {result['error']}[/red]")
            else:
                console.print(Panel(result["raw"], title=command))

        return result

    # Default: show device info
    if vendor == "cisco":
        result = await run_command(device, "show version", vendor)
    else:
        result = await run_command(device, "show version", vendor)

    device.disconnect()

    if output == "json":
        print(json.dumps(result, indent=2))
    else:
        console.print(Panel(result.get("raw", ""), title="Device Info"))

    return result
