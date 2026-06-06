<div align="center">
  <h1>netkit 🧰</h1>
  <p><strong>One CLI to ping, scan, trace, query, and probe your network.</strong></p>
  <p>Replace <code>nmap</code> · <code>dig</code> · <code>whois</code> · <code>ping</code> · <code>traceroute</code> · <code>curl</code> · <code>ifconfig</code> · <code>tcpdump</code> — with one tool.</p>

  <!-- Badges -->
  <p>
    <a href="https://pypi.org/project/netkit/"><img src="https://img.shields.io/pypi/v/netkit?style=flat&logo=pypi&color=blue" alt="PyPI"></a>
    <a href="https://github.com/zawthetzt/netkit"><img src="https://img.shields.io/github/stars/zawthetzt/netkit?style=flat&logo=github" alt="GitHub Stars"></a>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/zawthetzt/netkit?style=flat" alt="License"></a>
    <img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python" alt="Python 3.11+">
    <a href="https://github.com/zawthetzt/netkit/actions"><img src="https://img.shields.io/github/actions/workflow/status/zawthetzt/netkit/ci.yml?style=flat&logo=githubactions" alt="CI"></a>
  </p>

  <!-- Demo GIF placeholder -->
  <p>
    <a href="https://asciinema.org/a/EXAMPLE">
      <img src="https://img.shields.io/badge/📺%20Watch%20Demo-000?style=for-the-badge" alt="Demo">
    </a>
  </p>

  <pre><code style="background:#1e1e2e; color:#cdd6f4; padding:12px; border-radius:8px; display:inline-block; text-align:left;">
$ netkit scan 10.0.0.1 -p 22,80,443,3306
┌─────────────── Open Ports — 10.0.0.1 ───────────────┐
│ Port  │ Proto │ State │ Service    │ Banner         │
├───────┼───────┼───────┼────────────┼────────────────┤
│ 22    │ tcp   │ open  │ SSH        │ OpenSSH_9.6    │
│ 80    │ tcp   │ open  │ HTTP       │ nginx/1.24     │
│ 443   │ tcp   │ open  │ HTTPS      │ [TLS OK]       │
│ 3306  │ tcp   │ open  │ MySQL      │ 8.0.36         │
└───────┴───────┴───────┴────────────┴────────────────┘

$ netkit dns example.com --types A,MX,NS -o json | jq '...'
  </code></pre>
</div>

---

## 🚀 Why netkit?

Every network engineer knows the drill: **switch between 10 tools** to diagnose one problem. `ping` here, `nmap` there, `dig` for DNS, `whois` for domains, `curl` for HTTP, `tcpdump` for packets…

**netkit** replaces all of them with **one CLI, one syntax, one output format** — and it's all async, so scans finish in seconds, not minutes.

### 🔁 One-Liner Comparison

| Task | Traditional Tool | `netkit` | Why netkit wins |
|------|-----------------|----------|-----------------|
| Ping sweep | `nmap -sn 192.168.1.0/24` | `netkit ping 192.168.1.0/24` | Built‑in CIDR, async, colored output |
| Port scan | `nmap -p 1-1000 10.0.0.1` | `netkit scan 10.0.0.1 -p 1-1000` | Same power, no flags to memorize |
| SYN scan | `nmap -sS 10.0.0.1` | `netkit scan 10.0.0.1 --syn` | Streamlined option name |
| DNS lookup | `dig A example.com` | `netkit dns example.com --types A` | Type‑aware tables, multi‑record |
| Reverse DNS | `dig -x 8.8.8.8` | `netkit dns 8.8.8.8 --reverse` | No PTR syntax gymnastics |
| Zone transfer | `dig AXFR example.com @ns1` | `netkit dns example.com --zone` | Auto‑discovers NS, tries all |
| DNS + WHOIS | two commands | `netkit dns X && netkit whois X` | Same tool, same output style |
| Whois | `whois example.com` | `netkit whois example.com` | Structured result, JSON mode |
| Traceroute | `traceroute 8.8.8.8` | `netkit trace 8.8.8.8` | Async, auto ICMP/UDP fallback |
| HTTP probe | `curl -I https://example.com` | `netkit http example.com` | +TLS info, +title extraction |
| Subnet calc | `ipcalc 10.0.0.0/24` | `netkit subnet 10.0.0.0/24` | +live host scan with `--scan` |
| Packet capture | `tcpdump -c 20 -i eth0` | `netkit capture -c 20 -i eth0` | Same BPF, human summaries |
| Interface info | `ip addr` / `ifconfig` | `netkit interfaces` | Parseable, JSON output |
| **JSON output** | each tool has its own format | `... -o json` | Consistent schema across every command |

