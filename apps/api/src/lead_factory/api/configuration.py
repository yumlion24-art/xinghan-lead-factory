from fastapi import APIRouter, Request

router = APIRouter(tags=["configuration"])


@router.get("/configuration")
def configuration(request: Request) -> dict[str, object]:
    catalog = request.app.state.catalog
    return {
        "products": catalog.products.model_dump(mode="json"),
        "icp": catalog.icp.model_dump(mode="json"),
        "score_boundaries": {
            "A": catalog.scoring.grade_a_min,
            "B": catalog.scoring.grade_b_min,
            "C": catalog.scoring.grade_c_min,
        },
        "crawler_limits": catalog.crawler.model_dump(mode="json"),
        "ai_mode": request.app.state.settings.ai_provider,
    }

