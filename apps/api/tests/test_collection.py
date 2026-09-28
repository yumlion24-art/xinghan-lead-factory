from __future__ import annotations

from pathlib import Path

import httpcore
import pytest

from lead_factory.services import fetcher as fetcher_module
from lead_factory.services.budgets import BudgetLedger, BudgetLimits
from lead_factory.services.extractor import extract_company
from lead_factory.services.fetcher import (
    Fetcher,
    FetchError,
    HttpResponse,
    RedirectResponse,
    _pinned_request,
)
from lead_factory.services.robots import RobotsPolicy
from lead_factory.services.url_safety import UnsafeUrlError, validate_public_url


class SequenceResolver:
    def __init__(self, *answers: tuple[str, ...]) -> None:
        self.answers = list(answers)

    def resolve(self, hostname: str) -> tuple[str, ...]:
        return self.answers.pop(0)


class FakeTransport:
    def __init__(self, *responses: HttpResponse | RedirectResponse | Exception) -> None:
        self.responses = list(responses)
        self.calls = 0

    async def get(self, url, resolved_ips, timeout_seconds, max_bytes):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def budget() -> BudgetLedger:
    return BudgetLedger(BudgetLimits(pages=5, domains=5, ai_calls=0, elapsed_seconds=60))


def test_http_request_is_pinned_to_validated_ip_with_original_host_and_sni() -> None:
    target, headers, extensions = _pinned_request(
        "https://example.com/catalog?q=tray", "93.184.216.34"
    )

    assert target == "https://93.184.216.34/catalog?q=tray"
    assert headers == {"host": "example.com"}
    assert extensions == {"sni_hostname": "example.com"}


class RecordingNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self) -> None:
        self.host: str | None = None

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ):
        self.host = host
        return object()

    async def connect_unix_socket(self, path, timeout=None, socket_options=None):
        raise AssertionError("Unix sockets are not used for public web collection")

    async def sleep(self, seconds: float) -> None:
        return None


@pytest.mark.asyncio
async def test_pinned_network_backend_keeps_hostname_for_tls_but_connects_to_validated_ip() -> None:
    delegate = RecordingNetworkBackend()
    backend = fetcher_module.PinnedNetworkBackend("93.184.216.34", delegate=delegate)

    await backend.connect_tcp("example.com", 443)

    assert delegate.host == "93.184.216.34"


@pytest.mark.asyncio
async def test_fetch_blocks_dns_rebinding_before_transport() -> None:
    resolver = SequenceResolver(("93.184.216.34",), ("127.0.0.1",))
    safe = validate_public_url("https://example.com", resolver)
    transport = FakeTransport(HttpResponse(200, {"content-type": "text/html"}, b"ok", "https://example.com"))
    fetcher = Fetcher(transport=transport, resolver=resolver, sleep=lambda _: None)

    with pytest.raises(UnsafeUrlError, match="public"):
        await fetcher.fetch(safe, budget())
    assert transport.calls == 0


@pytest.mark.asyncio
async def test_fetch_blocks_private_redirect_target() -> None:
    resolver = SequenceResolver(
        ("93.184.216.34",),
        ("93.184.216.34",),
        ("127.0.0.1",),
    )
    safe = validate_public_url("https://example.com", resolver)
    transport = FakeTransport(RedirectResponse("http://private.example/admin"))
    fetcher = Fetcher(transport=transport, resolver=resolver, sleep=lambda _: None)

    with pytest.raises(UnsafeUrlError, match="public"):
        await fetcher.fetch(safe, budget())


@pytest.mark.asyncio
async def test_fetch_rejects_oversized_and_non_html_responses() -> None:
    resolver = SequenceResolver(("93.184.216.34",), ("93.184.216.34",))
    safe = validate_public_url("https://example.com", resolver)
    transport = FakeTransport(
        HttpResponse(200, {"content-type": "text/html"}, b"x" * 11, "https://example.com")
    )
    fetcher = Fetcher(
        transport=transport,
        resolver=resolver,
        max_response_bytes=10,
        sleep=lambda _: None,
    )

    with pytest.raises(FetchError, match="size"):
        await fetcher.fetch(safe, budget())


@pytest.mark.asyncio
async def test_transient_failures_retry_only_to_configured_cap() -> None:
    resolver = SequenceResolver(
        ("93.184.216.34",),
        ("93.184.216.34",),
        ("93.184.216.34",),
        ("93.184.216.34",),
    )
    safe = validate_public_url("https://example.com", resolver)
    transport = FakeTransport(TimeoutError("slow"), TimeoutError("slow"), TimeoutError("slow"))
    delays: list[float] = []
    fetcher = Fetcher(transport=transport, resolver=resolver, max_retries=2, sleep=delays.append)

    with pytest.raises(FetchError, match="after 3 attempts"):
        await fetcher.fetch(safe, budget())
    assert transport.calls == 3
    assert delays == [2.0, 4.0]


@pytest.mark.asyncio
async def test_fetch_applies_per_domain_delay_and_hashes_content() -> None:
    resolver = SequenceResolver(("93.184.216.34",), ("93.184.216.34",))
    safe = validate_public_url("https://example.com", resolver)
    transport = FakeTransport(
        HttpResponse(200, {"content-type": "text/html; charset=utf-8"}, b"<h1>Hello</h1>", "https://example.com")
    )
    delays: list[float] = []
    fetcher = Fetcher(transport=transport, resolver=resolver, domain_delay_seconds=2, sleep=delays.append)

    result = await fetcher.fetch(safe, budget())

    assert delays == [2]
    assert result.content_hash == "e2c6c0ea7c7900c31f953e48d30d5e839801ab90630d751e7c8426ed5859da47"
    assert result.text == "<h1>Hello</h1>"


def test_robots_policy_denies_disallowed_path() -> None:
    policy = RobotsPolicy.from_text("User-agent: *\nDisallow: /private\n")

    assert policy.allowed("XinghanLeadFactory/1.0", "https://example.com/products") is True
    assert policy.allowed("XinghanLeadFactory/1.0", "https://example.com/private/list") is False


def test_extractor_uses_visible_text_and_same_domain_links() -> None:
    html = (Path(__file__).parent / "fixtures/company_sites/airline-caterer.html").read_text("utf-8")
    page = HttpResponse(200, {"content-type": "text/html"}, html.encode(), "https://skymeals.example")

    observation = extract_company(page.to_fetch_result())

    assert observation.title == "Sky Meals International"
    assert "secretTrackingPayload" not in observation.visible_text
    assert "Inflight catering procurement" in observation.visible_text
    assert observation.same_domain_links == ["https://skymeals.example/products"]
    assert observation.contact_routes == [
        {"type": "email", "value": "buying@skymeals.example"}
    ]
