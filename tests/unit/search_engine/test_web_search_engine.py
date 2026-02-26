from unittest.mock import MagicMock, patch

from services.web_search_engine import GeminiGroundingSearchEngine, GoogleSearchEngine


@patch("services.web_search_engine.requests.post")
def test_gemini_grounding_search_engine_ai_studio(mock_post, monkeypatch):
    monkeypatch.setattr("config.GOOGLE_AI_STUDIO_API_KEY", "test-ai-studio-key")
    monkeypatch.setattr("config.GEMINI_SEARCH_USE_VERTEX", False)
    monkeypatch.setattr("config.GEMINI_SEARCH_MODEL", "gemini-2.5-flash")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"results": ['
                                '{"title": "Job 1", "link": "https://jobs.lever.co/a/apply", "snippet": "visa sponsorship"},'
                                '{"title": "Job 2", "link": "https://boards.greenhouse.io/b/jobs/123", "snippet": "sponsorship available"}'
                                "]}"
                            )
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    search_engine = GeminiGroundingSearchEngine()
    result = search_engine.search("software engineer uk", limit=2)

    assert len(result.results) == 2
    assert result.results[0].title == "Job 1"
    assert result.results[0].link == "https://jobs.lever.co/a/apply"
    assert result.results[1].title == "Job 2"
    assert result.engine_name == "gemini_grounding"

    assert mock_post.call_count == 1
    called_endpoint = mock_post.call_args.kwargs["url"] if "url" in mock_post.call_args.kwargs else mock_post.call_args.args[0]
    assert called_endpoint.endswith("/models/gemini-2.5-flash:generateContent")
    assert mock_post.call_args.kwargs["params"] == {"key": "test-ai-studio-key"}


@patch("services.web_search_engine.requests.post")
def test_google_alias_engine_uses_grounding(mock_post, monkeypatch):
    monkeypatch.setattr("config.GOOGLE_AI_STUDIO_API_KEY", "test-ai-studio-key")
    monkeypatch.setattr("config.GEMINI_SEARCH_USE_VERTEX", False)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "https://jobs.lever.co/example/apply"
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    search_engine = GoogleSearchEngine()
    result = search_engine.search("test query", limit=1)

    assert len(result.results) == 1
    assert result.results[0].link == "https://jobs.lever.co/example/apply"

