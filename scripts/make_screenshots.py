#!/usr/bin/env python3
"""Generate PNG screenshots from netkit command output."""

import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Run: pip install pillow")
    sys.exit(1)

SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Terminal colors (Dracula theme)
BG = (40, 42, 54)
FG = (248, 248, 242)
GREEN = (80, 250, 123)
CYAN = (139, 233, 253)
YELLOW = (241, 250, 140)
PINK = (255, 121, 198)
PURPLE = (189, 147, 249)
GRAY = (98, 114, 164)

def create_screenshot(text: str, filename: str, width: int = 1280, height: int = 800):
    """Create a PNG screenshot from terminal text."""
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # Try to use a monospace font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
    except:
        font = ImageFont.load_default()

    # Draw terminal border
    draw.rectangle([10, 10, width-10, height-10], outline=GRAY, width=2)

    # Draw title bar
    draw.rectangle([10, 10, width-10, 45], fill=(30, 31, 40))
    draw.text((30, 18), "● ● ●", fill=PINK, font=font)
    draw.text((width//2 - 50, 18), "netkit", fill=FG, font=font)

    # Draw text
    y = 60
    for line in text.split("\n"):
        if y > height - 30:
            break

        # Simple color highlighting
        color = FG
        if "✅" in line or "ok" in line.lower():
            color = GREEN
        elif "❌" in line or "fail" in line.lower() or "error" in line.lower():
            color = PINK
        elif line.startswith("│") or line.startswith("┃") or line.startswith("┡"):
            color = CYAN
        elif "PORT" in line or "SERVICE" in line or "COMMAND" in line:
            color = YELLOW
        elif line.startswith("$") or line.startswith("netkit"):
            color = GREEN

        draw.text((30, y), line, fill=color, font=font)
        y += 20

    img.save(SCREENSHOTS_DIR / filename)
    print(f"Created: {filename}")


def main():
    """Generate screenshots for all netkit commands."""
    commands = [
        ("netkit --help", "01-help.png"),
        ("netkit local", "02-local-ports.png"),
        ("netkit down google github cloudflare", "03-down-detector.png"),
    ]

    for cmd, filename in commands:
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(Path(__file__).parent.parent)
            )
            text = f"$ {cmd}\n\n{result.stdout}"
            if result.stderr:
                text += f"\n{result.stderr}"
            create_screenshot(text, filename)
        except Exception as e:
            print(f"Error running {cmd}: {e}")


if __name__ == "__main__":
    main()
