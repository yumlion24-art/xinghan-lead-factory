import pytest

from lead_factory.services.url_safety import UnsafeUrlError, validate_public_url


class StaticResolver:
    def __init__(self, *addresses: str) -> None:
        self.addresses = addresses

    def resolve(self, hostname: str) -> tuple[str, ...]:
        return self.addresses


@pytest.mark.parametrize(
    "url,address",
    [
        ("http://127.0.0.1/admin", "127.0.0.1"),
        ("http://localhost/admin", "127.0.0.1"),
        ("http://metadata.internal/", "169.254.169.254"),
        ("http://corp.internal/", "10.2.3.4"),
        ("http://ipv6.internal/", "::1"),
    ],
)
def test_private_and_reserved_targets_are_blocked(url: str, address: str) -> None:
    with pytest.raises(UnsafeUrlError, match="public"):
        validate_public_url(url, StaticResolver(address))


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/a", "javascript:alert(1)"])
def test_non_http_schemes_are_blocked(url: str) -> None:
    with pytest.raises(UnsafeUrlError, match="HTTP"):
        validate_public_url(url, StaticResolver("93.184.216.34"))


def test_public_target_records_the_validated_address() -> None:
    safe = validate_public_url("https://Example.com/path#fragment", StaticResolver("93.184.216.34"))

    assert safe.url == "https://example.com/path"
    assert safe.hostname == "example.com"
    assert safe.resolved_ips == ("93.184.216.34",)

