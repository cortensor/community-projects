from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import aiohttp


class CortensorClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 90,
        session_id: Optional[int] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session_id = session_id
        self._client: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "CortensorClient":
        self._client = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client:
            await self._client.close()

    @property
    def client(self) -> aiohttp.ClientSession:
        if not self._client:
            raise RuntimeError("Client session not initialized")
        return self._client

    async def summarize(self, prompt: str, **kwargs) -> str:
        # Accepts extra Cortensor params via kwargs
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "prompt_type": kwargs.get("prompt_type", 0),
            "prompt_template": kwargs.get("prompt_template", ""),
            "stream": False,
            "timeout": self.timeout,
            "precommit_timeout": kwargs.get("precommit_timeout", 90),
            "client_reference": kwargs.get("client_reference", "user-request-123"),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.95),
            "top_k": kwargs.get("top_k", 40),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
        }
        # Use sessionId in URL if present, else in body
        if self.session_id is not None:
            url = f"{self.base_url}/api/v1/completions/{self.session_id}"
        else:
            url = f"{self.base_url}/api/v1/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with self.client.post(url, headers=headers, json=payload) as resp:
            data = await resp.json(content_type=None)
            if resp.status >= 300:
                raise RuntimeError(
                    f"Cortensor error {resp.status}: {data!r}"
                )
            return self._extract_text(data)

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> str:
        # Try OpenAI-style response first
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            text = choices[0].get("text") or choices[0].get("message", {}).get("content")
            if text:
                return text

        # Fallbacks used by some Router builds
        if "completion" in data and isinstance(data["completion"], str):
            return data["completion"]
        if "data" in data and isinstance(data["data"], str):
            return data["data"]

        return str(data)

    async def healthcheck(self) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/api/v1/info"
        async with self.client.get(url, headers=headers) as resp:
            return await resp.json(content_type=None)


async def summarize_text(*args: Any, **kwargs: Any) -> str:
    async with CortensorClient(*args, **kwargs) as client:
        return await client.summarize(kwargs.get("prompt", ""))


async def check_router(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    async with CortensorClient(*args, **kwargs) as client:
        return await client.healthcheck()
