from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

import config
from constants import BING, BRAVE, GEMINI_GROUNDING, GOOGLE
from logger import logger
from utils.string_utils import is_multi_word


@dataclass
class SearchResult:
    """
    Represents an individual search result item.
    """

    title: str
    link: str
    snippet: str
    raw_data: Optional[Dict[str, Any]] = field(default=None)


@dataclass
class PaginatedSearchResponse:
    """
    Holds a list of SearchResult items plus offset-based pagination info.
    """

    results: List[SearchResult] = field(default_factory=list)
    engine_name: str = ""
    offset: int = 0
    limit: int = 10
    total_results: Optional[int] = None


class SearchTimeRange(Enum):
    LAST_24_HOURS = "last_24_hours"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"


@dataclass
class CustomTimeRange:
    start_time: datetime
    end_time: datetime


@dataclass
class UnifiedQuery:
    """
    Represents a unified search query that can be translated into
    platform-specific queries.
    """

    keywords: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=list)
    whitelist: List[str] = field(default_factory=list)
    date_range: Optional[SearchTimeRange] = None
    gl: Optional[str] = None
    source_sites: List[str] = field(default_factory=list)


class WebSearchEngine(ABC):
    @property
    @abstractmethod
    def DEFAULT_SEARCH_LIMIT(self) -> int:
        """
        Returns the default search limit for the search engine.
        """
        raise NotImplementedError

    @abstractmethod
    def search(
        self, query: str, params: dict, offset: int = 0, limit: int = 10
    ) -> PaginatedSearchResponse:
        """
        Perform an offset-based search with the specified limit.
        """
        raise NotImplementedError

    @abstractmethod
    def build_query(self, query: UnifiedQuery) -> Tuple[str, dict]:
        """
        Returns a tuple containing:
          - A query string
          - A parameters dictionary
        specific to the search engine.
        """
        raise NotImplementedError


class SearchQueryBuilder:
    """
    Builder for creating unified search queries.
    """

    def __init__(self):
        self.keywords: List[str] = []
        self.blacklist: List[str] = []
        self.whitelist: List[str] = []
        self.date_range: Optional[SearchTimeRange] = None
        self.gl: Optional[str] = None
        self.source_sites: List[str] = []

    @staticmethod
    def create() -> "SearchQueryBuilder":
        return SearchQueryBuilder()

    def add_to_blacklist(self, term: Union[str, List[str]]) -> "SearchQueryBuilder":
        if isinstance(term, list):
            self.blacklist.extend(term)
        else:
            self.blacklist.append(term)
        return self

    def add_to_whitelist(self, term: Union[str, List[str]]) -> "SearchQueryBuilder":
        if isinstance(term, list):
            self.whitelist.extend(term)
        else:
            self.whitelist.append(term)
        return self

    def add_to_keywords(self, term: Union[str, List[str]]) -> "SearchQueryBuilder":
        if isinstance(term, list):
            self.keywords.extend(term)
        else:
            self.keywords.append(term)
        return self

    def add_source_sites(self, sites: Union[str, List[str]]) -> "SearchQueryBuilder":
        if isinstance(sites, list):
            self.source_sites.extend(sites)
        else:
            self.source_sites.append(sites)
        return self

    def set_date_range(self, date_range: SearchTimeRange) -> "SearchQueryBuilder":
        if not isinstance(date_range, SearchTimeRange):
            raise ValueError("date_range must be an instance of SearchTimeRange Enum")
        self.date_range = date_range
        return self

    def set_geolocation(self, gl: str) -> "SearchQueryBuilder":
        self.gl = gl
        return self

    def build_unified_query(self) -> UnifiedQuery:
        return UnifiedQuery(
            keywords=self.keywords,
            blacklist=self.blacklist,
            whitelist=self.whitelist,
            date_range=self.date_range,
            gl=self.gl,
            source_sites=self.source_sites,
        )

    def build_query_for_engine(self, search_engine: WebSearchEngine) -> Tuple[str, dict]:
        return search_engine.build_query(self.build_unified_query())

    @staticmethod
    def build_final_query_string(unified_query: UnifiedQuery) -> str:
        """
        Construct the final query string:
        keywords + (whitelist) + (blacklist) + optional site constraints.
        """

        keywords_part = " ".join(unified_query.keywords)

        whitelist_part = ""
        if unified_query.whitelist:
            quoted = [
                f"\"{w}\"" if is_multi_word(w) else w for w in unified_query.whitelist
            ]
            whitelist_part = "(" + " OR ".join(quoted) + ")"

        blacklist_part = ""
        if unified_query.blacklist:
            negated = [
                f"-\"{b}\"" if is_multi_word(b) else f"-{b}"
                for b in unified_query.blacklist
            ]
            blacklist_part = "(" + " OR ".join(negated) + ")"

        sources_part = ""
        if unified_query.source_sites:
            normalized_sites = [
                site.strip().replace("site:", "")
                for site in unified_query.source_sites
                if site and site.strip()
            ]
            if normalized_sites:
                sources_part = "(" + " OR ".join(
                    [f"site:{site}" for site in normalized_sites]
                ) + ")"

        parts = [keywords_part, whitelist_part, blacklist_part, sources_part]
        return " ".join(part for part in parts if part).strip()


