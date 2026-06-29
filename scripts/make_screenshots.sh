#!/bin/bash
# Generate SVG screenshots from netkit command output

SCREENSHOTS_DIR="$(dirname "$0")/../screenshots"
mkdir -p "$SCREENSHOTS_DIR"

# Colors (Dracula theme)
BG="#282a36"
FG="#f8f8f2"
GREEN="#50fa7b"
CYAN="#8be9fd"
YELLOW="#f1f48d"
PINK="#ff79c6"
PURPLE="#bd93f9"
GRAY="#6272a4"

create_svg() {
    local title="$1"
    local content="$2"
    local filename="$3"
    local width="${4:-1280}"
    local height="${5:-800}"

    cat > "$SCREENSHOTS_DIR/$filename" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">
  <defs>
    <style>
      text { font-family: 'DejaVu Sans Mono', 'Consolas', monospace; font-size: 14px; }
      .title { font-size: 12px; fill: $PINK; }
      .header { font-size: 14px; fill: $FG; font-weight: bold; }
      .cmd { fill: $GREEN; }
      .ok { fill: $GREEN; }
      .fail { fill: $PINK; }
      .info { fill: $CYAN; }
      .highlight { fill: $YELLOW; }
      .normal { fill: $FG; }
      .dim { fill: $GRAY; }
    </style>
  </defs>

  <!-- Background -->
  <rect width="$width" height="$height" fill="$BG"/>

  <!-- Terminal border -->
  <rect x="10" y="10" width="$(($width-20))" height="$(($height-20))" fill="none" stroke="$GRAY" stroke-width="2" rx="8"/>

  <!-- Title bar -->
  <rect x="10" y="10" width="$(($width-20))" height="35" fill="#1e1f29" rx="8"/>
  <rect x="10" y="30" width="$(($width-20))" height="15" fill="#1e1f29"/>
  <circle cx="30" cy="27" r="6" fill="$PINK"/>
  <circle cx="50" cy="27" r="6" fill="$YELLOW"/>
  <circle cx="70" cy="27" r="6" fill="$GREEN"/>
  <text x="$(($width/2-30))" y="30" class="header">$title</text>

  <!-- Content -->
  <text x="30" y="65">
    $content
  </text>
</svg>
EOF
    echo "Created: $filename"
}

# Generate help screenshot
create_svg "netkit" '
    <tspan x="30" dy="0" class="cmd">$ netkit --help</tspan>
    <tspan x="30" dy="25" class="normal">🧰 A full network engineer'\''s CLI toolkit</tspan>
    <tspan x="30" dy="25" class="highlight">Commands:</tspan>
    <tspan x="30" dy="22" class="info">  ping        ICMP ping sweep — single host or subnet scan.</tspan>
    <tspan x="30" dy="20" class="info">  scan        Port scanner — TCP connect, SYN, and UDP scanning.</tspan>
    <tspan x="30" dy="20" class="info">  service     Service &amp; banner detection — grab banners from open ports.</tspan>
    <tspan x="30" dy="20" class="info">  trace       Traceroute — trace the path to a network host.</tspan>
    <tspan x="30" dy="20" class="info">  dns         DNS toolkit — lookups, reverse DNS, zone transfers.</tspan>
    <tspan x="30" dy="20" class="info">  whois       Whois lookup — domain &amp; IP registration information.</tspan>
    <tspan x="30" dy="20" class="info">  http        HTTP probe — check web server status, headers, and TLS.</tspan>
    <tspan x="30" dy="20" class="info">  subnet      Subnet calculator — calculate subnet details and scan for live hosts.</tspan>
    <tspan x="30" dy="20" class="info">  capture     Packet capture — live capture with BPF filter.</tspan>
    <tspan x="30" dy="20" class="info">  interfaces  Network interfaces — show local interface information.</tspan>
    <tspan x="30" dy="20" class="info">  local       Local ports scanner — show all open/listening ports on this machine.</tspan>
    <tspan x="30" dy="20" class="info">  speed       Network speed test — measure download and upload speeds.</tspan>
    <tspan x="30" dy="20" class="info">  down        Down detector — check if websites/services are up or down.</tspan>
    <tspan x="30" dy="20" class="info">  iftop       Network traffic monitor — live bandwidth per connection (iftop-style).</tspan>
' "01-help.svg"

# Generate local ports screenshot
create_svg "netkit local" '
    <tspan x="30" dy="0" class="cmd">$ netkit local</tspan>
    <tspan x="30" dy="25" class="highlight">🖥️  Local Open Ports — zack</tspan>
    <tspan x="30" dy="25" class="info">┌───────┬───────┬────────┬───────────────┬─────────┬──────┐</tspan>
    <tspan x="30" dy="18" class="info">│  PORT │ PROTO │ STATE  │ ADDRESS       │ PROCESS │ PID  │</tspan>
    <tspan x="30" dy="18" class="info">├───────┼───────┼────────┼───────────────┼─────────┼──────┤</tspan>
    <tspan x="30" dy="18" class="ok">│    53 │ TCP   │ LISTEN │ 127.0.0.53    │ systemd │ -    │</tspan>
    <tspan x="30" dy="18" class="ok">│    80 │ TCP   │ LISTEN │ 0.0.0.0       │ nginx   │ 1234 │</tspan>
    <tspan x="30" dy="18" class="ok">│   443 │ TCP   │ LISTEN │ 0.0.0.0       │ nginx   │ 1234 │</tspan>
    <tspan x="30" dy="18" class="ok">│  3306 │ TCP   │ LISTEN │ 127.0.0.1     │ mysqld  │ 5678 │</tspan>
    <tspan x="30" dy="18" class="ok">│  8080 │ TCP   │ LISTEN │ 0.0.0.0       │ node    │ 9012 │</tspan>
    <tspan x="30" dy="18" class="info">└───────┴───────┴────────┴───────────────┴─────────┴──────┘</tspan>
    <tspan x="30" dy="25" class="normal">Total: 5 open ports</tspan>
' "02-local-ports.svg"

# Generate down detector screenshot
create_svg "netkit down" '
    <tspan x="30" dy="0" class="cmd">$ netkit down google github cloudflare</tspan>
    <tspan x="30" dy="25" class="highlight">🔍 Service Status — Down Detector</tspan>
    <tspan x="30" dy="25" class="info">┌─────────────────┬────────────┬────────┬────────────┬─────────────────────┐</tspan>
    <tspan x="30" dy="18" class="info">│ SERVICE         │   STATUS   │  CODE  │  RESPONSE  │ URL                 │</tspan>
    <tspan x="30" dy="18" class="info">├─────────────────┼────────────┼────────┼────────────┼─────────────────────┤</tspan>
    <tspan x="30" dy="18" class="ok">│ google          │   ✅ UP    │  200   │     138ms  │ https://google.com  │</tspan>
    <tspan x="30" dy="18" class="ok">│ github          │   ✅ UP    │  200   │     200ms  │ https://github.com  │</tspan>
    <tspan x="30" dy="18" class="ok">│ cloudflare      │   ✅ UP    │  200   │     878ms  │ https://cloudflare… │</tspan>
    <tspan x="30" dy="18" class="info">└─────────────────┴────────────┴────────┴────────────┴─────────────────────┘</tspan>
    <tspan x="30" dy="25" class="ok">✅ Up: 3  |  ❌ Down: 0  |  Total: 3</tspan>
' "03-down-detector.svg"

echo "Done! Screenshots saved to $SCREENSHOTS_DIR"
