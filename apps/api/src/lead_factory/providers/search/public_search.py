from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from lead_factory.providers.search.base import SearchHit, SearchRequest


class PublicSearchProvider:
    """Light no-key search adapter for local, low-volume discovery."""

    endpoint = "https://html.duckduckgo.com/html/"

    async def search(self, request: SearchRequest) -> list[SearchHit]:
        query = " ".join([request.query, *request.countries]).strip()
        if not query:
            return []
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            response = await client.get(
                self.endpoint,
                params={"q": query},
                headers={"user-agent": "XinghanLeadFactory/1.0 (+https://www.xhanaero.com/)"},
            )
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        hits: list[SearchHit] = []
        for result in soup.select(".result"):
            anchor = result.select_one(".result__a")
            if anchor is None or not anchor.get("href"):
                continue
            href = str(anchor["href"])
            parsed = urlparse(href)
            if parsed.netloc.endswith("duckduckgo.com"):
                href = unquote(parse_qs(parsed.query).get("uddg", [href])[0])
            snippet = result.select_one(".result__snippet")
            hits.append(
                SearchHit(
                    url=href,
                    title=anchor.get_text(" ", strip=True),
                    snippet=snippet.get_text(" ", strip=True) if snippet else "",
                    source="public_search",
                )
            )
            if len(hits) >= request.max_results:
                break
        return hits
