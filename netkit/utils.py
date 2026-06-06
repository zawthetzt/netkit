"""Shared utilities: host resolution, validation, helpers."""

import ipaddress
import socket
import re


def resolve_host(host: str) -> str | None:
    """Resolve a hostname to an IP address. Returns None on failure."""
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None


def resolve_hostname(ip: str) -> str | None:
    """Reverse DNS lookup. Returns hostname or None."""
    try:
        result = socket.gethostbyaddr(ip)
        return result[0]
    except (socket.herror, socket.gaierror, ValueError):
        return None


def parse_targets(targets: list[str]) -> list[str]:
    """Parse a list of target specs into flat IP list.
    Accepted formats:
      - "192.168.1.1"
      - "192.168.1.0/24"   (CIDR)
      - "192.168.1.1-20"   (range)
      - "192.168.1.1,5"    (comma shorthand for range)
      - "hostname.example"
    """
    ips: list[str] = []
    for t in targets:
        # Try CIDR first
        if "/" in t:
            try:
                net = ipaddress.ip_network(t, strict=False)
                ips.extend(str(h) for h in net.hosts())
                continue
            except ValueError:
                pass

        # Try range: 192.168.1.1-20
        m = re.match(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.)(\d{1,3})-(\d{1,3})$", t)
        if m:
            prefix, start, end = m.group(1), int(m.group(2)), int(m.group(3))
            for i in range(start, end + 1):
                ips.append(f"{prefix}{i}")
            continue

        # Try comma-range: 192.168.1.1,5
        m = re.match(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.)(\d{1,3}),(\d{1,3})$", t)
        if m:
            prefix, start, end = m.group(1), int(m.group(2)), int(m.group(3))
            for i in range(start, end + 1):
                ips.append(f"{prefix}{i}")
            continue

        # Resolve hostname or pass through IP
        resolved = resolve_host(t)
        if resolved:
            ips.append(resolved)
        else:
            ips.append(t)  # let caller handle failure

    return ips


def parse_ports(port_spec: str) -> list[int]:
    """Parse port specification string into a list of ports.
    Formats: "80", "22,80,443", "1-1024", "22,80,443-500"
    """
    ports: set[int] = set()
    parts = port_spec.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                a, b = part.split("-", 1)
                start, end = int(a.strip()), int(b.strip())
                if 1 <= start <= 65535 and 1 <= end <= 65535 and start <= end:
                    ports.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= 65535:
                    ports.add(p)
            except ValueError:
                continue
    return sorted(ports)


COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
    993, 995, 1433, 1521, 2049, 3306, 3389, 5432, 5900, 5985,
    5986, 6379, 8080, 8443, 9000, 9090, 27017,
]

WELL_KNOWN_SERVICES: dict[int, str] = {
    20: "FTP-data", 21: "FTP", 22: "SSH", 23: "Telnet",
    25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
    111: "RPC", 135: "MSRPC", 137: "NetBIOS-ns", 138: "NetBIOS-dgm",
    139: "NetBIOS-ssn", 143: "IMAP", 161: "SNMP", 162: "SNMP-trap",
    179: "BGP", 389: "LDAP", 443: "HTTPS", 445: "SMB",
    465: "SMTPS", 514: "Syslog", 515: "LPD", 587: "SMTP-sub",
    636: "LDAPS", 993: "IMAPS", 995: "POP3S", 1080: "SOCKS",
    1194: "OpenVPN", 1352: "Lotus-Notes", 1433: "MSSQL",
    1521: "Oracle-DB", 1723: "PPTP", 2049: "NFS", 2082: "cPanel",
    2083: "cPanel-SSL", 2375: "Docker", 2376: "Docker-SSL",
    2483: "Oracle-DB", 2484: "Oracle-DB-SSL", 3128: "Squid",
    3306: "MySQL", 3389: "RDP", 3690: "SVN", 4333: "mSQL",
    4444: "Blaster", 4848: "GlassFish", 5000: "UPnP",
    5432: "PostgreSQL", 5554: "Sasser", 5900: "VNC",
    5901: "VNC-1", 5902: "VNC-2", 5903: "VNC-3", 5984: "CouchDB",
    5985: "WinRM-HTTP", 5986: "WinRM-HTTPS", 6379: "Redis",
    6443: "K8s-API", 6667: "IRC", 6668: "IRC", 6669: "IRC",
    7001: "WebLogic", 7002: "WebLogic-SSL", 8000: "HTTP-alt",
    8080: "HTTP-proxy", 8081: "HTTP-alt", 8086: "InfluxDB",
    8087: "InfluxDB", 8088: "InfluxDB", 8443: "HTTPS-alt",
    9000: "SonarQube", 9042: "Cassandra", 9090: "Prometheus",
    9092: "Kafka", 9100: "NodeExporter", 9200: "Elasticsearch",
    9300: "Elasticsearch", 9418: "Git", 11211: "Memcached",
    27017: "MongoDB", 27018: "MongoDB", 27019: "MongoDB",
    50070: "HDFS", 50075: "HDFS",
}

CLOSE_PORTS_SAMPLE = [31000, 31001, 31002]


def guess_service(port: int, protocol: str = "tcp") -> str:
    return WELL_KNOWN_SERVICES.get(port, "unknown")


def is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False
