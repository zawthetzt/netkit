---
marp: true
theme: default
paginate: true
auto: 20
---

# netkit 🧰
## One CLI for All Network Tools

**Replace 10+ tools with one command**

Ping · Scan · DNS · Whois · Traceroute · HTTP · Subnet · Capture

---

# The Problem

Network engineers switch between **10+ tools** daily:

- `ping` for connectivity
- `nmap` for port scanning
- `dig` for DNS lookups
- `whois` for domain info
- `traceroute` for routing
- `curl` for HTTP checks
- `tcpdump` for packets

**Context switching kills productivity**

---

# The Solution

```bash
netkit ping 192.168.1.0/24    # Ping sweep
netkit scan 10.0.0.1 -p 1-1000  # Port scan
netkit dns example.com         # DNS lookup
netkit whois example.com       # Domain info
netkit trace 8.8.8.8          # Traceroute
netkit http example.com        # HTTP probe
```

**One syntax. One output format. Async execution.**

---

# Built with AI

### Claude Code Integration

- **MCP Servers**: GitHub, filesystem, web search
- **Skills**: Reusable network scan patterns
- **Agents**: Automated diagnostics

### Development Speed

- 10x faster prototyping
- Automated testing & documentation
- Real-time code review

---

# Key Features

| Feature | Traditional | netkit |
|---------|-------------|--------|
| Ping sweep | `nmap -sn` | `netkit ping` |
| Port scan | `nmap -p` | `netkit scan` |
| DNS lookup | `dig` | `netkit dns` |
| JSON output | Each tool different | Consistent |
| Async | Manual parallel | Built-in |

**Same power. Less syntax. Faster results.**

---

# Try It Now

```bash
pip install netkit
netkit --help
```

### GitHub
⭐ **Star the repo**: github.com/zawthetzt/netkit

### Built With
- Python 3.11+
- asyncio for speed
- Claude Code for AI assistance

**Thank you!** 🙏
