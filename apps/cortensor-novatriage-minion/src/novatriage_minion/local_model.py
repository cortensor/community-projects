"""OpenMinion config builder and zero-cost OpenAI-compatible deterministic model server."""

from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any
from urllib.parse import urlparse

from openminion import OpenMinionConfig


_ADDRESS_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
_SOL_PATH_RE = re.compile(r"([A-Za-z0-9_./\\-]+\.sol)\b")
_KV_RE = re.compile(r"([a-zA-Z0-9_]+)=([^\s,;]+)")


def _parse_kv_hints(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _KV_RE.finditer(text)}


def _extract_tool_names(tools_payload: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for item in tools_payload:
        if not isinstance(item, dict):
            continue
        fn = item.get("function")
        if isinstance(fn, dict) and fn.get("name"):
            names.append(str(fn["name"]))
        elif item.get("name"):
            names.append(str(item["name"]))
    return names


_SYNTHETIC_USER_PREFIXES = (
    "CURRENT TASK",
    "Continue the active task",
    "Original user request for this turn:",
)


def _last_user_turn_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    last_user_idx = -1
    last_user_text = ""
    for idx, msg in enumerate(messages):
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(
                    str(part.get("text") or "")
                    for part in content
                    if isinstance(part, dict)
                )
            else:
                text = ""
            if text.lstrip().startswith(_SYNTHETIC_USER_PREFIXES):
                continue
            last_user_idx = idx
            last_user_text = text
    if last_user_idx == -1:
        return "", []
    return last_user_text, messages[last_user_idx + 1 :]


def _called_tools_in_turn(turn_tail: list[dict[str, Any]]) -> list[tuple[str, Any]]:
    results: list[tuple[str, Any]] = []
    id_to_name: dict[str, str] = {}
    for msg in turn_tail:
        if msg.get("role") == "assistant" and isinstance(msg.get("tool_calls"), list):
            for tc in msg["tool_calls"]:
                if isinstance(tc, dict):
                    tc_id = str(tc.get("id") or "")
                    fn_name = str(((tc.get("function") or {}).get("name")) or "")
                    if tc_id and fn_name:
                        id_to_name[tc_id] = fn_name
        elif msg.get("role") == "tool":
            tc_id = str(msg.get("tool_call_id") or "")
            name = str(msg.get("name") or id_to_name.get(tc_id, ""))
            raw_content = msg.get("content")
            parsed: Any = raw_content
            if isinstance(raw_content, str):
                try:
                    parsed = json.loads(raw_content)
                except json.JSONDecodeError:
                    parsed = raw_content
            results.append((name, parsed))
    return results


def _extract_json_dict(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    first_brace = text.find("{")
    if first_brace == -1:
        return None
    try:
        obj, _ = decoder.raw_decode(text[first_brace:])
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        return None
    return None


def _unwrap_tool_payload(payload: Any) -> dict[str, Any]:
    current: Any = payload
    for _ in range(6):
        if isinstance(current, str):
            decoded = _extract_json_dict(current)
            if decoded is not None:
                current = decoded
                continue
            return {}
        if not isinstance(current, dict):
            return {}
        if isinstance(current.get("outputs"), dict):
            current = current["outputs"]
            continue
        if isinstance(current.get("data"), dict):
            current = current["data"]
            continue
        if isinstance(current.get("output"), dict):
            current = current["output"]
            continue
        if isinstance(current.get("summary"), str) and "{" in current["summary"]:
            decoded = _extract_json_dict(current["summary"])
            if decoded is not None:
                current = decoded
                continue
        if isinstance(current.get("content"), str) and "{" in current["content"]:
            decoded = _extract_json_dict(current["content"])
            if decoded is not None:
                current = decoded
                continue
        break
    return dict(current) if isinstance(current, dict) else {}


def _tool_call_response(model: str, call_id: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-novatriage-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(arguments, ensure_ascii=True),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 32, "total_tokens": 152},
    }


def _text_response(model: str, content: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-novatriage-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 150, "completion_tokens": 80, "total_tokens": 230},
    }


