from lead_factory.providers.search.base import SearchHit, SearchRequest


class SeedSearchProvider:
    async def search(self, request: SearchRequest) -> list[SearchHit]:
        return [
            SearchHit(url=url, title="Seed URL", source="seed")
            for url in request.seed_urls[: request.max_results]
        ]

