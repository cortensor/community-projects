"""The scripted provider speaks OpenAI's protocol well enough for OpenMinion."""

from __future__ import annotations

import json

from repo_triager.scripted_provider import ScriptedProvider

SCRIPTS = {
    "demo": {
        "steps": [
            {"kind": "tool", "tool": "get_issue", "args": {"issue_number": 1}},
            {"kind": "text", "content": "{\"done\": true}"},
        ],
        "output": {"done": True},
    }
}


def _post(url: str, payload: dict) -> dict:
    import urllib.request

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode())


def _user(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


def test_scripted_tool_call_then_text(tmp_path):
    log = tmp_path / "log.jsonl"
    with ScriptedProvider(scripts=SCRIPTS, port=0, log_path=log) as provider:
        first = _post(
            f"{provider.base_url}/chat/completions",
            {
                "model": "scripted-1",
                "messages": _user("SCENARIO:demo please triage"),
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_issue",
                            "parameters": {"title": "GetIssueArgs", "type": "object"},
                        },
                    }
                ],
            },
        )
        call = first["choices"][0]["message"]["tool_calls"][0]
        assert call["function"]["name"] == "get_issue"
        assert json.loads(call["function"]["arguments"]) == {"issue_number": 1}

        second = _post(
            f"{provider.base_url}/chat/completions",
            {
                "model": "scripted-1",
                "messages": [
                    *_user("SCENARIO:demo please triage"),
                    {"role": "assistant", "content": None},
                    {"role": "tool", "content": "{\"number\": 1}"},
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_issue",
                            "parameters": {"title": "GetIssueArgs", "type": "object"},
                        },
                    }
                ],
            },
        )
        assert second["choices"][0]["message"]["content"] == "{\"done\": true}"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    assert [record["step"] for record in records] == [0, 1]


def test_auto_fact_extraction_gets_an_empty_candidate_list():
    with ScriptedProvider(scripts=SCRIPTS, port=0) as provider:
        response = _post(
            f"{provider.base_url}/chat/completions",
            {
                "model": "scripted-1",
                "messages": _user("SCENARIO:demo hello"),
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "submit_output",
                            "parameters": {"title": "UserMessageCandidateReport"},
                        },
                    }
                ],
            },
        )
        call = response["choices"][0]["message"]["tool_calls"][0]
        args = json.loads(call["function"]["arguments"])
        assert args["items"] == []


def test_internal_schemas_get_wellformed_answers():
    with ScriptedProvider(scripts=SCRIPTS, port=0) as provider:
        for title, key in (("FreshnessContract", "answer_mode"), ("ClosureJudgment", "next_action")):
            response = _post(
                f"{provider.base_url}/chat/completions",
                {
                    "model": "scripted-1",
                    "messages": _user("SCENARIO:demo hello"),
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "submit_output", "parameters": {"title": title}},
                        }
                    ],
                },
            )
            args = json.loads(
                response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
            )
            assert key in args


def test_tool_call_outside_the_offered_tools_is_an_error():
    with ScriptedProvider(scripts=SCRIPTS, port=0) as provider:
        import urllib.error

        try:
            _post(
                f"{provider.base_url}/chat/completions",
                {
                    "model": "scripted-1",
                    "messages": _user("SCENARIO:demo x"),
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "other_tool",
                                "parameters": {"title": "T", "type": "object"},
                            },
                        }
                    ],
                },
            )
        except urllib.error.HTTPError as exc:
            assert exc.code == 500
        else:  # pragma: no cover
            raise AssertionError("expected the provider to reject an impossible script")


def test_models_endpoint():
    with ScriptedProvider(scripts=SCRIPTS, port=0) as provider:
        import urllib.request

        with urllib.request.urlopen(f"{provider.base_url}/models", timeout=10) as response:
            payload = json.loads(response.read().decode())
        assert payload["data"][0]["id"] == "scripted-1"
