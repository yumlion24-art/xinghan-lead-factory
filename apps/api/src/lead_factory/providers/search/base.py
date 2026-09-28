from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SearchRequest:
    query: str
    countries: list[str] = field(default_factory=list)
    seed_urls: list[str] = field(default_factory=list)
    max_results: int = 20


@dataclass(frozen=True)
class SearchHit:
    url: str
    title: str = ""
    snippet: str = ""
    source: str = ""


class SearchProvider(Protocol):
    async def search(self, request: SearchRequest) -> list[SearchHit]: ...