def _build_report_from_tool_outputs(
    user_text: str,
    called: list[tuple[str, Any]],
) -> dict[str, Any]:
    hints = _parse_kv_hints(user_text)
    solidity_data: dict[str, Any] | None = None
    preflight_data: dict[str, Any] | None = None
    x402_data: dict[str, Any] | None = None
    memory_hits: list[str] = []
    delegations: list[dict[str, Any]] = []

    for tool_name, raw_payload in called:
        data = _unwrap_tool_payload(raw_payload)
        if tool_name == "analyze_solidity_contract":
            solidity_data = data
        elif tool_name == "fetch_token_onchain_preflight":
            preflight_data = data
        elif tool_name == "probe_x402_endpoint":
            x402_data = data
        elif tool_name == "recall_triage_memory":
            for m in data.get("matches") or []:
                memory_hits.append(json.dumps(m, ensure_ascii=True)[:200])
        elif tool_name == "transfer_to_solidity_auditor_minion":
            if isinstance(data.get("solidity_audit"), (dict, str)):
                solidity_data = _unwrap_tool_payload(data["solidity_audit"])
            elif "risk_score" in data and "findings" in data:
                solidity_data = data
            delegations.append(
                {
                    "agent_name": "solidity_auditor_minion",
                    "role": "Static Solidity Auditor (READ_ONLY)",
                    "tool_allowlist": ["analyze_solidity_contract"],
                    "run_state": "completed",
                    "summary": f"Scanned {solidity_data.get('contract_label', 'contract') if solidity_data else 'contract'}",
                }
            )
        elif tool_name == "transfer_to_recon_minion":
            if data.get("token_preflight") is not None:
                preflight_data = _unwrap_tool_payload(data["token_preflight"])
            if data.get("x402_probe") is not None:
                x402_data = _unwrap_tool_payload(data["x402_probe"])
            delegations.append(
                {
                    "agent_name": "recon_minion",
                    "role": "On-Chain & x402 Preflight Recon (READ_ONLY)",
                    "tool_allowlist": ["fetch_token_onchain_preflight", "probe_x402_endpoint"],
                    "run_state": "completed",
                    "summary": "Verified live token preflight and HTTP 402 payment challenge",
                }
            )

    if solidity_data is None:
        solidity_data = {
            "contract_label": hints.get("target_name", "unknown.sol"),
            "lines_scanned": 0,
            "risk_score": 0,
            "risk_tier": "MINIMAL",
            "finding_count": 0,
            "findings": [],
        }

    score = int(solidity_data.get("risk_score", 0))
    if preflight_data and str(preflight_data.get("is_honeypot", "")).strip() == "1":
        score = max(score, 90)
    if score >= 75:
        tier, rec = "CRITICAL", "BLOCK"
    elif score >= 45:
        tier, rec = "HIGH", "MANUAL_REVIEW"
    elif score >= 20:
        tier, rec = "MEDIUM", "PROCEED_WITH_CAUTION"
    elif score > 0:
        tier, rec = "LOW", "PROCEED_WITH_CAUTION"
    else:
        tier, rec = "MINIMAL", "CLEAR"

    target_name = hints.get("target_name") or solidity_data.get("contract_label") or "target"
    finding_count = int(solidity_data.get("finding_count", 0))
    x402_status = x402_data.get("challenge_status") if x402_data else None
    summary = (
        f"NovaTriage Minion completed risk triage for {target_name}: "
        f"risk_score={score}/100 ({tier}), solidity_findings={finding_count}, "
        f"recommendation={rec}"
        + (f", x402_challenge_http={x402_status}" if x402_status is not None else "")
        + "."
    )
    return {
        "target_name": target_name,
        "overall_risk_score": score,
        "overall_risk_tier": tier,
        "recommendation": rec,
        "solidity_audit": solidity_data,
        "token_preflight": preflight_data,
        "x402_probe": x402_data,
        "delegations": delegations,
        "memory_hits": memory_hits,
        "executive_summary": summary,
    }


