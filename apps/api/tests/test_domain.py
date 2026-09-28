import pytest

from lead_factory.services.domain import normalize_domain


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://WWW.Example.COM/products?utm_source=x", "example.com"),
        ("https://shop.example.co.uk/path", "example.co.uk"),
        ("https://食狮.com.cn/产品", "xn--85x722f.com.cn"),
    ],
)
def test_normalize_domain_returns_registrable_ascii_domain(url: str, expected: str) -> None:
    assert normalize_domain(url) == expected


def test_normalize_domain_rejects_hostless_input() -> None:
    with pytest.raises(ValueError, match="hostname"):
        normalize_domain("not a URL")

