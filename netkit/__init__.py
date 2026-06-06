"""netkit — A network engineer's CLI toolkit."""
from importlib.metadata import version

try:
    __version__ = version("netkit")
except Exception:
    __version__ = "0.1.0"
