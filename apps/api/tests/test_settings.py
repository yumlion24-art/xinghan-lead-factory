from pathlib import Path

import pytest
from pydantic import ValidationError

from lead_factory.config_loader import ScoringConfig, load_catalog
from lead_factory.settings import Settings


def test_checked_in_catalog_loads_xinghan_taxonomy(config_dir: Path) -> None:
    catalog = load_catalog(config_dir)

    assert [family.id for family in catalog.products.families] == [
        "airline_airport",
        "foodservice_packaging",
        "sustainable_packaging",
        "flexible_packaging",
    ]
    assert catalog.scoring.grade_a_min == 75
    assert catalog.scoring.grade_b_min == 55
    assert catalog.scoring.grade_c_min == 0
    assert catalog.scoring.negative_cap == 40


def test_scoring_config_rejects_weights_that_do_not_total_100() -> None:
    with pytest.raises(ValidationError, match="weights must total 100"):
        ScoringConfig.model_validate(
            {
                "version": "test",
                "grade_a_min": 75,
                "grade_b_min": 55,
                "grade_c_min": 0,
                "negative_cap": 40,
                "weights": {
                    "icp_fit": 25,
                    "product_demand": 20,
                    "scale": 15,
                    "geography": 10,
                    "intent": 15,
                    "evidence": 10,
                },
                "rules": [],
                "negative_rules": [],
            }
        )


def test_settings_keep_ai_optional(config_dir: Path) -> None:
    settings = Settings(_env_file=None, config_dir=config_dir)

    assert settings.database_url.startswith("sqlite")
    assert settings.ai_api_key is None
    assert settings.ai_provider == "disabled"

