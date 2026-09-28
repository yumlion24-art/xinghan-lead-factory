from __future__ import annotations

import asyncio
import hashlib
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin

import httpx

from lead_factory.services.budgets import BudgetKind, BudgetLedger
from lead_factory.services.url_safety import (
    Resolver,
    SafeUrl,
    SocketResolver,
    UnsafeUrlError,
    validate_public_url,
)


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class RedirectResponse:
    location: str


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    headers: dict[str, str]
    content: bytes
    final_url: str
    text: str
    content_hash: str


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes
    final_url: str

    def to_fetch_result(self) -> FetchResult:
        return FetchResult(
            status_code=self.status_code,
            headers=self.headers,
            content=self.content,
            final_url=self.final_url,
            text=self.content.decode("utf-8", errors="replace"),
            content_hash=hashlib.sha256(self.content).hexdigest(),
        )


class Transport(Protocol):
    async def get(
        self,
        url: str,
        resolved_ips: tuple[str, ...],
        timeout_seconds: float,
        max_bytes: int,
    ) -> HttpResponse | RedirectResponse: ...


class HttpxTransport:
    async def get(
        self,
        url: str,
        resolved_ips: tuple[str, ...],
        timeout_seconds: float,
        max_bytes: int,
    ) -> HttpResponse | RedirectResponse:
        del resolved_ips
        async with (
            httpx.AsyncClient(follow_redirects=False, timeout=timeout_seconds) as client,
            client.stream("GET", url) as response,
        ):
                if response.is_redirect and response.headers.get("location"):
                    return RedirectResponse(response.headers["location"])
                chunks: list[bytes] = []
                length = 0
                async for chunk in response.aiter_bytes():
                    length += len(chunk)
                    if length > max_bytes:
                        raise FetchError("Response exceeds configured size limit")
                    chunks.append(chunk)
                return HttpResponse(
                    response.status_code,
                    {key.casefold(): value for key, value in response.headers.items()},
                    b"".join(chunks),
                    str(response.url),
                )


async def _sleep(callback: Callable[[float], object], seconds: float) -> None:
    result = callback(seconds)
    if inspect.isawaitable(result):
        await result


class Fetcher:
    def __init__(
        self,
        transport: Transport | None = None,
        resolver: Resolver | None = None,
        *,
        timeout_seconds: float = 12,
        max_response_bytes: int = 2_000_000,
        max_redirects: int = 5,
        max_retries: int = 2,
        domain_delay_seconds: float = 0,
        allowed_content_types: tuple[str, ...] = ("text/html",),
        sleep: Callable[[float], object] = asyncio.sleep,
    ) -> None:
        self.transport = transport or HttpxTransport()
        self.resolver = resolver or SocketResolver()
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects
        self.max_retries = max_retries
        self.domain_delay_seconds = domain_delay_seconds
        self.allowed_content_types = allowed_content_types
        self.sleep = sleep

    async def fetch(self, safe_url: SafeUrl, budget: BudgetLedger) -> FetchResult:
        current = safe_url
        redirects = 0
        while True:
            fresh = validate_public_url(current.url, self.resolver)
            if set(fresh.resolved_ips) != set(current.resolved_ips):
                raise UnsafeUrlError("DNS resolution changed after URL validation")

            response: HttpResponse | RedirectResponse | None = None
            for attempt in range(self.max_retries + 1):
                budget.consume(BudgetKind.PAGE)
                if self.domain_delay_seconds:
                    await _sleep(self.sleep, self.domain_delay_seconds)
                try:
                    response = await self.transport.get(
                        current.url,
                        current.resolved_ips,
                        self.timeout_seconds,
                        self.max_response_bytes,
                    )
                    break
                except (TimeoutError, httpx.TransportError) as exc:
                    if attempt == self.max_retries:
                        raise FetchError(f"Fetch failed after {attempt + 1} attempts") from exc
                    await _sleep(self.sleep, 2 ** (attempt + 1))

            if response is None:
                raise FetchError("Fetch produced no response")

            if isinstance(response, RedirectResponse):
                redirects += 1
                if redirects > self.max_redirects:
                    raise FetchError("Too many redirects")
                target = urljoin(current.url, response.location)
                current = validate_public_url(target, self.resolver)
                continue

            if len(response.content) > self.max_response_bytes:
                raise FetchError("Response exceeds configured size limit")
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().casefold()
            if content_type not in self.allowed_content_types:
                raise FetchError(f"Unsupported content type: {content_type or 'missing'}")
            if response.status_code >= 400:
                raise FetchError(f"HTTP {response.status_code}")
            return response.to_fetch_result()
