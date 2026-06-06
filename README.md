# netkit 🧰

**A full network engineer's CLI toolkit** — ping, port scan, DNS, traceroute, whois, HTTP probing, subnet calculation, packet capture, and more.

Built with Python, using async I/O for fast scanning and Rich for beautiful terminal output.

## Features

| Command | Description |
|---------|-------------|
| `netkit ping` | ICMP ping sweep — single host or CIDR subnet |
| `netkit scan` | Port scanner — TCP connect, SYN scan, UDP scan |
| `netkit service` | Service & banner detection from open ports |
| `netkit trace` | Traceroute (ICMP / UDP) |
| `netkit dns` | DNS toolkit — A/AAAA/MX/NS/TXT/SOA/CAA lookups, reverse DNS, zone transfer |
| `netkit whois` | Domain & IP whois lookups |
| `netkit http` | HTTP probe — status, headers, server, TLS, title |
| `netkit subnet` | Subnet calculator & live host scanning |
| `netkit capture` | Live packet capture with BPF filtering |
| `netkit interfaces` | Show local network interface info |

## Quick Start

```bash
# Install
pip install .

# Ping sweep
netkit ping 8.8.8.8
netkit ping 192.168.1.0/24 --count 1

# Port scanning
netkit scan 192.168.1.1 -p 22,80,443
netkit scan 10.0.0.0/24 --ports 1-1024 --syn

# DNS lookups
netkit dns example.com
netkit dns example.com --types A,MX,NS
netkit dns 8.8.8.8 --reverse

# Traceroute
netkit trace 8.8.8.8
netkit trace example.com -m 20

# Subnet calculator
netkit subnet 192.168.1.0/24
netkit subnet 10.0.0.0/8 --scan

# HTTP probe
netkit http example.com
netkit http https://example.com/api --method HEAD

# Whois lookup
netkit whois example.com

# Packet capture (requires root / scapy)
sudo netkit capture -c 50 -f "tcp port 80"

# Machine-readable output
netkit scan 10.0.0.1 -p 22,80 -o json | jq .
```

## JSON Output

Every command supports `--output json` (or `-o json`) for machine-readable output.

## Requirements

- Python 3.11+
- Some features (`--syn` scan, packet capture) require **root privileges** for raw sockets
- Scapy auto-falls back to system commands when raw sockets are unavailable

## Installation

```bash
# From source
git clone <repo> && cd netkit
pip install .

# Development install
pip install -e .
```