def _handle_chat_completion(body: dict[str, Any]) -> dict[str, Any]:
    model = str(body.get("model") or "novatriage-local-deterministic-v1")
    messages = list(body.get("messages") or [])
    tool_names = _extract_tool_names(list(body.get("tools") or []))
    if tool_names == ["submit_output"]:
        return _text_response(model, "{}")
    user_text, turn_tail = _last_user_turn_messages(messages)
    called = _called_tools_in_turn(turn_tail)
    called_names = [name for name, _ in called]
    hints = _parse_kv_hints(user_text)

    # Multi-turn follow-up detection: prior assistant turn exists and user asks a follow-up question
    prior_user_count = sum(1 for m in messages if m.get("role") == "user")
    if prior_user_count >= 2 and "FOLLOWUP:" in user_text:
        prior_reports = [
            m.get("content", "")
            for m in messages[:-1]
            if m.get("role") == "assistant" and m.get("content")
        ]
        if prior_reports:
            parsed = _extract_json_dict(str(prior_reports[-1]))
            if parsed and "executive_summary" in parsed:
                findings = ((parsed.get("solidity_audit") or {}).get("findings") or [])
                top_rules = ", ".join(f"{f.get('rule_id')}@L{f.get('line')}" for f in findings[:3]) or "none"
                return _text_response(
                    model,
                    f"Session follow-up grounded in prior turn: {parsed['executive_summary']} Top rules: {top_rules}.",
                )
        return _text_response(
            model,
            "Session follow-up grounded in prior turn context: No prior report found.",
        )

    # Explicit freeze escalation test path (tests dangerous=True fail-closed denial)
    if "TEST_FREEZE_ESCALATION" in user_text and "publish_emergency_freeze_notice" in tool_names:
        if "publish_emergency_freeze_notice" not in called_names:
            return _tool_call_response(
                model,
                "call_freeze_1",
                "publish_emergency_freeze_notice",
                {
                    "target_name": hints.get("target_name", "VulnerableVault.sol"),
                    "reason": "Critical reentrancy & delegatecall exposure",
                },
            )
        freeze_payload = called[-1][1]
        return _text_response(model, json.dumps({"freeze_result": freeze_payload}, ensure_ascii=True))

    # ReconMinion subagent path
    if (
        "fetch_token_onchain_preflight" in tool_names
        and "probe_x402_endpoint" in tool_names
        and "transfer_to_recon_minion" not in tool_names
    ):
        addr_match = _ADDRESS_RE.search(user_text)
        token_addr = hints.get("token_address") or (addr_match.group(0) if addr_match else "")
        chain_id = hints.get("chain_id", "base")
        x402_url = hints.get("x402_base_url", "")
        if token_addr and "fetch_token_onchain_preflight" not in called_names:
            return _tool_call_response(
                model,
                "call_preflight_1",
                "fetch_token_onchain_preflight",
                {"token_address": token_addr, "chain_id": chain_id},
            )
        if "probe_x402_endpoint" not in called_names:
            return _tool_call_response(
                model,
                "call_x402_1",
                "probe_x402_endpoint",
                {"base_url": x402_url, "resource_path": "/api/v1/solidity-triage"},
            )
        preflight = None
        x402_res = None
        for cname, cdata in called:
            unwrapped = _unwrap_tool_payload(cdata)
            if cname == "fetch_token_onchain_preflight":
                preflight = unwrapped
            elif cname == "probe_x402_endpoint":
                x402_res = unwrapped
        return _text_response(
            model,
            json.dumps({"token_preflight": preflight, "x402_probe": x402_res}, ensure_ascii=True),
        )

    # SolidityAuditorMinion subagent path
    if "analyze_solidity_contract" in tool_names and "transfer_to_solidity_auditor_minion" not in tool_names:
        sol_match = _SOL_PATH_RE.search(user_text)
        sol_path = hints.get("contract_path") or (sol_match.group(1) if sol_match else "")
        if "analyze_solidity_contract" not in called_names:
            return _tool_call_response(
                model,
                "call_sol_1",
                "analyze_solidity_contract",
                {"file_path": sol_path, "contract_label": hints.get("target_name", "")},
            )
        sol_res = _unwrap_tool_payload(called[-1][1])
        return _text_response(
            model,
            json.dumps(sol_res, ensure_ascii=True),
        )

    # Coordinator path (orchestrates memory -> SolidityAuditorMinion -> ReconMinion -> write_triage_report -> JSON report)
    if (
        "recall_triage_memory" in tool_names
        and hints.get("memory_bundle")
        and "recall_triage_memory" not in called_names
    ):
        return _tool_call_response(
            model,
            "call_mem_1",
            "recall_triage_memory",
            {"bundle_path": hints["memory_bundle"], "query": ""},
        )

    if "transfer_to_solidity_auditor_minion" in tool_names and "transfer_to_solidity_auditor_minion" not in called_names:
        sol_match = _SOL_PATH_RE.search(user_text)
        sol_path = hints.get("contract_path") or (sol_match.group(1) if sol_match else "")
        return _tool_call_response(
            model,
            "call_handoff_sol_1",
            "transfer_to_solidity_auditor_minion",
            {"message": f"Audit Solidity contract_path={sol_path} target_name={hints.get('target_name', 'contract.sol')}"},
        )

    if "transfer_to_recon_minion" in tool_names and "transfer_to_recon_minion" not in called_names:
        addr_match = _ADDRESS_RE.search(user_text)
        token_addr = hints.get("token_address") or (addr_match.group(0) if addr_match else "")
        msg = f"Run preflight recon token_address={token_addr} chain_id={hints.get('chain_id', 'base')}"
        if hints.get("x402_base_url"):
            msg += f" x402_base_url={hints['x402_base_url']}"
        return _tool_call_response(model, "call_handoff_recon_1", "transfer_to_recon_minion", {"message": msg})

    report_dict = _build_report_from_tool_outputs(user_text, called)

    if (
        "write_triage_report" in tool_names
        and hints.get("output_path")
        and "write_triage_report" not in called_names
    ):
        return _tool_call_response(
            model,
            "call_write_1",
            "write_triage_report",
            {
                "output_path": hints["output_path"],
                "report_json": json.dumps(report_dict, ensure_ascii=True),
            },
        )

    return _text_response(model, json.dumps(report_dict, ensure_ascii=True))


