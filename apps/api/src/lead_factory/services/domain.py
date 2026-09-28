from __future__ import annotations

from urllib.parse import urlsplit

import tldextract


_extract = tldextract.TLDExtract(suffix_list_urls=())


def normalize_domain(url: str) -> str:
    parts = urlsplit(url)
    if not parts.hostname:
        raise ValueError("URL must include a hostname")
    try:
        hostname = parts.hostname.encode("idna").decode("ascii").casefold().rstrip(".")
    except UnicodeError as exc:
        raise ValueError("URL hostname is invalid") from exc
    result = _extract(hostname)
    if not result.domain:
        raise ValueError("URL must include a registrable hostname")
    if result.suffix:
        return f"{result.domain}.{result.suffix}"
    return result.domain

