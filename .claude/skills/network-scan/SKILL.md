# Network Scan Skill

## Description
Automated network scanning and diagnostics using netkit CLI tools.

## When to Use
- User asks to scan a network or IP range
- User wants to check port availability
- User needs DNS or WHOIS lookups
- User requests network troubleshooting

## Instructions

### Step 1: Parse the Target
Extract the target from user input:
- IP address: `192.168.1.1`
- CIDR range: `192.168.1.0/24`
- Domain: `example.com`

### Step 2: Determine Scan Type
Based on user request:
- **Ping sweep**: `netkit ping <target>`
- **Port scan**: `netkit scan <target> -p <ports>`
- **DNS lookup**: `netkit dns <domain>`
- **WHOIS**: `netkit whois <domain>`
- **Traceroute**: `netkit trace <target>`
- **HTTP probe**: `netkit http <url>`

### Step 3: Execute and Format
Run the appropriate netkit command and format output:
```bash
# Example: Quick ping sweep
netkit ping 192.168.1.0/24

# Example: Port scan
netkit scan 10.0.0.1 -p 1-1000

# Example: DNS lookup with all record types
netkit dns example.com --types A,AAAA,MX,NS,TXT
```

### Step 4: Provide Analysis
Interpret results for the user:
- Identify live hosts
- Flag open ports and services
- Note DNS configuration issues
- Suggest next steps if issues found

## Output Format
Always provide:
1. Summary of findings
2. Detailed results table
3. Recommendations (if issues found)

## Examples

### Example 1: Scan local network
```
User: Scan my local network 192.168.1.0/24

Action: Run `netkit ping 192.168.1.0/24`
Output: Table of live hosts with response times
```

### Example 2: Check domain DNS
```
User: Look up DNS records for google.com

Action: Run `netkit dns google.com --types A,AAAA,MX,NS`
Output: Formatted DNS records with analysis
```

## Notes
- Always use JSON output for programmatic use: `-o json`
- For large networks, scans may take time - inform user
- Respect rate limits for external lookups (WHOIS, DNS)