---

## 📦 Install

```bash
pip install netkit
```

Or from source:

```bash
git clone https://github.com/zawthetzt/netkit.git
cd netkit
pip install .
```

> **Requirements:** Python 3.11+
> SYN scan & packet capture need root (raw sockets) — auto-falls back to connect scan & system tools.

---

## 🧰 Commands at a Glance

| Command | Description | Example |
|---------|-------------|---------|
| `netkit ping` | ICMP ping sweep — one host or a whole subnet | `netkit ping 10.0.0.0/24` |
| `netkit scan` | TCP connect / SYN / UDP port scanner | `netkit scan 10.0.0.1 -p 22,80,443` |
| `netkit service` | Banner grab + service fingerprinting | `netkit service 10.0.0.1` |
| `netkit trace` | ICMP / UDP traceroute | `netkit trace 8.8.8.8` |
| `netkit dns` | A · AAAA · MX · NS · TXT · SOA · CAA · CNAME + reverse + zone transfer | `netkit dns example.com --types A,MX,NS` |
| `netkit whois` | Domain & IP whois lookups | `netkit whois example.com` |
| `netkit http` | HTTP probe — status, headers, server, TLS, page title | `netkit http example.com` |
| `netkit subnet` | Subnet calculator + live host discovery | `netkit subnet 192.168.1.0/24` |
| `netkit capture` | Live packet capture with BPF filters | `netkit capture -c 50 -f "tcp port 80"` |
| `netkit interfaces` | List local network interfaces and IPs | `netkit interfaces` |

---

## 🎯 Quick Examples

```bash
# Ping sweep a subnet
netkit ping 192.168.1.0/24 --count 2

# Scan common ports on a host
netkit scan 10.0.0.1

# Full DNS investigation
netkit dns example.com
netkit dns 8.8.8.8 --reverse
netkit dns example.com --zone                 # Try AXFR

# HTTP + WHOIS in one workflow
netkit http example.com -o json | jq '.status, .server'
netkit whois example.com

# Subnet planning
netkit subnet 10.0.0.0/24
netkit subnet 10.0.0.0/24 --scan              # Find live hosts

# Grab service banners
netkit service 10.0.0.1 -p 22,80,443,3306,6379

# Trace a route
netkit trace github.com

# Machine-readable everything
netkit scan 10.0.0.0/24 -p 22,80 -o json > scan.json
```

---

## 🔧 Advanced Usage

### JSON output (every command supports it)

```bash
netkit scan 10.0.0.1 -p 1-1000 -o json | jq '.[].ports[] | select(.state == "open")'
```

### CIDR & range targets (any command)

```bash
netkit ping 10.0.0.0/28
netkit scan 192.168.1.100-250 -p 22
netkit scan 10.0.0.1,50 -p 80,443          # shorthand range
```

### Graceful degradation

- **SYN scan** → falls back to TCP connect without root
- **Scapy ping** → falls back to system `ping`
- **Scapy traceroute** → falls back to system `traceroute`
- No silent failures: you always see what's happening

---

## 🏗 Architecture

Built with modern Python:

| Library | Role |
|---------|------|
| [Typer](https://typer.tiangolo.com/) | CLI framework |
| [Rich](https://rich.readthedocs.io/) | Terminal tables, colors, progress bars |
| [Scapy](https://scapy.net/) | Raw packet crafting (ICMP, SYN, UDP, capture) |
| [httpx](https://www.python-httpx.org/) | Async HTTP probing |
| [dnspython](https://www.dnspython.org/) | DNS queries & zone transfers |
| [python-whois](https://pypi.org/project/python-whois/) | Domain/IP whois |
| **asyncio** | Async concurrency for fast scanning |

---

## 🗺 Roadmap

- [ ] **PyPI release** — `pip install netkit` (coming soon)
- [ ] **Nmap XML/CSV export**
- [ ] **Concurrent multi-host traceroute**
- [ ] **Web dashboard** (read-only mode)
- [ ] **Plugin system** for custom probes
- [ ] **IPv6 deep support**

Ideas? Open an [issue](https://github.com/zawthetzt/netkit/issues)!

---

## 🤝 Contributing

Contributions are welcome! See a bug? Want a feature?

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push (`git push origin feature/my-feature`)
5. Open a Pull Request

## 📄 License

MIT — free to use, modify, and distribute.

---

<div align="center">
  <sub>Built with ☕ by <a href="https://github.com/zawthetzt">zawthetzt</a></sub>
</div>
