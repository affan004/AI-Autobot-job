from __future__ import annotations

from typing import List, Union

import requests
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from loguru import logger

import config
from constants import AI_STUDIO, VERTEX


load_dotenv()


class GeminiRestChatModel:
    """
    Minimal chat model adapter for Gemini via AI Studio or Vertex AI REST APIs.
    """

    AI_STUDIO_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, provider: str, api_key: str):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = config.GEMINI_LLM_MODEL
        self.vertex_project_id = config.VERTEX_PROJECT_ID
        self.vertex_location = config.VERTEX_LOCATION
        self.vertex_model = config.VERTEX_GEMINI_MODEL

    def invoke(self, prompt: Union[str, List[BaseMessage]]) -> AIMessage:
        prompt_text = self._messages_to_prompt(prompt)
        payload = self._generate(prompt_text)
        text = self._extract_response_text(payload)
        return AIMessage(content=text)

    def _generate(self, prompt_text: str) -> dict:
        if self.provider == VERTEX:
            return self._call_vertex(prompt_text)
        return self._call_ai_studio(prompt_text)

    def _call_ai_studio(self, prompt_text: str) -> dict:
        endpoint = f"{self.AI_STUDIO_BASE_URL}/models/{self.model}:generateContent"
        response = requests.post(
            endpoint,
            params={"key": self.api_key},
            json={
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {"temperature": 0.2},
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def _call_vertex(self, prompt_text: str) -> dict:
        if not self.vertex_project_id:
            raise ValueError("VERTEX_PROJECT_ID is required when LLM_PROVIDER=vertex")

        token = self._get_vertex_access_token()
        endpoint = (
            f"{config.VERTEX_API_ENDPOINT}/v1/projects/{self.vertex_project_id}"
            f"/locations/{self.vertex_location}/publishers/google/models/"
            f"{self.vertex_model}:generateContent"
        )
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
                "generationConfig": {"temperature": 0.2},
            },
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
                raise ValueError("No token received from ADC.")
            return credentials.token
        except Exception as exc:
            raise ValueError(
                "Unable to obtain Vertex access token. Set VERTEX_ACCESS_TOKEN "
                "or configure Application Default Credentials."
            ) from exc

    @staticmethod
    def _messages_to_prompt(prompt: Union[str, List[BaseMessage]]) -> str:
        if isinstance(prompt, str):
            return prompt

        lines = []
        for message in prompt:
            role = message.type.upper()
            content = message.content
            if isinstance(content, list):
                rendered = " ".join(str(item) for item in content)
            else:
                rendered = str(content)
            lines.append(f"{role}: {rendered}")
        return "\n".join(lines)

    @staticmethod
    def _extract_response_text(payload: dict) -> str:
        candidates = payload.get("candidates", [])
        text_parts: List[str] = []

        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if text:
                    text_parts.append(text)

        text = "\n".join(text_parts).strip()
        if not text:
            logger.warning("Gemini response had no text parts; returning empty string")
        return text


class AIAdapter:
    """
    Adapter for multiple LLM providers:
    - ai_studio (default)
    - vertex
    - tensorzero
    """

    def __init__(self, config_data: dict, api_key: str):
        provider = config.LLM_PROVIDER.lower()
        logger.info(f"Initializing AIAdapter with provider='{provider}'")

        if provider == "tensorzero":
            gateway_url = f"{config.TENSORZERO_GATEWAY_URL}/openai/v1"
            self.model = ChatOpenAI(
                base_url=gateway_url,
                temperature=0.4,
                model=f"tensorzero::function_name::{config.TENSORZERO_DEFAULT_FUNCTION}",
            )
            return

        if provider not in {AI_STUDIO, VERTEX}:
            raise ValueError(
                "Unsupported LLM_PROVIDER. Use one of: ai_studio, vertex, tensorzero."
            )

        effective_api_key = api_key or config.GOOGLE_AI_STUDIO_API_KEY
        if provider == AI_STUDIO and not effective_api_key:
            raise ValueError(
                "Missing API key for AI Studio. Set llm_api_key in secrets.yaml "
                "or GOOGLE_AI_STUDIO_API_KEY in .env."
            )

        # For Vertex, api_key is not required if ADC / VERTEX_ACCESS_TOKEN is configured.
        self.model = GeminiRestChatModel(provider=provider, api_key=effective_api_key)

    def invoke(self, prompt: Union[str, List[BaseMessage]]) -> BaseMessage:
        try:
            return self.model.invoke(prompt)
        except Exception as exc:
            logger.error(f"Error invoking LLM provider: {exc}")
            raise


class TensorZeroChatModelWrapper:
    """
    Backward-compatible wrapper around an object exposing .invoke(messages).
    """

    def __init__(self, llm):
        self.llm = llm
        logger.debug(f"TensorZeroChatModelWrapper initialized with LLM: {llm}")

    def __call__(self, messages: List[BaseMessage]) -> BaseMessage:
        try:
            reply = self.llm.invoke(messages)
            if isinstance(reply, AIMessage):
                return reply
            if isinstance(reply, str):
                return AIMessage(content=reply)
            return AIMessage(content=str(reply))
        except Exception as exc:
            logger.error(f"Error during LLM invocation within wrapper: {exc}")
            raise

