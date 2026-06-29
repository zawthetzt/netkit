---
marp: true
paginate: true
transition: fade
auto-advance: 20
---

<!-- slide 1 -->
# netkit 🧰
## Your Network, One Command Away
**The modern CLI toolkit for network engineers**
Replace 10+ tools with a single, unified interface
<!-- 20s -->

---

<!-- slide 2 -->
# Why netkit?
Network engineers juggle **10+ tools** daily:
- `ping` → `nmap` → `dig` → `whois`
- `traceroute` → `curl` → `tcpdump`
- Different syntax, different output, different flags

**netkit unifies them all:**
```bash
netkit ping 192.168.1.0/24
netkit scan 10.0.0.1 -p 80,443
netkit dns example.com
```

---

<!-- slide 3 -->
# 14 Powerful Commands
| Command | What it does |
|---------|--------------|
| `ping` | Host discovery with CIDR support |
| `scan` | Port scanning (TCP/UDP/SYN) |
| `dns` | DNS lookups & zone transfers |
| `whois` | Domain registration info |
| `trace` | Traceroute with auto fallback |
| `http` | HTTP/HTTPS probing |
| `local` | Open ports on your machine |
| `speed` | Network speed test |
| `down` | Service status checker |
| `iftop` | Live traffic monitor |

---

<!-- slide 4 -->
# AI-Powered Development
Built with **Claude Code** + **MCP**:
- 🤖 **MCP Servers** — GitHub, Filesystem, Brave Search
- 🎯 **Skills** — Reusable network scan patterns
- 🧠 **Agents** — Automated diagnostics
- ⚡ **10x faster** development with AI assistance

```json
// .mcp.json
{
  "mcpServers": {
    "github": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"] }
  }
}
```

---

<!-- slide 5 -->
# Real-World Usage
```bash
# Check if your server is healthy
$ netkit local
🖥️  Local Open Ports — my-server
┌───────┬───────┬────────┬─────────┐
│  PORT │ PROTO │ STATE  │ PROCESS │
├───────┼───────┼────────┼─────────┤
│    80 │ TCP   │ LISTEN │ nginx   │
│   443 │ TCP   │ LISTEN │ nginx   │
│  3306 │ TCP   │ LISTEN │ mysql   │
└───────┴───────┴────────┴─────────┘

# Monitor services in real-time
$ netkit down google github
✅ Up: 2  |  ❌ Down: 0
```

---

<!-- slide 6 -->
# Get Started Now
```bash
pip install netkit
netkit --help
```

### Links
- 📦 **PyPI:** pypi.org/project/netkit
- 💻 **GitHub:** github.com/zawthetzt/netkit
- 📖 **Docs:** README.md

### Built With
- Python 3.11+ · asyncio · Claude Code · MCP

**Thank you!** 🙏
