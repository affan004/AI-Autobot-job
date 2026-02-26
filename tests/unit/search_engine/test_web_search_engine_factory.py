import pytest

from services.web_search_engine import GeminiGroundingSearchEngine, WebSearchEngineFactory


def test_web_search_engine_factory_default(monkeypatch):
    monkeypatch.setattr("config.ALLOWED_SEARCH_ENGINES", ["gemini_grounding"])
    monkeypatch.setattr("config.DEFAULT_SEARCH_ENGINE", "gemini_grounding")
    monkeypatch.setattr("config.GOOGLE_AI_STUDIO_API_KEY", "test-key")
    WebSearchEngineFactory._instances = {}

    engine = WebSearchEngineFactory.get_search_engine()
    assert isinstance(engine, GeminiGroundingSearchEngine)


def test_web_search_engine_factory_singleton(monkeypatch):
    monkeypatch.setattr("config.ALLOWED_SEARCH_ENGINES", ["gemini_grounding"])
    monkeypatch.setattr("config.DEFAULT_SEARCH_ENGINE", "gemini_grounding")
    monkeypatch.setattr("config.GOOGLE_AI_STUDIO_API_KEY", "test-key")
    WebSearchEngineFactory._instances = {}

    engine_1 = WebSearchEngineFactory.get_search_engine("gemini_grounding")
    engine_2 = WebSearchEngineFactory.get_search_engine("google")
    assert engine_1 is engine_2


def test_web_search_engine_factory_rejects_disallowed(monkeypatch):
    monkeypatch.setattr("config.ALLOWED_SEARCH_ENGINES", ["gemini_grounding"])
    monkeypatch.setattr("config.DEFAULT_SEARCH_ENGINE", "gemini_grounding")
    monkeypatch.setattr("config.GOOGLE_AI_STUDIO_API_KEY", "test-key")
    WebSearchEngineFactory._instances = {}

    with pytest.raises(ValueError):
        WebSearchEngineFactory.get_search_engine("duckduckgo")

