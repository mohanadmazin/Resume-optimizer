# app/services/security.py

"""SSRF protection: URL validation, DNS resolution, port blocking."""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

# Ports that should never be connected to for web fetching
BLOCKED_PORTS: frozenset[int] = frozenset({
    21,    # FTP
    22,    # SSH
    23,    # Telnet
    25,    # SMTP
    110,   # POP3
    135,   # MS RPC
    139,   # NetBIOS
    445,   # SMB
    1433,  # MSSQL
    3306,  # MySQL
    3389,  # RDP
    5432,  # PostgreSQL
    5900,  # VNC
    6379,  # Redis
    6443,  # Kubernetes API
    11211, # Memcached
    27017, # MongoDB
})


class SSRFError(Exception):
    """Raised when a URL fails SSRF safety checks."""


@dataclass(frozen=True)
class ResolvedTarget:
    """A validated, resolved IP and the original hostname."""

    hostname: str
    ip: str
    port: int
    scheme: str


def validate_scheme(url: str) -> None:
    """Reject URL schemes other than http/https."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"URL scheme '{parsed.scheme}' is not allowed.")


def validate_port(url: str) -> None:
    """Reject connections to dangerous ports."""
    parsed = urlparse(url)
    port = parsed.port
    if port and port in BLOCKED_PORTS:
        raise SSRFError(f"Port {port} is blocked for security reasons.")


def resolve_and_validate(url: str) -> ResolvedTarget:
    """Resolve DNS once, validate the IP, return a connectable target.

    Prevents DNS rebinding by resolving exactly once and rejecting
    any hostname that resolves to a private/reserved IP.

    Returns:
        ResolvedTarget with hostname, IP, port, and scheme.

    Raises:
        SSRFError on any validation failure.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise SSRFError(f"URL has no hostname: {url}")

    scheme = parsed.scheme
    port = parsed.port or (443 if scheme == "https" else 80)

    try:
        results = socket.getaddrinfo(hostname, None)
    except OSError as exc:
        raise SSRFError(f"DNS resolution failed for '{hostname}': {exc}")

    if not results:
        raise SSRFError(f"DNS resolution returned no results for '{hostname}'.")

    # Validate ALL resolved IPs — reject if ANY is unsafe
    for _family, _type, _proto, _canonname, sockaddr in results:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise SSRFError(f"Resolved address '{ip_str}' is not a valid IP.")
        if (
            ip.is_private
            or ip.is_reserved
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
        ):
            raise SSRFError(
                f"URL hostname '{hostname}' resolves to a private/reserved IP ({ip_str})."
            )

    first_ip = results[0][4][0]
    return ResolvedTarget(
        hostname=hostname, ip=first_ip, port=port, scheme=scheme
    )
