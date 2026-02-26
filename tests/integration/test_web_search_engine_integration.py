import os

import pytest

from services.web_search_engine import GeminiGroundingSearchEngine


@pytest.mark.integration
def test_gemini_grounding_search_engine_integration():
    if not os.getenv("GOOGLE_AI_STUDIO_API_KEY"):
        pytest.skip("GOOGLE_AI_STUDIO_API_KEY is required for integration test.")

    search_engine = GeminiGroundingSearchEngine()
    response = search_engine.search(
        "site:jobs.lever.co software engineer visa sponsorship",
        limit=3,
    )

    assert len(response.results) > 0
    assert all(result.link.startswith("http") for result in response.results)

