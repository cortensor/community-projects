"""Single-pass, dual-perspective consensus, MemoryBundle, and Handoff auditor."""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, Sequence
from uuid import uuid4

from openminion.api import APIRuntime, Agent, AgentRunResult, Handoff, subagent
from openminion.modules.memory.portability import (
    MemoryBundle,
    export_bundle,
    import_bundle,
    load_bundle,
    save_bundle,
)
from openminion.modules.policy.grants import PolicyGrantInput
from openminion.modules.runtime.contracts import TurnTelemetry

from cortensor_verifier.models import (
    ApprovalModeLiteral,
    AuditRunBundle,
    ClaimDossier,
    ConsensusVerdict,
    PassTelemetry,
    PublicationResult,
    TelemetrySummary,
    VerifierPassResult,
)
from cortensor_verifier.probe import infer_calibration_status, sanitize_base_url
from cortensor_verifier.runtime_factory import build_isolated_config, create_isolated_runtime
from cortensor_verifier.tools import (
    READ_ONLY_VERIFIER_TOOLS,
    assert_read_only_tools,
    build_scoped_verifier_tools,
    make_publish_consensus_verdict_tool,
)

ApprovalCallback = Callable[[str, dict[str, Any], str], bool]


def _safe_key(raw: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_") or "default"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:48]}_{digest}"


def synthesize_consensus(
    claim_id: str,
    passes: Sequence[VerifierPassResult],
    *,
    disagreement_threshold: float = 0.35,
) -> ConsensusVerdict:
    """Deterministically aggregate verifier passes into a ConsensusVerdict."""
    if not passes:
        raise ValueError("Cannot synthesize ConsensusVerdict from zero passes.")

    pass_list = list(passes)
    mean_confidence = round(
        sum(item.confidence for item in pass_list) / len(pass_list), 6
    )

    if len(pass_list) == 1:
        sole = pass_list[0]
        return ConsensusVerdict(
            claim_id=claim_id,
            final_verdict=sole.verdict,
            agreement_score=1.0,
            mean_confidence=sole.confidence,
            disagreement_summary="Single-pass verification completed.",
            passes=pass_list,
            requires_human_review=(sole.verdict == "INCONCLUSIVE"),
        )

    by_role = {item.pass_role: item for item in pass_list}
    corroborator = by_role.get("corroborator", pass_list[0])
    skeptic = by_role.get("skeptic", pass_list[1])
    conf_gap = abs(corroborator.confidence - skeptic.confidence)

    if (
        corroborator.verdict == skeptic.verdict
        and corroborator.verdict in ("SUPPORTED", "REFUTED")
    ):
        agreement_score = round(max(0.0, min(1.0, 1.0 - conf_gap * 0.5)), 6)
        if conf_gap > disagreement_threshold:
            return ConsensusVerdict(
                claim_id=claim_id,
                final_verdict="INCONCLUSIVE",
                agreement_score=agreement_score,
                mean_confidence=mean_confidence,
                disagreement_summary=(
                    f"Confidence gap {conf_gap:.2f} exceeds threshold "
                    f"{disagreement_threshold:.2f} (corroborator={corroborator.verdict} "
                    f"{corroborator.confidence:.2f}, skeptic={skeptic.verdict} "
                    f"{skeptic.confidence:.2f})."
                ),
                passes=pass_list,
                requires_human_review=True,
            )
        return ConsensusVerdict(
            claim_id=claim_id,
            final_verdict=corroborator.verdict,
            agreement_score=agreement_score,
            mean_confidence=mean_confidence,
            disagreement_summary=(
                f"Corroborator and skeptic agreed on {corroborator.verdict} "
                f"(confidence gap {conf_gap:.2f})."
            ),
            passes=pass_list,
            requires_human_review=False,
        )

    if {corroborator.verdict, skeptic.verdict} == {"SUPPORTED", "REFUTED"}:
        min_conf = min(corroborator.confidence, skeptic.confidence)
        agreement_score = round(
            max(0.0, min(1.0, 0.25 * (1.0 - conf_gap) * (1.0 - min_conf))),
            6,
        )
        return ConsensusVerdict(
            claim_id=claim_id,
            final_verdict="INCONCLUSIVE",
            agreement_score=agreement_score,
            mean_confidence=mean_confidence,
            disagreement_summary=(
                f"Conflicting verdicts: corroborator={corroborator.verdict} "
                f"(confidence={corroborator.confidence:.2f}; {corroborator.rationale[:120]}) "
                f"vs skeptic={skeptic.verdict} (confidence={skeptic.confidence:.2f}; "
                f"{skeptic.rationale[:120]})."
            ),
            passes=pass_list,
            requires_human_review=True,
        )

    if corroborator.verdict == "INCONCLUSIVE" and skeptic.verdict == "INCONCLUSIVE":
        agreement_score = round(max(0.0, min(1.0, 1.0 - conf_gap * 0.5)), 6)
    else:
        agreement_score = round(max(0.0, min(1.0, 0.5 - conf_gap * 0.25)), 6)

    return ConsensusVerdict(
        claim_id=claim_id,
        final_verdict="INCONCLUSIVE",
        agreement_score=agreement_score,
        mean_confidence=mean_confidence,
        disagreement_summary=(
            f"Inconclusive consensus: corroborator={corroborator.verdict} "
            f"(confidence={corroborator.confidence:.2f}; {corroborator.rationale[:100]}) "
            f"vs skeptic={skeptic.verdict} (confidence={skeptic.confidence:.2f}; "
            f"{skeptic.rationale[:100]})."
        ),
        passes=pass_list,
        requires_human_review=True,
    )


def _pass_telemetry_from_run(
    pass_role: str,
    result: AgentRunResult[Any],
) -> tuple[PassTelemetry, TurnTelemetry]:
    stats = dict(result.stats or {})
    meta = dict(result.metadata or {})
    requests = int(stats.get("llm_calls") or meta.get("llm_calls_count") or 0)
    prompt_tokens = int(stats.get("input_tokens") or meta.get("total_input_tokens_used") or 0)
    completion_tokens = int(
        stats.get("output_tokens") or meta.get("total_output_tokens_used") or 0
    )
    latency_ms = int(
        stats.get("duration_ms")
        or meta.get("turn_duration_ms")
        or meta.get("elapsed_ms")
        or 0
    )
    tool_calls = int(stats.get("tool_calls") or 0)
    tool_errors = int(stats.get("tool_errors") or 0)

    pass_tel = PassTelemetry(
        pass_role=pass_role,
        requests=requests,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=latency_ms,
        tool_calls=tool_calls,
        tool_errors=tool_errors,
    )
    retries = int(stats.get("retries") or meta.get("retries") or meta.get("provider_retries") or 0)
    queue_wait_ms = int(stats.get("queue_wait_ms") or meta.get("queue_wait_ms") or 0)
    turn_tel = TurnTelemetry(
        tokens_in=prompt_tokens,
        tokens_out=completion_tokens,
        duration_ms=latency_ms,
        retries=retries,
        queue_wait_ms=queue_wait_ms,
    )
    return pass_tel, turn_tel


def _aggregate_telemetry(
    runs: Sequence[tuple[str, AgentRunResult[Any]]],
    *,
    base_summary: TelemetrySummary | None = None,
) -> TelemetrySummary:
    per_pass: dict[str, PassTelemetry] = (
        dict(base_summary.per_pass) if base_summary else {}
    )
    turn_telemetries: list[dict[str, Any]] = (
        list(base_summary.turn_telemetries) if base_summary else []
    )
    requests = base_summary.requests if base_summary else 0
    prompt_tokens = base_summary.prompt_tokens if base_summary else 0
    completion_tokens = base_summary.completion_tokens if base_summary else 0
    total_latency_ms = base_summary.total_latency_ms if base_summary else 0

    for role, run_result in runs:
        pass_tel, turn_tel = _pass_telemetry_from_run(role, run_result)
        per_pass[role] = pass_tel
        turn_telemetries.append({"pass_role": role, **asdict(turn_tel)})
        requests += pass_tel.requests
        prompt_tokens += pass_tel.prompt_tokens
        completion_tokens += pass_tel.completion_tokens
        total_latency_ms += pass_tel.latency_ms

    return TelemetrySummary(
        requests=requests,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        total_latency_ms=total_latency_ms,
        per_pass=per_pass,
        turn_telemetries=turn_telemetries,
    )


class ConsensusAuditor:
    """Orchestrates evidence-backed verification passes using isolated openminion runtimes."""

    def __init__(
        self,
        *,
        runtime: APIRuntime | None = None,
        preset: str = "openai-compatible",
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str | None = None,
        agent_id: str = "verifier",
        home_root: str | Path | None = None,
        data_root: str | Path | None = None,
        config_path: str | Path | None = None,
        tools: Sequence[Any] | None = None,
        fixture_path: str | Path | None = None,
        allow_private_network: bool = False,
        tool_call_strategy: Literal["native", "hybrid"] = "native",
        timeout_seconds: int | None = None,
        provider_retry_max_attempts: int = 2,
        http_connection_reuse_enabled: bool = False,
        cortensor_api_mode: str = "auto",
        cortensor_session_id: int = 1,
    ) -> None:
        self._explicit_tools = tools is not None
        self.fixture_path = fixture_path
        self.allow_private_network = allow_private_network
        initial_tools = (
            tools
            if tools is not None
            else build_scoped_verifier_tools(
                fixture_path=fixture_path,
                dossier=None,
                allow_private_network=allow_private_network,
            )
        )
        self.tools = assert_read_only_tools(initial_tools)
        self._allowed_tool_names = {item.tool_decl.name for item in self.tools}
        self._runtime = runtime
        self._owns_runtime = runtime is None
        self._publisher_runtime: APIRuntime | None = None
        self.preset = preset
        self.base_url = base_url
        self.model = model
        self.api_key_env = api_key_env
        self.agent_id = agent_id
        self.home_root = home_root
        self.data_root = data_root
        self.config_path = config_path
        self.tool_call_strategy = tool_call_strategy
        self.timeout_seconds = timeout_seconds
        self.provider_retry_max_attempts = provider_retry_max_attempts
        self.http_connection_reuse_enabled = http_connection_reuse_enabled
        self.cortensor_api_mode = cortensor_api_mode
        self.cortensor_session_id = cortensor_session_id

    def __enter__(self) -> "ConsensusAuditor":
        self._ensure_runtime()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._publisher_runtime is not None:
            self._publisher_runtime.close()
            self._publisher_runtime = None
        if self._owns_runtime and self._runtime is not None:
            self._runtime.close()
            self._runtime = None

    def _ensure_runtime(self) -> APIRuntime:
        if self._runtime is None:
            self._runtime = create_isolated_runtime(
                preset=self.preset,
                base_url=self.base_url,
                model=self.model,
                api_key_env=self.api_key_env,
                agent_id=self.agent_id,
                home_root=self.home_root,
                data_root=self.data_root,
                config_path=self.config_path,
                tool_call_strategy=self.tool_call_strategy,
                timeout_seconds=self.timeout_seconds,
                provider_retry_max_attempts=self.provider_retry_max_attempts,
                http_connection_reuse_enabled=self.http_connection_reuse_enabled,
                cortensor_api_mode=self.cortensor_api_mode,
                cortensor_session_id=self.cortensor_session_id,
            )
            self._owns_runtime = True
        return self._runtime

    def _state_root(self) -> Path:
        if self.data_root is not None:
            base = Path(self.data_root)
        else:
            base = Path(self._ensure_runtime().data_root)
        return base if base.name == ".openminion-state" else base / ".openminion-state"

    def _resolve_endpoint_and_model(self, cfg: Any = None) -> tuple[str | None, str | None]:
        """Resolve the effective provider base URL and model without forcing runtime boot."""
        resolved_cfg = cfg
        if resolved_cfg is None:
            resolved_cfg = (
                getattr(self._runtime, "config", None)
                if self._runtime is not None
                else build_isolated_config(
                    preset=self.preset,
                    base_url=self.base_url,
                    model=self.model,
                    persist=False,
                )
            )
        providers = getattr(resolved_cfg, "providers", None) if resolved_cfg is not None else None
        prov_cfg = (
            (
                getattr(providers, "cortensor", None)
                if self.preset == "cortensor-router"
                else getattr(providers, "openai", None)
            )
            if providers is not None
            else None
        )
        base_url = self.base_url or getattr(prov_cfg, "base_url", None)
        model = self.model or getattr(prov_cfg, "model", None)
        return (str(base_url) if base_url else None, str(model) if model else None)

    def _calibration_metadata(self) -> dict[str, str]:
        """Return sanitized calibration provenance fields for ``AuditRunBundle.metadata``."""
        resolved_base_url, resolved_model = self._resolve_endpoint_and_model()
        return {
            "calibration_status": infer_calibration_status(resolved_base_url),
            "calibrated_model": resolved_model or "unknown",
            "endpoint_host": sanitize_base_url(resolved_base_url),
        }

    def _ensure_publisher_runtime(self) -> APIRuntime:
        if self._publisher_runtime is None:
            pub_root = self._state_root() / "publisher_runtime"
            runtime = self._ensure_runtime()
            base_url, model = self._resolve_endpoint_and_model(getattr(runtime, "config", None))
            self._publisher_runtime = create_isolated_runtime(
                preset=self.preset,
                base_url=base_url,
                model=model,
                api_key_env=self.api_key_env,
                agent_id=self.agent_id,
                home_root=pub_root / "home",
                data_root=pub_root / "data",
                tool_call_strategy=self.tool_call_strategy,
                timeout_seconds=self.timeout_seconds,
                provider_retry_max_attempts=self.provider_retry_max_attempts,
                http_connection_reuse_enabled=self.http_connection_reuse_enabled,
                cortensor_api_mode=self.cortensor_api_mode,
                cortensor_session_id=self.cortensor_session_id,
            )
        return self._publisher_runtime

    def _read_only_approval_guard(
        self,
        tool_name: str,
        args: dict[str, Any],
        approval_id: str,
    ) -> bool:
        del args, approval_id
        return tool_name in self._allowed_tool_names

    def _build_instructions(self, pass_role: str) -> str:
        role_directive = {
            "corroborator": (
                "You are the 'corroborator' verifier subagent. Focus on finding and "
                "confirming primary evidence, exact dates, official filings, and verbatim "
                "quotes that support or establish the factual resolution of the claim."
            ),
            "skeptic": (
                "You are the 'skeptic' verifier subagent. Actively search for "
                "counter-evidence, contradictions, missing primary citations, caveats, "
                "ambiguities, or unsupported assumptions before accepting the claim."
            ),
        }.get(
            pass_role,
            f"You are performing a '{pass_role}' evidence verification pass for a Claim Dossier.",
        )
        return (
            f"{role_directive} "
            "Use the provided READ_ONLY evidence tools (calling at most one tool per step; never batch parallel "
            "tool calls or emit extra task_update fields) to gather and verify sources, then respond "
            "with ONLY a single raw RFC-8259 JSON object using double quotes and zero prose or markdown fences "
            "matching the VerifierPassResult schema: "
            '{"verdict": "SUPPORTED"|"REFUTED"|"INCONCLUSIVE", "confidence": 0.9, '
            '"rationale": "concise factual rationale", '
            '"citations": [{"source_id": "...", "title": "...", "url": "...", "excerpt": "...", "published_at": "..."}], '
            f'"pass_role": "{pass_role}"}}'
        )

    def _session_bundle_path(self, session_id: str) -> Path:
        return self._state_root() / "memory_bundles" / f"{_safe_key(session_id)}.json"

    def _paused_thread_path(self, thread_id: str) -> Path:
        return self._state_root() / "paused_threads" / f"{_safe_key(thread_id)}.json"

    def _used_approvals_path(self) -> Path:
        return self._state_root() / "policy_grants" / "used_approvals.json"

    def _load_used_approvals(self) -> dict[str, str]:
        path = self._used_approvals_path()
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return dict(data) if isinstance(data, dict) else {}

    def _mark_approval_used(self, approval_id: str) -> None:
        path = self._used_approvals_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        used = self._load_used_approvals()
        used[approval_id] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(used, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def export_session_memory(
        self,
        session_id: str,
        output_path: str | Path | None = None,
    ) -> MemoryBundle:
        """Export portable openminion MemoryBundle strictly scoped to session_id."""
        bundle_path = self._session_bundle_path(session_id)
        if bundle_path.exists():
            loaded = load_bundle(bundle_path)
            scoped_items = [
                dict(item)
                for item in loaded.items
                if isinstance(item, dict) and item.get("session_id") == session_id
            ]
            bundle = export_bundle(
                scoped_items,
                metadata={
                    **dict(loaded.metadata or {}),
                    "session_id": session_id,
                    "item_count": len(scoped_items),
                },
            )
        else:
            bundle = export_bundle(
                [],
                metadata={"session_id": session_id, "item_count": 0},
            )
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            save_bundle(bundle, out)
        return bundle

    def import_session_memory(
        self,
        session_id: str,
        source: MemoryBundle | str | Path,
    ) -> dict[str, Any]:
        """Import a MemoryBundle into session_id while rejecting foreign-session records."""
        incoming = source if isinstance(source, MemoryBundle) else load_bundle(Path(source))
        import_report = import_bundle(incoming, trust_mode="direct")
        existing = self.export_session_memory(session_id)
        merged_by_id: dict[str, dict[str, Any]] = {
            str(item.get("id", f"existing-{idx}")): dict(item)
            for idx, item in enumerate(existing.items)
        }

        imported_count = 0
        for idx, raw_item in enumerate(incoming.items):
            if not isinstance(raw_item, dict):
                continue
            item_session = raw_item.get("session_id") or (
                raw_item.get("metadata", {}) or {}
            ).get("session_id")
            if item_session not in (None, "", session_id):
                raise ValueError(
                    f"Cross-session MemoryBundle isolation violation: item belongs to "
                    f"{item_session!r}, cannot import into {session_id!r}."
                )
            normalized = dict(raw_item)
            normalized["session_id"] = session_id
            meta = dict(normalized.get("metadata") or {})
            meta["session_id"] = session_id
            normalized["metadata"] = meta
            item_id = str(normalized.get("id") or f"{session_id}:import:{idx}")
            merged_by_id[item_id] = normalized
            imported_count += 1

        updated = export_bundle(
            list(merged_by_id.values()),
            metadata={
                "session_id": session_id,
                "item_count": len(merged_by_id),
                "pass_session_ids": [],
            },
        )
        bundle_path = self._session_bundle_path(session_id)
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        save_bundle(updated, bundle_path)
        return {**import_report, "session_id": session_id, "imported_into_session": imported_count}

    def _persist_session_memory(
        self,
        *,
        session_id: str | None,
        dossier: ClaimDossier,
        consensus: ConsensusVerdict,
        run_id: str | None,
        pass_session_ids: Sequence[str] | None = None,
        memory_bundle_out: str | Path | None = None,
    ) -> MemoryBundle | None:
        if session_id is None and memory_bundle_out is None:
            return None

        citations: list[dict[str, Any]] = []
        seen_cites: set[tuple[str, str]] = set()
        for p in consensus.passes:
            for c in p.citations:
                key = (c.source_id, c.excerpt)
                if key not in seen_cites:
                    seen_cites.add(key)
                    citations.append(c.model_dump(mode="json"))

        effective_session = session_id or "ephemeral"
        existing_bundle = (
            self.export_session_memory(effective_session) if session_id is not None else None
        )
        existing_items: list[dict[str, Any]] = (
            list(existing_bundle.items) if existing_bundle is not None else []
        )
        prior_pass_sids = list(
            (existing_bundle.metadata or {}).get("pass_session_ids", [])
            if existing_bundle is not None
            else []
        )
        merged_pass_sids: list[str] = []
        for sid in [*prior_pass_sids, *(pass_session_ids or [])]:
            if isinstance(sid, str) and sid and sid not in merged_pass_sids:
                merged_pass_sids.append(sid)

        turn_index = len(existing_items) + 1
        citation_summary = "; ".join(
            f"[{c['source_id']}] {c['title']}: {c['excerpt']}" for c in citations
        )
        item = {
            "id": f"{effective_session}:{dossier.claim_id}:{turn_index}",
            "session_id": effective_session,
            "claim_id": dossier.claim_id,
            "claim": dossier.claim,
            "final_verdict": consensus.final_verdict,
            "agreement_score": consensus.agreement_score,
            "mean_confidence": consensus.mean_confidence,
            "citations": citations,
            "content": (
                f"Claim {dossier.claim_id} ({dossier.claim}) -> {consensus.final_verdict} "
                f"(agreement={consensus.agreement_score:.2f}, "
                f"confidence={consensus.mean_confidence:.2f}). "
                f"Verified citations: {citation_summary or 'none'}."
            ),
            "metadata": {
                "session_id": effective_session,
                "claim_id": dossier.claim_id,
                "final_verdict": consensus.final_verdict,
                "run_id": run_id,
                "turn": turn_index,
            },
        }
        items = [*existing_items, item]
        bundle = export_bundle(
            items,
            metadata={
                "session_id": effective_session,
                "item_count": len(items),
                "claim_ids": [str(entry.get("claim_id", "")) for entry in items],
                "pass_session_ids": merged_pass_sids,
            },
        )
        if session_id is not None:
            bundle_path = self._session_bundle_path(session_id)
            bundle_path.parent.mkdir(parents=True, exist_ok=True)
            save_bundle(bundle, bundle_path)
        if memory_bundle_out is not None:
            out = Path(memory_bundle_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            save_bundle(bundle, out)
        return bundle

    @staticmethod
    def _extract_session_message_snippet(msg: Any) -> str | None:
        """Format an openminion message record or dict into a compact `role: content` snippet."""
        if isinstance(msg, dict):
            role = str(msg.get("role") or "message").strip()
            raw_text = msg.get("content") or msg.get("body")
        else:
            role = str(getattr(msg, "role", None) or "message").strip()
            raw_text = getattr(msg, "content", None) or getattr(msg, "body", None)
        if not raw_text:
            return None
        compact = " ".join(str(raw_text).split())
        if not compact:
            return None
        return f"{role}: {compact[:140]}"

    def _build_session_context_block(self, session_id: str | None) -> str:
        if not session_id:
            return ""
        bundle = self.export_session_memory(session_id)
        runtime = self._ensure_runtime()
        recorded_sids = list(
            dict.fromkeys(
                [
                    session_id,
                    *[
                        str(sid)
                        for sid in (bundle.metadata or {}).get("pass_session_ids", [])
                        if sid
                    ],
                ]
            )
        )
        session_msgs: list[Any] = []
        for sid in recorded_sids:
            session_msgs.extend(runtime.sessions.list_messages(session_id=sid))
        if not bundle.items and not session_msgs:
            return ""

        lines = [f"[SESSION MEMORY & PRIOR VERIFIED CITATIONS | session_id={session_id}]"]
        for item in bundle.items:
            lines.append(f"- {item.get('content', '')}")
        if session_msgs:
            lines.append(f"- Prior openminion session messages recorded: {len(session_msgs)}")
            snippets = [
                snippet
                for msg in session_msgs
                if (snippet := self._extract_session_message_snippet(msg)) is not None
            ]
            for snippet in snippets[-3:]:
                lines.append(f"  - {snippet}")
        return "\n".join(lines) + "\n\n"

    def _build_prompt(
        self,
        dossier: ClaimDossier,
        pass_role: str,
        *,
        session_context: str = "",
    ) -> str:
        serialized = json.dumps(dossier.model_dump(mode="json"), indent=2, sort_keys=True)
        return (
            f"{session_context}"
            f"Audit the following Claim Dossier as the '{pass_role}' verifier pass.\n"
            "Inspect public evidence using the read-only tools (calling at most one tool per step) "
            "before issuing your structured JSON verdict.\n\n"
            f"Claim Dossier:\n{serialized}\n\n"
            "FINAL OUTPUT REQUIREMENT: Reply with ONLY a single raw RFC-8259 JSON object "
            "(double quotes, zero prose prefix, zero markdown code fences) conforming to "
            "VerifierPassResult where verdict is one of SUPPORTED, REFUTED, or INCONCLUSIVE, "
            "confidence is a float between 0.0 and 1.0, citations is a list of EvidenceCitation "
            f'objects (each requiring non-empty source_id, title, and excerpt), and pass_role is "{pass_role}".\n'
            'Example shape: {"verdict": "SUPPORTED", "confidence": 0.9, '
            '"rationale": "concise factual rationale citing retrieved evidence", '
            '"citations": [{"source_id": "src-1", "title": "...", "url": "https://...", '
            '"excerpt": "...", "published_at": "..."}], '
            f'"pass_role": "{pass_role}"}}'
        )

    def _extract_tool_calls(self, result: AgentRunResult[Any]) -> list[str]:
        collected: list[str] = []
        raw_meta = result.raw.get("metadata")
        meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}
        candidates: list[Any] = [
            result.metadata.get("tool_calls_cumulative"),
            result.metadata.get("tool_results"),
            result.metadata.get("tool_calls"),
            result.metadata.get("tools_used"),
            meta.get("tool_calls_cumulative"),
            meta.get("tool_results"),
            meta.get("tool_calls"),
            meta.get("tools_used"),
        ]

        for entry in candidates:
            if isinstance(entry, str) and entry.strip().startswith("["):
                try:
                    entry = json.loads(entry)
                except json.JSONDecodeError:
                    continue
            if not isinstance(entry, list):
                continue
            for item in entry:
                if isinstance(item, str) and item not in collected:
                    collected.append(item)
                elif isinstance(item, dict):
                    name = item.get("tool_name") or item.get("name") or item.get("tool")
                    if isinstance(name, str) and name not in collected:
                        collected.append(name)
        return collected

    def _coerce_pass_result(
        self,
        run_result: AgentRunResult[VerifierPassResult],
        pass_role: str,
    ) -> VerifierPassResult:
        output = run_result.output
        if not isinstance(output, VerifierPassResult):
            output = VerifierPassResult.model_validate(output)
        if pass_role != "primary" and (
            not output.pass_role or output.pass_role == "primary"
        ):
            output = output.model_copy(update={"pass_role": pass_role})
        return output

    def _turn_timeout(self) -> float | None:
        if self.timeout_seconds is None:
            return None
        # Preserve OpenMinion's 90s turn floor for inner retries while extending for slow reasoning LLMs.
        return float(max(90, int(self.timeout_seconds)))

    def _execute_single_pass(
        self,
        dossier: ClaimDossier,
        *,
        pass_role: str = "primary",
        instructions: str | None = None,
        forced_tools: list[str] | None = None,
        session_id: str | None = None,
        session_context: str = "",
        tools: Sequence[Any] | None = None,
    ) -> tuple[VerifierPassResult, AgentRunResult[VerifierPassResult]]:
        active_tools = assert_read_only_tools(self.tools if tools is None else tools)
        allowed_names = {item.tool_decl.name for item in active_tools}
        self._allowed_tool_names = allowed_names
        if forced_tools:
            unknown = [name for name in forced_tools if name not in allowed_names]
            if unknown:
                raise ValueError(
                    f"forced_tools {unknown!r} are not registered READ_ONLY verifier tools."
                )

        runtime = self._ensure_runtime()
        agent = Agent(
            runtime=runtime,
            agent_id=self.agent_id,
            model=self.model,
            instructions=instructions or self._build_instructions(pass_role),
            tools=list(active_tools),
            forced_tools=forced_tools,
            output_type=VerifierPassResult,
        )
        run_session_id = f"{session_id}:{pass_role}:{uuid4().hex[:8]}" if session_id else None
        run_result = agent.run(
            self._build_prompt(dossier, pass_role, session_context=session_context),
            session_id=run_session_id,
            approval_callback=self._read_only_approval_guard,
            timeout_seconds=self._turn_timeout(),
        )
        return self._coerce_pass_result(run_result, pass_role), run_result

    def _execute_dual_passes(
        self,
        dossier: ClaimDossier,
        *,
        session_id: str | None = None,
        session_context: str = "",
        tools: Sequence[Any] | None = None,
    ) -> list[tuple[str, VerifierPassResult, AgentRunResult[VerifierPassResult]]]:
        active_tools = assert_read_only_tools(self.tools if tools is None else tools)
        self._allowed_tool_names = {item.tool_decl.name for item in active_tools}
        runtime = self._ensure_runtime()
        coordinator = Agent(
            name="verifier_coordinator",
            runtime=runtime,
            agent_id=self.agent_id,
            model=self.model,
            instructions=(
                "Coordinate independent corroborator and skeptic verification passes "
                "using READ_ONLY evidence tools."
            ),
            tools=list(active_tools),
        )
        outcomes: list[tuple[str, VerifierPassResult, AgentRunResult[VerifierPassResult]]] = []
        turn_timeout = self._turn_timeout()
        for role in ("corroborator", "skeptic"):
            child = subagent(
                coordinator,
                name=role,
                model=self.model,
                instructions=self._build_instructions(role),
                tools=list(active_tools),
                output_type=VerifierPassResult,
                timeout_seconds=int(turn_timeout) if turn_timeout is not None else None,
            )
            pass_session_id = f"{session_id}:{role}:{uuid4().hex[:8]}" if session_id else None
            run_result = child.run(
                self._build_prompt(dossier, role, session_context=session_context),
                session_id=pass_session_id,
                approval_callback=self._read_only_approval_guard,
                timeout_seconds=turn_timeout,
            )
            outcomes.append((role, self._coerce_pass_result(run_result, role), run_result))
        return outcomes

    @contextmanager
    def _with_publisher_allow_once_grant(
        self,
        *,
        approval_id: str,
        reason: str,
    ) -> Iterator[str]:
        """Issue a scoped single-use PolicyGrantInput on publisher runtime and revoke on exit."""
        pub_rt = self._ensure_publisher_runtime()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        grant_id = pub_rt.action_policy.create_grant(
            PolicyGrantInput(
                effect="allow",
                tool="publish_consensus_verdict",
                method="*",
                duration_type="until",
                expires_at=expires_at,
                max_uses=1,
                approval_id=approval_id,
                reason=reason,
            )
        )
        try:
            yield grant_id
        finally:
            pub_rt.action_policy.revoke_grant(grant_id)

    def _resolve_log_path(self, publication_log_path: str | Path | None) -> Path:
        if publication_log_path is not None:
            return Path(publication_log_path)
        return self._state_root() / "published_verdicts.jsonl"

    @staticmethod
    def _log_line_count(path: Path) -> int:
        if not path.exists():
            return 0
        text = path.read_text(encoding="utf-8")
        return len([ln for ln in text.splitlines() if ln.strip()])

    def _build_handoff_coordinator(
        self,
        *,
        log_path: Path,
    ) -> Agent[Any, Any]:
        coord_rt = self._ensure_runtime()
        pub_rt = self._ensure_publisher_runtime()
        publish_tool = make_publish_consensus_verdict_tool(log_path)
        publisher_agent = Agent(
            name="publisher",
            runtime=pub_rt,
            agent_id=self.agent_id,
            model=self.model,
            instructions=(
                "Execute publish_consensus_verdict once with the provided ConsensusVerdict "
                "fields (do not emit extra task_update fields) and return a concise "
                "confirmation of the written publication receipt."
            ),
            tools=[publish_tool],
        )
        handoff = Handoff(
            target=publisher_agent,
            name="transfer_to_publisher",
            description=(
                "Delegate approved ConsensusVerdict publication to the isolated publisher agent."
            ),
        )
        return Agent(
            name="publication_coordinator",
            runtime=coord_rt,
            agent_id=self.agent_id,
            model=self.model,
            instructions=(
                "Delegate verified ConsensusVerdict publication by calling "
                "transfer_to_publisher exactly once with the verdict payload, then "
                "immediately confirm publication cleanly."
            ),
            tools=[],
            handoffs=[handoff],
        )

    def _save_paused_thread_snapshot(
        self,
        *,
        thread_id: str,
        pub_session_id: str,
        session_id: str | None,
        dossier: ClaimDossier,
        consensus: ConsensusVerdict,
        tool_calls: list[str],
        approval_id: str | None,
        log_path: Path,
        telemetry: TelemetrySummary,
        status: str,
    ) -> None:
        path = self._paused_thread_path(thread_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "thread_id": thread_id,
            "pub_session_id": pub_session_id,
            "session_id": session_id,
            "claim_id": dossier.claim_id,
            "dossier": dossier.model_dump(mode="json"),
            "consensus": consensus.model_dump(mode="json"),
            "tool_calls": tool_calls,
            "approval_id": approval_id,
            "log_path": str(log_path),
            "telemetry": telemetry.model_dump(mode="json"),
            "status": status,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _load_paused_thread_snapshot(self, thread_id: str) -> dict[str, Any] | None:
        path = self._paused_thread_path(thread_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return dict(data) if isinstance(data, dict) else None

    def _execute_handoff_publication(
        self,
        *,
        dossier: ClaimDossier,
        consensus: ConsensusVerdict,
        session_id: str | None,
        approval_mode: ApprovalModeLiteral | None,
        approval_callback: ApprovalCallback | None,
        approval_id: str | None,
        publication_log_path: str | Path | None,
        prior_tool_calls: list[str],
        prior_telemetry: TelemetrySummary,
    ) -> tuple[PublicationResult, AgentRunResult[Any] | None]:
        eff_mode: ApprovalModeLiteral
        if approval_mode is not None:
            eff_mode = approval_mode
        elif approval_callback is not None:
            eff_mode = "allow_once"
        else:
            eff_mode = "pause"

        log_path = self._resolve_log_path(publication_log_path)
        pub_session_id = f"{session_id or 'pub'}:publish:{uuid4().hex[:8]}"
        pub_prompt = (
            "Publish the verified ConsensusVerdict via transfer_to_publisher:\n"
            + json.dumps(
                {
                    "claim_id": dossier.claim_id,
                    "final_verdict": consensus.final_verdict,
                    "agreement_score": consensus.agreement_score,
                    "mean_confidence": consensus.mean_confidence,
                    "requires_human_review": consensus.requires_human_review,
                    "session_id": session_id or "",
                    "summary": consensus.disagreement_summary,
                },
                sort_keys=True,
            )
        )

        if eff_mode == "allow_once":
            eff_approval_id = approval_id or f"appr-{uuid4().hex[:12]}"
            used = self._load_used_approvals()
            if eff_approval_id in used:
                return (
                    PublicationResult(
                        requested=True,
                        published=False,
                        publication_status="denied",
                        claim_id=dossier.claim_id,
                        final_verdict=consensus.final_verdict,
                        approval_mode="allow_once",
                        approval_id=eff_approval_id,
                        denial_reason=(
                            f"Policy denied replay: approval_id '{eff_approval_id}' "
                            "was already used (allow_once cannot be replayed)."
                        ),
                        log_path=str(log_path),
                    ),
                    None,
                )

            self._mark_approval_used(eff_approval_id)
            cb_state = {"calls": 0, "denied": False}

            def _single_use_cb(tool_name: str, args: dict[str, Any], cmd_id: str) -> bool:
                cb_state["calls"] += 1
                if cb_state["calls"] > 1:
                    cb_state["denied"] = True
                    return False
                if approval_callback is not None:
                    ok = bool(approval_callback(tool_name, args, cmd_id))
                    if not ok:
                        cb_state["denied"] = True
                    return ok
                return True

            coord = self._build_handoff_coordinator(log_path=log_path)
            before_lines = self._log_line_count(log_path)
            with self._with_publisher_allow_once_grant(
                approval_id=eff_approval_id,
                reason="allow_once_handoff_publication",
            ):
                coord_res = coord.run(
                    pub_prompt,
                    session_id=pub_session_id,
                    approval_callback=_single_use_cb,
                    timeout_seconds=self._turn_timeout(),
                )

            after_lines = self._log_line_count(log_path)
            wrote_record = after_lines > before_lines and not cb_state["denied"]
            return (
                PublicationResult(
                    requested=True,
                    published=wrote_record,
                    publication_status="published" if wrote_record else "denied",
                    claim_id=dossier.claim_id,
                    final_verdict=consensus.final_verdict,
                    approval_mode="allow_once",
                    thread_id=coord_res.thread_id,
                    approval_id=eff_approval_id,
                    denial_reason=(
                        ""
                        if wrote_record
                        else "Publication denied or did not commit under allow_once policy."
                    ),
                    log_path=str(log_path),
                    run_id=coord_res.run_id,
                ),
                coord_res,
            )

        if eff_mode == "deny":
            coord = self._build_handoff_coordinator(log_path=log_path)

            def _deny_cb(tool_name: str, args: dict[str, Any], cmd_id: str) -> bool:
                if approval_callback is not None:
                    approval_callback(tool_name, args, cmd_id)
                return False

            coord_res = coord.run(
                pub_prompt,
                session_id=pub_session_id,
                approval_callback=_deny_cb,
                timeout_seconds=self._turn_timeout(),
            )
            return (
                PublicationResult(
                    requested=True,
                    published=False,
                    publication_status="denied",
                    claim_id=dossier.claim_id,
                    final_verdict=consensus.final_verdict,
                    approval_mode="deny",
                    thread_id=coord_res.thread_id,
                    approval_id=coord_res.metadata.get("pending_confirmation_command_id"),
                    denial_reason="Publication blocked by operator policy confirmation (deny).",
                    log_path=str(log_path),
                    run_id=coord_res.run_id,
                ),
                coord_res,
            )

        # Fail-closed pause mode (approval_callback=None pauses before Handoff execution).
        coord = self._build_handoff_coordinator(log_path=log_path)
        coord_res = coord.run(
            pub_prompt,
            session_id=pub_session_id,
            approval_callback=None,
            timeout_seconds=self._turn_timeout(),
        )
        paused_tid = coord_res.thread_id or f"{pub_session_id}:paused"
        pending_id = coord_res.metadata.get("pending_confirmation_command_id")
        self._save_paused_thread_snapshot(
            thread_id=paused_tid,
            pub_session_id=pub_session_id,
            session_id=session_id,
            dossier=dossier,
            consensus=consensus,
            tool_calls=prior_tool_calls,
            approval_id=pending_id,
            log_path=log_path,
            telemetry=prior_telemetry,
            status="paused",
        )
        return (
            PublicationResult(
                requested=True,
                published=False,
                publication_status="paused",
                claim_id=dossier.claim_id,
                final_verdict=consensus.final_verdict,
                approval_mode="pause",
                thread_id=paused_tid,
                approval_id=pending_id,
                confirmation_prompt=coord_res.text,
                log_path=str(log_path),
                run_id=coord_res.run_id,
            ),
            coord_res,
        )

    def _build_audit_bundle(
        self,
        *,
        dossier: ClaimDossier,
        consensus: ConsensusVerdict,
        tool_calls: list[str],
        telemetry: TelemetrySummary,
        session_id: str | None,
        run_id: str | None = None,
        publication: PublicationResult | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> AuditRunBundle:
        metadata: dict[str, Any] = dict(extra_metadata or {})
        metadata["telemetry"] = telemetry.model_dump(mode="json")
        metadata.update(self._calibration_metadata())
        if publication is not None:
            metadata["publication"] = publication.model_dump(mode="json")
        return AuditRunBundle(
            claim_id=dossier.claim_id,
            preset=self.preset,
            dossier=dossier,
            consensus=consensus,
            tool_calls=tool_calls,
            run_id=run_id,
            session_id=session_id,
            publication=publication,
            metadata=metadata,
        )

    def resume_publication(
        self,
        *,
        thread_id: str,
        approval_mode: ApprovalModeLiteral = "allow_once",
        approval_id: str | None = None,
        publication_log_path: str | Path | None = None,
        memory_bundle_out: str | Path | None = None,
    ) -> AuditRunBundle:
        """Resume a paused Handoff publication thread via thread_id."""
        snapshot = self._load_paused_thread_snapshot(thread_id)
        if snapshot is None:
            raise ValueError(f"No paused publication snapshot found for thread_id={thread_id!r}.")

        dossier = ClaimDossier.model_validate(snapshot["dossier"])
        consensus = ConsensusVerdict.model_validate(snapshot["consensus"])
        prior_tool_calls = list(snapshot.get("tool_calls") or [])
        prior_telemetry = TelemetrySummary.model_validate(snapshot.get("telemetry") or {})
        log_path = (
            Path(publication_log_path)
            if publication_log_path is not None
            else Path(snapshot["log_path"])
        )
        pub_session_id = str(snapshot["pub_session_id"])
        session_id = snapshot.get("session_id")
        snap_status = str(snapshot.get("status", ""))
        snap_approval_id = approval_id or snapshot.get("approval_id") or f"thread:{thread_id}"

        if snap_status != "paused":
            pub_res = PublicationResult(
                requested=True,
                published=False,
                publication_status="denied",
                claim_id=dossier.claim_id,
                final_verdict=consensus.final_verdict,
                approval_mode=approval_mode,
                thread_id=thread_id,
                approval_id=snap_approval_id,
                denial_reason=(
                    f"Policy denied replay: paused thread '{thread_id}' already "
                    f"terminated with status '{snap_status}'."
                ),
                log_path=str(log_path),
            )
            return self._build_audit_bundle(
                dossier=dossier,
                consensus=consensus,
                tool_calls=prior_tool_calls,
                telemetry=prior_telemetry,
                session_id=session_id,
                publication=pub_res,
            )

        if approval_mode == "pause":
            pub_res = PublicationResult(
                requested=True,
                published=False,
                publication_status="paused",
                claim_id=dossier.claim_id,
                final_verdict=consensus.final_verdict,
                approval_mode="pause",
                thread_id=thread_id,
                approval_id=snap_approval_id,
                log_path=str(log_path),
            )
            return self._build_audit_bundle(
                dossier=dossier,
                consensus=consensus,
                tool_calls=prior_tool_calls,
                telemetry=prior_telemetry,
                session_id=session_id,
                publication=pub_res,
            )

        coord = self._build_handoff_coordinator(log_path=log_path)
        if approval_mode == "deny":
            res_run = coord.run(
                "deny",
                session_id=pub_session_id,
                thread_id=thread_id,
                timeout_seconds=self._turn_timeout(),
            )
            self._save_paused_thread_snapshot(
                thread_id=thread_id,
                pub_session_id=pub_session_id,
                session_id=session_id,
                dossier=dossier,
                consensus=consensus,
                tool_calls=prior_tool_calls,
                approval_id=snap_approval_id,
                log_path=log_path,
                telemetry=prior_telemetry,
                status="denied",
            )
            pub_res = PublicationResult(
                requested=True,
                published=False,
                publication_status="denied",
                claim_id=dossier.claim_id,
                final_verdict=consensus.final_verdict,
                approval_mode="deny",
                thread_id=thread_id,
                approval_id=snap_approval_id,
                denial_reason="Paused publication denied on resume.",
                log_path=str(log_path),
                run_id=res_run.run_id,
            )
            agg_tel = _aggregate_telemetry(
                [("publication", res_run)],
                base_summary=prior_telemetry,
            )
            return self._build_audit_bundle(
                dossier=dossier,
                consensus=consensus,
                tool_calls=prior_tool_calls,
                telemetry=agg_tel,
                session_id=session_id,
                run_id=res_run.run_id,
                publication=pub_res,
                extra_metadata={
                    "run_state": res_run.run_state,
                    "stats": res_run.stats,
                },
            )

        # approval_mode == "allow_once"
        used = self._load_used_approvals()
        replay_key = approval_id or f"thread:{thread_id}"
        if replay_key in used:
            pub_res = PublicationResult(
                requested=True,
                published=False,
                publication_status="denied",
                claim_id=dossier.claim_id,
                final_verdict=consensus.final_verdict,
                approval_mode="allow_once",
                thread_id=thread_id,
                approval_id=snap_approval_id,
                denial_reason=f"Policy denied replay: authorization '{replay_key}' already consumed.",
                log_path=str(log_path),
            )
            return self._build_audit_bundle(
                dossier=dossier,
                consensus=consensus,
                tool_calls=prior_tool_calls,
                telemetry=prior_telemetry,
                session_id=session_id,
                publication=pub_res,
            )

        self._mark_approval_used(replay_key)
        before_lines = self._log_line_count(log_path)
        with self._with_publisher_allow_once_grant(
            approval_id=str(snap_approval_id),
            reason="resume_allow_once_handoff",
        ):
            res_run = coord.run(
                "allow_once",
                session_id=pub_session_id,
                thread_id=thread_id,
                timeout_seconds=self._turn_timeout(),
            )

        after_lines = self._log_line_count(log_path)
        wrote_record = after_lines > before_lines
        new_status = "published" if wrote_record else "denied"
        self._save_paused_thread_snapshot(
            thread_id=thread_id,
            pub_session_id=pub_session_id,
            session_id=session_id,
            dossier=dossier,
            consensus=consensus,
            tool_calls=prior_tool_calls,
            approval_id=snap_approval_id,
            log_path=log_path,
            telemetry=prior_telemetry,
            status=new_status,
        )
        if memory_bundle_out is not None:
            self.export_session_memory(session_id or "ephemeral", output_path=memory_bundle_out)
        pub_res = PublicationResult(
            requested=True,
            published=wrote_record,
            publication_status="published" if wrote_record else "denied",
            claim_id=dossier.claim_id,
            final_verdict=consensus.final_verdict,
            approval_mode="allow_once",
            thread_id=thread_id,
            approval_id=snap_approval_id,
            denial_reason="" if wrote_record else "Resumed Handoff publication did not commit.",
            log_path=str(log_path),
            run_id=res_run.run_id,
        )
        agg_tel = _aggregate_telemetry(
            [("publication", res_run)],
            base_summary=prior_telemetry,
        )
        return self._build_audit_bundle(
            dossier=dossier,
            consensus=consensus,
            tool_calls=prior_tool_calls,
            telemetry=agg_tel,
            session_id=session_id,
            run_id=res_run.run_id,
            publication=pub_res,
            extra_metadata={
                "run_state": res_run.run_state,
                "stats": res_run.stats,
            },
        )

    def audit_claim(
        self,
        dossier: ClaimDossier,
        *,
        single_pass: bool = False,
        session_id: str | None = None,
        thread_id: str | None = None,
        publish: bool = False,
        approval_callback: ApprovalCallback | None = None,
        approval_mode: ApprovalModeLiteral | None = None,
        approval_id: str | None = None,
        publication_log_path: str | Path | None = None,
        memory_bundle_out: str | Path | None = None,
        fixture_path: str | Path | None = None,
    ) -> AuditRunBundle:
        """Run dual-pass (or single-pass) consensus verification with optional Handoff publication."""
        if thread_id is not None:
            if approval_mode is not None:
                resolved_mode: ApprovalModeLiteral = approval_mode
            elif approval_callback is not None:
                approved = bool(
                    approval_callback(
                        "transfer_to_publisher",
                        {"thread_id": thread_id, "claim_id": dossier.claim_id},
                        approval_id or thread_id,
                    )
                )
                resolved_mode = "allow_once" if approved else "deny"
            else:
                resolved_mode = "pause"
            return self.resume_publication(
                thread_id=thread_id,
                approval_mode=resolved_mode,
                approval_id=approval_id,
                publication_log_path=publication_log_path,
                memory_bundle_out=memory_bundle_out,
            )

        effective_fixture_path = fixture_path if fixture_path is not None else self.fixture_path
        active_tools = (
            list(self.tools)
            if self._explicit_tools
            else assert_read_only_tools(
                build_scoped_verifier_tools(
                    fixture_path=effective_fixture_path,
                    dossier=dossier,
                    allow_private_network=self.allow_private_network,
                )
            )
        )
        self._allowed_tool_names = {item.tool_decl.name for item in active_tools}

        session_context = self._build_session_context_block(session_id)
        telemetry_runs: list[tuple[str, AgentRunResult[Any]]] = []
        tool_calls: list[str] = []

        if single_pass:
            pass_result, run_result = self._execute_single_pass(
                dossier,
                pass_role="primary",
                session_id=session_id,
                session_context=session_context,
                tools=active_tools,
            )
            tool_calls = self._extract_tool_calls(run_result)
            consensus = synthesize_consensus(dossier.claim_id, [pass_result])
            telemetry_runs.append(("primary", run_result))
            primary_run = run_result
        else:
            pass_outcomes = self._execute_dual_passes(
                dossier,
                session_id=session_id,
                session_context=session_context,
                tools=active_tools,
            )
            passes: list[VerifierPassResult] = []
            for role, pass_out, run_res in pass_outcomes:
                passes.append(pass_out)
                telemetry_runs.append((role, run_res))
                for tool_name in self._extract_tool_calls(run_res):
                    if tool_name not in tool_calls:
                        tool_calls.append(tool_name)
            consensus = synthesize_consensus(dossier.claim_id, passes)
            primary_run = pass_outcomes[-1][2]

        telemetry = _aggregate_telemetry(telemetry_runs)
        pass_session_ids = [run.session_id for _, run in telemetry_runs if run.session_id]
        saved_bundle = self._persist_session_memory(
            session_id=session_id,
            dossier=dossier,
            consensus=consensus,
            run_id=primary_run.run_id,
            pass_session_ids=pass_session_ids,
            memory_bundle_out=memory_bundle_out,
        )

        publication: PublicationResult | None = None
        if publish:
            publication, pub_run = self._execute_handoff_publication(
                dossier=dossier,
                consensus=consensus,
                session_id=session_id,
                approval_mode=approval_mode,
                approval_callback=approval_callback,
                approval_id=approval_id,
                publication_log_path=publication_log_path,
                prior_tool_calls=tool_calls,
                prior_telemetry=telemetry,
            )
            if pub_run is not None:
                telemetry_runs.append(("publication", pub_run))
                telemetry = _aggregate_telemetry(telemetry_runs)

        extra_metadata: dict[str, Any] = {
            "run_state": primary_run.run_state,
            "stats": primary_run.stats,
            "per_pass_stats": {
                role: dict(res.stats or {}) for role, res in telemetry_runs
            },
        }
        if saved_bundle is not None:
            extra_metadata["session_memory"] = {
                "session_id": session_id,
                "item_count": len(saved_bundle.items),
            }

        return self._build_audit_bundle(
            dossier=dossier,
            consensus=consensus,
            tool_calls=tool_calls,
            telemetry=telemetry,
            session_id=session_id if session_id is not None else primary_run.session_id,
            run_id=primary_run.run_id,
            publication=publication,
            extra_metadata=extra_metadata,
        )
