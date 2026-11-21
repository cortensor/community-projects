from __future__ import annotations

import os
import re
from typing import Protocol

import httpx

from .models import IssueAssessment, IssueInput


class ModelError(RuntimeError):
    pass


class ModelClient(Protocol):
    def review_issue(self, issue: IssueInput, assessment: IssueAssessment) -> str: ...


class FakeModelClient:
    def __init__(self, response: str | None = None) -> None:
        self.response = response

    def review_issue(self, issue: IssueInput, assessment: IssueAssessment) -> str:
        if self.response is not None:
            return self.response
        return (
            f"Issue #{issue.number} is {assessment.severity}. "
            f"Reproduction score is {assessment.repro_score}/100."
        )


class OpenAICompatibleModelClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("CORTENSOR_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.api_key = api_key or os.getenv("CORTENSOR_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("CORTENSOR_MODEL") or os.getenv("OPENAI_MODEL", "")
        self.client = client or httpx.Client(timeout=30.0)

    def review_issue(self, issue: IssueInput, assessment: IssueAssessment) -> str:
        if not self.model:
            raise ModelError("model name is required")
        prompt = (
            "Review this issue triage fact set and return two short sentences. "
            "Mention the main risk and the most useful missing evidence.\n\n"
            f"Issue: {issue.title}\n"
            f"Labels: {', '.join(issue.labels)}\n"
            f"Severity: {assessment.severity}\n"
            f"Categories: {', '.join(assessment.categories)}\n"
            f"Missing reproduction fields: {', '.join(assessment.missing_repro_fields)}"
        )
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a concise QA triage reviewer."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": 512,
            },
        )
        response.raise_for_status()
        payload = response.json()
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError("chat completion response has no message content") from exc
        if content is None:
            raise ModelError("empty model response")
        cleaned = re.sub(r"<think>.*?</think>", "", str(content), flags=re.DOTALL).strip()
        if not cleaned:
            raise ModelError("empty model response")
        return cleaned

