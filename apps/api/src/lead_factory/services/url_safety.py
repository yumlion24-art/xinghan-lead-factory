from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit


class UnsafeUrlError(ValueError):
    pass


class Resolver(Protocol):
    def resolve(self, hostname: str) -> tuple[str, ...]: ...


class SocketResolver:
    def resolve(self, hostname: str) -> tuple[str, ...]:
        answers = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        return tuple(dict.fromkeys(answer[4][0] for answer in answers))


@dataclass(frozen=True)
class SafeUrl:
    url: str
    hostname: str
    resolved_ips: tuple[str, ...]


def _assert_public(addresses: tuple[str, ...]) -> None:
    if not addresses:
        raise UnsafeUrlError("URL hostname did not resolve")
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError as exc:
            raise UnsafeUrlError("URL resolved to an invalid address") from exc
        if not parsed.is_global:
            raise UnsafeUrlError("URL must resolve only to public addresses")


def validate_public_url(url: str, resolver: Resolver | None = None) -> SafeUrl:
    resolver = resolver or SocketResolver()
    parts = urlsplit(url)
    if parts.scheme.casefold() not in {"http", "https"}:
        raise UnsafeUrlError("Only HTTP and HTTPS URLs are supported")
    if not parts.hostname:
        raise UnsafeUrlError("URL must include a hostname")
    if parts.username or parts.password:
        raise UnsafeUrlError("Credentials in URLs are not supported")

    try:
        hostname = parts.hostname.encode("idna").decode("ascii").casefold()
        port = parts.port
    except (UnicodeError, ValueError) as exc:
        raise UnsafeUrlError("URL hostname or port is invalid") from exc
    if port is not None and port not in {80, 443}:
        raise UnsafeUrlError("Only standard HTTP and HTTPS ports are supported")

    addresses = resolver.resolve(hostname)
    _assert_public(addresses)
    netloc = hostname if port is None else f"{hostname}:{port}"
    normalized = urlunsplit((parts.scheme.casefold(), netloc, parts.path or "", parts.query, ""))
    return SafeUrl(url=normalized, hostname=hostname, resolved_ips=addresses)

