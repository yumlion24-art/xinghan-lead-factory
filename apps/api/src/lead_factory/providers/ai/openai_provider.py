from __future__ import annotations

import json
from pathlib import Path

from openai import AsyncOpenAI

from lead_factory.providers.ai.base import EnrichmentRequest, EnrichmentResult


class OpenAIProvider:
    def __init__(self, api_key: str | None, model: str, prompt_path: Path) -> None:
        self.api_key = api_key
        self.model = model
        self.prompt_path = prompt_path
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

    def is_available(self) -> bool:
        return self.client is not None

    async def enrich(self, request: EnrichmentRequest) -> EnrichmentResult:
        if self.client is None:
            raise RuntimeError("OpenAI provider has no API key")
        prompt = self.prompt_path.read_text(encoding="utf-8")
        payload = {
            "company": request.observation.model_dump(mode="json"),
            "deterministic_score": request.deterministic_score,
            "deterministic_grade": request.deterministic_grade.value,
            "deterministic_product_matches": [
                {
                    "family_id": item.family_id,
                    "reason": item.reason,
                    "evidence_ids": item.evidence_ids,
                }
                for item in request.deterministic_product_matches
            ],
            "prompt_version": request.prompt_version,
        }
        response = await self.client.responses.create(
            model=self.model,
            instructions=prompt,
            input=json.dumps(payload, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "company_enrichment",
                    "strict": True,
                    "schema": EnrichmentResult.model_json_schema(),
                }
            },
        )
        result = EnrichmentResult.model_validate_json(response.output_text)
        usage = getattr(response, "usage", None)
        if usage is not None:
            result.usage.input_tokens = getattr(usage, "input_tokens", None)
            result.usage.output_tokens = getattr(usage, "output_tokens", None)
        return result

