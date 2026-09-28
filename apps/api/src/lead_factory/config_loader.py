from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductFamily(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    buyer_signals: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    recommended_offerings: list[str] = Field(default_factory=list)


class ProductsConfig(BaseModel):
    version: str
    families: list[ProductFamily]


class ICPProfile(BaseModel):
    id: str
    name: str
    company_types: list[str]
    high_value_signals: list[str]
    low_fit_signals: list[str] = Field(default_factory=list)


class ICPConfig(BaseModel):
    version: str
    profiles: list[ICPProfile]


class ScoreWeights(BaseModel):
    icp_fit: int
    product_demand: int
    scale: int
    geography: int
    intent: int
    evidence: int


class ScoreRule(BaseModel):
    id: str
    dimension: str
    points: int
    any_terms: list[str] = Field(default_factory=list)
    description: str


class ScoringConfig(BaseModel):
    version: str
    grade_a_min: int = 75
    grade_b_min: int = 55
    grade_c_min: int = 0
    negative_cap: int = 40
    weights: ScoreWeights
    rules: list[ScoreRule]
    negative_rules: list[ScoreRule]

    @model_validator(mode="after")
    def validate_score_ranges(self) -> ScoringConfig:
        if sum(self.weights.model_dump().values()) != 100:
            raise ValueError("weights must total 100")
        if not 100 >= self.grade_a_min > self.grade_b_min > self.grade_c_min == 0:
            raise ValueError("grade boundaries must descend from A to C and end at 0")
        return self


class CrawlerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_agent: str
    request_timeout_seconds: float
    max_response_bytes: int
    max_redirects: int
    per_domain_concurrency: int
    per_domain_delay_seconds: float
    max_search_results: int
    max_domains_per_task: int
    max_pages_per_domain: int
    max_pages_per_task: int
    max_task_seconds: int
    daily_page_limit: int
    daily_ai_call_limit: int
    allowed_content_types: list[str]


class CatalogConfig(BaseModel):
    products: ProductsConfig
    icp: ICPConfig
    scoring: ScoringConfig
    crawler: CrawlerConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"Missing configuration file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"Configuration must be a mapping: {path}")
    return data


def load_catalog(config_dir: Path) -> CatalogConfig:
    return CatalogConfig(
        products=ProductsConfig.model_validate(_read_yaml(config_dir / "products.yaml")),
        icp=ICPConfig.model_validate(_read_yaml(config_dir / "icp.yaml")),
        scoring=ScoringConfig.model_validate(_read_yaml(config_dir / "scoring.yaml")),
        crawler=CrawlerConfig.model_validate(_read_yaml(config_dir / "crawler.yaml")),
    )
