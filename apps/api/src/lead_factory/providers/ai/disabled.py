from lead_factory.providers.ai.base import EnrichmentRequest, EnrichmentResult, ProviderUnavailable


class DisabledAIProvider:
    def is_available(self) -> bool:
        return False

    async def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        del request
        raise ProviderUnavailable("AI enrichment is disabled")

