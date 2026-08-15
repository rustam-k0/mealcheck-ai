from __future__ import annotations

import base64
from aiohttp import FormData

from banana_bot.domain import TextResult
from banana_bot.http import AsyncHTTPClient, ProviderError


class UnifiedAIAdapter:
    """Provider-neutral adapter for an OpenAI-compatible gateway."""

    def __init__(self, client: AsyncHTTPClient, api_key: str, base_url: str, provider: str = "gateway"):
        self.client, self.base_url, self.provider = client, base_url.rstrip("/"), provider
        self.headers = {"Authorization": f"Bearer {api_key}"}

    @staticmethod
    def _text(payload: dict) -> str:
        if payload.get("output_text"):
            return payload["output_text"]
        choices = payload.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            return content if isinstance(content, str) else "".join(x.get("text", "") for x in content)
        return "".join(part.get("text", "") for item in payload.get("output", []) for part in item.get("content", []) if part.get("type") in {"output_text", "text"})

    async def complete(self, model: str, system: str, user: str, *, image: bytes | None = None, max_tokens: int = 1800, response_schema: dict | None = None) -> TextResult:
        content: str | list[dict] = user
        if image is not None:
            encoded = base64.b64encode(image).decode("ascii")
            content = [{"type": "text", "text": user}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}]
        response_format = ({"type": "json_schema", "json_schema": {"name": "food_result", "strict": True, "schema": response_schema}}
                           if response_schema else {"type": "json_object"})
        payload = await self.client.request_json("POST", f"{self.base_url}/chat/completions", headers=self.headers, json={
            "model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
            "max_tokens": max_tokens, "response_format": response_format,
        })
        value = self._text(payload).strip()
        if not value:
            raise ProviderError(502, "Gateway returned no text")
        return TextResult(text=value, provider=self.provider, model=model)

    async def transcribe(self, model: str, audio: bytes) -> TextResult:
        def form() -> FormData:
            value = FormData(); value.add_field("model", model); value.add_field("response_format", "json")
            value.add_field("file", audio, filename="voice.ogg", content_type="audio/ogg"); return value
        payload = await self.client.request_json("POST", f"{self.base_url}/audio/transcriptions", headers=self.headers, data_factory=form)
        value = payload.get("text", "").strip()
        if not value:
            raise ProviderError(502, "Transcription returned no text")
        return TextResult(text=value, provider=self.provider, model=model)
