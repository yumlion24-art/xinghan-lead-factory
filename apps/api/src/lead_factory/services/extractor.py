from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from lead_factory.services.fetcher import FetchResult


EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


@dataclass(frozen=True)
class CompanyPageObservation:
    title: str
    visible_text: str
    same_domain_links: list[str]
    contact_routes: list[dict[str, str]]
    source_url: str


def extract_company(page: FetchResult) -> CompanyPageObservation:
    soup = BeautifulSoup(page.text, "html.parser")
    for node in soup(["script", "style", "noscript", "template"]):
        node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    visible_text = " ".join(soup.get_text(" ", strip=True).split())
    source_host = urlsplit(page.final_url).hostname
    links: list[str] = []
    emails: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        if href.casefold().startswith("mailto:"):
            emails.append(href[7:].split("?", 1)[0])
            continue
        absolute = urljoin(page.final_url, href)
        parts = urlsplit(absolute)
        if parts.scheme in {"http", "https"} and parts.hostname == source_host:
            normalized = parts._replace(fragment="").geturl()
            if normalized != page.final_url and normalized not in links:
                links.append(normalized)
    emails.extend(EMAIL_PATTERN.findall(visible_text))
    contacts = [
        {"type": "email", "value": email}
        for email in dict.fromkeys(email.casefold() for email in emails)
    ]
    return CompanyPageObservation(
        title=title,
        visible_text=visible_text,
        same_domain_links=links,
        contact_routes=contacts,
        source_url=page.final_url,
    )