@dataclass
class NovaTriageLocalModelServer:
    """In-process OpenAI-compatible HTTP server so OpenMinion's real OpenAIProvider runs at $0 cost."""

    server: ThreadingHTTPServer
    thread: threading.Thread
    base_url: str

    @classmethod
    def start(cls) -> "NovaTriageLocalModelServer":
        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def do_GET(self) -> None:  # noqa: N802
                if urlparse(self.path).path.endswith("/models"):
                    payload = {"object": "list", "data": [{"id": "novatriage-local-deterministic-v1", "object": "model"}]}
                    body = json.dumps(payload).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length > 0 else b"{}"
                req_payload = json.loads(raw.decode("utf-8"))
                resp_payload = _handle_chat_completion(req_payload)
                body = json.dumps(resp_payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        return cls(server=httpd, thread=thread, base_url=f"http://127.0.0.1:{port}/v1")

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def __enter__(self) -> "NovaTriageLocalModelServer":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def build_openminion_config_file(
    config_path: Path,
    *,
    provider: str = "local",
    model: str = "",
    local_base_url: str = "",
) -> Path:
    """Write a canonical OpenMinion 0.1.24 JSON config for local, Cortensor, or OpenAI providers."""
    selected = (provider or os.getenv("NOVATRIAGE_PROVIDER", "local")).strip().lower()
    cfg = OpenMinionConfig().to_dict()

    if selected == "local":
        resolved_provider = "openai"
        resolved_model = model or "novatriage-local-deterministic-v1"
        cfg["providers"]["openai"]["base_url"] = local_base_url
        cfg["providers"]["openai"]["api_key"] = "novatriage-local-zero-cost-key"
        cfg["providers"]["openai"]["model"] = resolved_model
        cfg["providers"]["openai"]["tool_call_strategy"] = "native"
    elif selected == "cortensor":
        resolved_provider = "cortensor"
        resolved_model = model or os.getenv("NOVATRIAGE_MODEL", "gpt-oss-20b")
        if os.getenv("CORTENSOR_API_URL"):
            cfg["providers"]["cortensor"]["base_url"] = os.getenv("CORTENSOR_API_URL")
        if os.getenv("CORTENSOR_API_KEY"):
            cfg["providers"]["cortensor"]["api_key"] = os.getenv("CORTENSOR_API_KEY")
        cfg["providers"]["cortensor"]["model"] = resolved_model
    else:
        resolved_provider = selected
        resolved_model = model or os.getenv("NOVATRIAGE_MODEL", "gpt-4.1-mini")
        if selected in cfg["providers"]:
            cfg["providers"][selected]["model"] = resolved_model
            if os.getenv("NOVATRIAGE_BASE_URL"):
                cfg["providers"][selected]["base_url"] = os.getenv("NOVATRIAGE_BASE_URL")
            if os.getenv("NOVATRIAGE_API_KEY"):
                cfg["providers"][selected]["api_key"] = os.getenv("NOVATRIAGE_API_KEY")

    # Note: OpenMinion 0.1.24 requires default_channel="console" so Agent.run() passes inbound authenticity!
    cfg["runtime"]["agent_loop_tool_result_max_chars"] = 16000
    cfg["agents"]["default"] = {
        "provider": resolved_provider,
        "model": resolved_model,
        "default_channel": "console",
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return config_path
