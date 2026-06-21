---
marp: true
paginate: true
transition: fade
# PechaKucha: 6 slides, 20s auto-advance. Do not change the count.
auto-advance: 20
---

<!-- slide 1 -->
# netkit 🧰
## One CLI for All Network Tools
**Replace 10+ tools with one command**
Ping · Scan · DNS · Whois · Traceroute · HTTP · Subnet · Capture
<!-- 20s -->

---

<!-- slide 2 -->
# The Problem
Network engineers switch between **10+ tools** daily:
- `ping` for connectivity
- `nmap` for port scanning
- `dig` for DNS lookups
- `whois` for domain info
- `traceroute` for routing
**Context switching kills productivity**

---

<!-- slide 3 -->
# What I Built
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

<!-- slide 4 -->
# How I Built It
- **MCP**: GitHub server for repo ops, filesystem for project access, Brave Search for docs
- **Skill**: network-scan — reusable patterns for network diagnostics
- **Agent**: network-analyzer — automated analysis and health reports
- **Claude Code**: scaffolding, debugging, documentation, testing

---

<!-- slide 5 -->
# Why It Matters
| Feature | Traditional | netkit |
|---------|-------------|--------|
| Ping sweep | `nmap -sn` | `netkit ping` |
| Port scan | `nmap -p` | `netkit scan` |
| DNS lookup | `dig` | `netkit dns` |
| JSON output | Each tool different | Consistent |
| Async | Manual parallel | Built-in |
**Same power. Less syntax. Faster results.**

---

<!-- slide 6 -->
# Done checklist
- [x] repo public
- [x] MCP + skill + agent used
- [x] report.md in team repo
- [x] 6 slides, 20s auto-advance
- [x] 3 stars ⭐
**Thank you!** 🙏