class GeminiGroundingSearchEngine(WebSearchEngine):
    """
    Search engine implementation backed by Gemini Grounding with Google Search.
    """

    AI_STUDIO_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def DEFAULT_SEARCH_LIMIT(self) -> int:
        return 20

    def __init__(self):
        self.ai_studio_api_key = config.GOOGLE_AI_STUDIO_API_KEY
        self.model = config.GEMINI_SEARCH_MODEL
        self.use_vertex = config.GEMINI_SEARCH_USE_VERTEX
        self.vertex_project_id = config.VERTEX_PROJECT_ID
        self.vertex_location = config.VERTEX_LOCATION
        self.vertex_model = config.VERTEX_GEMINI_MODEL
        self.default_sites = [
            site.strip()
            for site in config.GEMINI_SEARCH_DEFAULT_SITES.split(",")
            if site.strip()
        ]

    def build_query(self, query: UnifiedQuery) -> Tuple[str, dict]:
        base_query = SearchQueryBuilder.build_final_query_string(query)
        params: Dict[str, Any] = {
            "date_range": query.date_range.value if query.date_range else None,
            "gl": query.gl,
            "source_sites": query.source_sites or self.default_sites,
        }
        return base_query, params

    def search(
        self, query: str, params: dict | None = None, offset: int = 0, limit: int | None = None
    ) -> PaginatedSearchResponse:
        params = params or {}
        limit = limit or self.DEFAULT_SEARCH_LIMIT

        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        if offset < 0:
            raise ValueError("offset cannot be negative")

        requested_size = offset + limit
        prompt = self._build_grounded_prompt(query, params, requested_size)
        raw_response = self._generate_grounded_response(prompt)
        all_results = self._response_to_results(raw_response, requested_size)
        paged_results = all_results[offset : offset + limit]

        return PaginatedSearchResponse(
            results=paged_results,
            engine_name=GEMINI_GROUNDING,
            offset=offset,
            limit=limit,
            total_results=len(all_results),
        )

    def _build_grounded_prompt(self, query: str, params: dict, limit: int) -> str:
        source_sites = params.get("source_sites") or self.default_sites
        date_hint = ""

        date_range = params.get("date_range")
        if date_range == SearchTimeRange.LAST_24_HOURS.value:
            date_hint = "Prefer jobs posted in the last 24 hours."
        elif date_range == SearchTimeRange.LAST_WEEK.value:
            date_hint = "Prefer jobs posted in the last 7 days."
        elif date_range == SearchTimeRange.LAST_MONTH.value:
            date_hint = "Prefer jobs posted in the last 30 days."

        location_hint = ""
        location = params.get("gl")
        if location:
            normalized_location = str(location).replace("&location=", "").strip()
            if normalized_location:
                location_hint = f"Target location: {normalized_location}."

        site_hint = ""
        if source_sites:
            normalized_sites = [f"site:{site.replace('site:', '')}" for site in source_sites]
            site_hint = f"Search scope: {' OR '.join(normalized_sites)}."

        return (
            "You are a job sourcing assistant.\n"
            "Use Google Search grounding and return only direct job posting links.\n"
            f"Query: {query}\n"
            f"{site_hint}\n"
            f"{date_hint}\n"
            f"{location_hint}\n"
            "Prefer job postings that explicitly mention visa sponsorship/work authorization support.\n"
            "Output must be valid JSON with the shape:\n"
            '{"results":[{"title":"string","link":"https://...","snippet":"string"}]}\n'
            f"Return at most {limit} results.\n"
            "No markdown, no explanations."
        )

    def _generate_grounded_response(self, prompt: str) -> Dict[str, Any]:
        if self.use_vertex and self.vertex_project_id:
            try:
                return self._call_vertex_generate_content(prompt)
            except Exception as exc:
                logger.warning(
                    f"Vertex search call failed, falling back to AI Studio: {exc}"
                )

        if not self.ai_studio_api_key:
            raise ValueError(
                "GOOGLE_AI_STUDIO_API_KEY is required for Gemini Grounding search."
            )
        return self._call_ai_studio_generate_content(prompt)

    def _call_ai_studio_generate_content(self, prompt: str) -> Dict[str, Any]:
        endpoint = f"{self.AI_STUDIO_BASE_URL}/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        response = requests.post(
            endpoint,
            params={"key": self.ai_studio_api_key},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def _call_vertex_generate_content(self, prompt: str) -> Dict[str, Any]:
        token = self._get_vertex_access_token()
        endpoint = (
            f"{config.VERTEX_API_ENDPOINT}/v1/projects/{self.vertex_project_id}"
            f"/locations/{self.vertex_location}/publishers/google/models/"
            f"{self.vertex_model}:generateContent"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [{"googleSearch": {}}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _get_vertex_access_token() -> str:
        if config.VERTEX_ACCESS_TOKEN:
            return config.VERTEX_ACCESS_TOKEN

        try:
            import google.auth  # type: ignore
            from google.auth.transport.requests import Request  # type: ignore

            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(Request())
            if not credentials.token:
                raise ValueError("No Vertex token obtained from ADC.")
            return credentials.token
        except Exception as exc:
            raise ValueError(
                "Unable to obtain Vertex access token. Set VERTEX_ACCESS_TOKEN "
                "or configure Application Default Credentials."
            ) from exc

    @staticmethod
    def _extract_response_text(payload: Dict[str, Any]) -> str:
        candidates = payload.get("candidates", [])
        text_parts: List[str] = []

        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if text:
                    text_parts.append(text)

        return "\n".join(text_parts).strip()

    def _response_to_results(
        self, payload: Dict[str, Any], max_results: int
    ) -> List[SearchResult]:
        text = self._extract_response_text(payload)
        records = self._extract_records(text)

        results: List[SearchResult] = []
        seen_links: set[str] = set()

        for record in records:
            link = self._clean_url(record.get("link", ""))
            if not link or link in seen_links:
                continue

            seen_links.add(link)
            title = (record.get("title") or "").strip() or link
            snippet = (record.get("snippet") or "").strip()
            results.append(
                SearchResult(
                    title=title,
                    link=link,
                    snippet=snippet,
                    raw_data=record,
                )
            )

            if len(results) >= max_results:
                break

        return results

    def _extract_records(self, response_text: str) -> List[Dict[str, Any]]:
        parsed = self._try_parse_json_response(response_text)
        if parsed is not None:
            return parsed

        # Fallback: extract links from plain text.
        urls = self._extract_urls(response_text)
        return [{"title": url, "link": url, "snippet": ""} for url in urls]

    def _try_parse_json_response(
        self, response_text: str
    ) -> Optional[List[Dict[str, Any]]]:
        if not response_text:
            return []

        candidate_blocks = [response_text]

        first_brace = response_text.find("{")
        last_brace = response_text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate_blocks.append(response_text[first_brace : last_brace + 1])

        first_bracket = response_text.find("[")
        last_bracket = response_text.rfind("]")
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            candidate_blocks.append(response_text[first_bracket : last_bracket + 1])

        for block in candidate_blocks:
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue

            if isinstance(data, dict):
                if isinstance(data.get("results"), list):
                    return [
                        self._normalize_record(item)
                        for item in data["results"]
                        if isinstance(item, dict)
                    ]
                return [self._normalize_record(data)]

            if isinstance(data, list):
                normalized_records = []
                for item in data:
                    if isinstance(item, dict):
                        normalized_records.append(self._normalize_record(item))
                    elif isinstance(item, str):
                        normalized_records.append(
                            {"title": item, "link": item, "snippet": ""}
                        )
                return normalized_records

        return None

    @staticmethod
    def _normalize_record(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": str(item.get("title", "")).strip(),
            "link": str(item.get("link", "")).strip(),
            "snippet": str(item.get("snippet", "")).strip(),
        }

    @staticmethod
    def _extract_urls(text: str) -> List[str]:
        if not text:
            return []
        pattern = r"https?://[^\s\"'<>]+"
        urls = re.findall(pattern, text)
        deduped: List[str] = []
        seen = set()
        for url in urls:
            cleaned = GeminiGroundingSearchEngine._clean_url(url)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                deduped.append(cleaned)
        return deduped

    @staticmethod
    def _clean_url(url: str) -> str:
        cleaned = url.strip().rstrip(".,);")
        return cleaned


class GoogleSearchEngine(GeminiGroundingSearchEngine):
    """
    Backward-compatible alias. Uses Gemini Grounding internally.
    """


class BingSearchEngine(GeminiGroundingSearchEngine):
    """
    Backward-compatible alias. Uses Gemini Grounding internally.
    """


class BraveSearchEngine(GeminiGroundingSearchEngine):
    """
    Backward-compatible alias. Uses Gemini Grounding internally.
    """


class WebSearchEngineFactory:
    _instances: Dict[str, WebSearchEngine] = {}

    @staticmethod
    def get_search_engine(engine_name: Optional[str] = None) -> WebSearchEngine:
        legacy_to_new = {
            GOOGLE: GEMINI_GROUNDING,
            BING: GEMINI_GROUNDING,
            BRAVE: GEMINI_GROUNDING,
        }

        available_engines = [
            legacy_to_new.get(name.lower(), name.lower())
            for name in config.ALLOWED_SEARCH_ENGINES
        ]

        if engine_name is None:
            engine_name = config.DEFAULT_SEARCH_ENGINE
        engine_name = engine_name.lower()
        normalized_engine_name = legacy_to_new.get(engine_name, engine_name)

        if normalized_engine_name not in available_engines and engine_name not in legacy_to_new:
            raise ValueError(
                f"Search engine '{engine_name}' is not allowed. "
                f"Allowed engines: {config.ALLOWED_SEARCH_ENGINES}"
            )

        cache_key = normalized_engine_name
        if cache_key in WebSearchEngineFactory._instances:
            return WebSearchEngineFactory._instances[cache_key]

        if normalized_engine_name == GEMINI_GROUNDING:
            instance = GeminiGroundingSearchEngine()
        else:
            raise ValueError(f"Unknown search engine: {engine_name}")

        WebSearchEngineFactory._instances[cache_key] = instance
        return instance
