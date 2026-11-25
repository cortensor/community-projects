"""Custom OpenMinion 0.1.24 @tool implementations for Cortensor Router auditing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import time
from typing import Any

import httpx
from openminion import tool

from cortensor_router_doctor.models import (
    PoIDriftAnalysis,
    ProbeResult,
    ProbeRoundSample,
    QuarantineAction,
    RecommendedAction,
    SLAGrade,
    SLAPolicyEvaluation,
    SeverityLevel,
)

_TOKEN_RE = re.compile(r"[a-z0-9_:=.-]+", re.IGNORECASE)


@dataclass
class ToolEvidenceLedger:
    """In-process deterministic audit trail of real OpenMinion @tool executions."""

    probes: list[ProbeResult] = field(default_factory=list)
    evaluations: list[SLAPolicyEvaluation] = field(default_factory=list)
    quarantines: list[QuarantineAction] = field(default_factory=list)
    tool_trace: list[str] = field(default_factory=list)


_LEDGER_LOCK = threading.Lock()
_ACTIVE_LEDGER: ToolEvidenceLedger | None = None


def start_evidence_ledger() -> ToolEvidenceLedger:
    """Begin capturing deterministic @tool execution artifacts for an audit run."""
    global _ACTIVE_LEDGER
    ledger = ToolEvidenceLedger()
    with _LEDGER_LOCK:
        _ACTIVE_LEDGER = ledger
    return ledger


def stop_evidence_ledger() -> ToolEvidenceLedger | None:
    """Stop capturing and return the completed ledger."""
    global _ACTIVE_LEDGER
    with _LEDGER_LOCK:
        ledger = _ACTIVE_LEDGER
        _ACTIVE_LEDGER = None
    return ledger


def _record_probe(result: ProbeResult) -> None:
    with _LEDGER_LOCK:
        if _ACTIVE_LEDGER is not None:
            _ACTIVE_LEDGER.probes.append(result)
            _ACTIVE_LEDGER.tool_trace.append(f"probe_cortensor_router({result.endpoint_url})")


def _record_evaluation(evaluation: SLAPolicyEvaluation) -> None:
    with _LEDGER_LOCK:
        if _ACTIVE_LEDGER is not None:
            _ACTIVE_LEDGER.evaluations.append(evaluation)
            _ACTIVE_LEDGER.tool_trace.append(f"evaluate_sla_policy({evaluation.grade})")


def _record_quarantine(action: QuarantineAction) -> None:
    with _LEDGER_LOCK:
        if _ACTIVE_LEDGER is not None:
            _ACTIVE_LEDGER.quarantines.append(action)
            _ACTIVE_LEDGER.tool_trace.append(f"apply_router_quarantine({action.severity})")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _jaccard_similarity(left: str, right: str) -> float:
    tokens_left = _tokenize(left)
    tokens_right = _tokenize(right)
    if not tokens_left and not tokens_right:
        return 1.0
    union = tokens_left | tokens_right
    if not union:
        return 1.0
    return len(tokens_left & tokens_right) / len(union)


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return float(sorted_values[lower])
    weight = rank - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def _extract_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        first = choices[0]
        message = first.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"].strip()
        if isinstance(first.get("text"), str):
            return first["text"].strip()
    for key in ("text", "output_text", "response"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _compute_poi_analysis(
    rounds_requested: int,
    successful_texts: list[str],
) -> PoIDriftAnalysis:
    succeeded = len(successful_texts)
    if succeeded == 0:
        return PoIDriftAnalysis(
            rounds_requested=rounds_requested,
            rounds_succeeded=0,
            exact_match_ratio=0.0,
            mean_jaccard_agreement=0.0,
            poi_agreement_score=0.0,
            unique_responses=0,
            drift_detected=True,
        )
    if succeeded == 1:
        return PoIDriftAnalysis(
            rounds_requested=rounds_requested,
            rounds_succeeded=1,
            exact_match_ratio=1.0,
            mean_jaccard_agreement=1.0,
            poi_agreement_score=1.0,
            unique_responses=1,
            drift_detected=False,
        )

    pair_count = 0
    exact_pairs = 0
    jaccard_sum = 0.0
    for idx in range(succeeded):
        for jdx in range(idx + 1, succeeded):
            pair_count += 1
            a = successful_texts[idx].strip()
            b = successful_texts[jdx].strip()
            if a == b:
                exact_pairs += 1
            jaccard_sum += _jaccard_similarity(a, b)

    exact_ratio = exact_pairs / pair_count if pair_count else 1.0
    mean_jaccard = jaccard_sum / pair_count if pair_count else 1.0
    # Weighted PoI agreement balances semantic token overlap (70%) and strict determinism (30%).
    poi_score = round(0.7 * mean_jaccard + 0.3 * exact_ratio, 4)
    unique_count = len({t.strip() for t in successful_texts})
    return PoIDriftAnalysis(
        rounds_requested=rounds_requested,
        rounds_succeeded=succeeded,
        exact_match_ratio=round(exact_ratio, 4),
        mean_jaccard_agreement=round(mean_jaccard, 4),
        poi_agreement_score=poi_score,
        unique_responses=unique_count,
        drift_detected=poi_score < 0.85,
    )


@tool(min_scope="READ_ONLY", idempotent=True)
def probe_cortensor_router(
    endpoint_url: str,
    prompt: str,
    rounds: int = 3,
    session_id: int = 1,
    timeout_seconds: float = 10.0,
) -> str:
    """Probe a Cortensor Router or OpenAI-compatible inference endpoint across redundant rounds.

    Fires `rounds` requests to `endpoint_url`, measures p50/p95 latency and HTTP success rate,
    and computes a Proof-of-Inference (PoI) cross-round consensus agreement score (0.0-1.0).
    Returns JSON matching `ProbeResult`.
    """
    effective_rounds = max(1, min(int(rounds), 20))
    effective_timeout = max(0.5, float(timeout_seconds))
    is_chat_endpoint = "/chat/completions" in endpoint_url

    samples: list[ProbeRoundSample] = []
    latencies: list[float] = []
    successful_texts: list[str] = []

    with httpx.Client(timeout=effective_timeout) as client:
        for round_index in range(1, effective_rounds + 1):
            body: dict[str, Any]
            if is_chat_endpoint:
                body = {
                    "model": "gpt-oss-20b",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 128,
                }
            else:
                body = {
                    "session_id": int(session_id),
                    "prompt": prompt,
                    "temperature": 0.0,
                    "max_tokens": 128,
                    "stream": False,
                }

            started = time.perf_counter()
            try:
                resp = client.post(
                    endpoint_url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
                latencies.append(elapsed_ms)
                if 200 <= resp.status_code < 300:
                    data = resp.json()
                    text = (
                        _extract_completion_text(data)
                        if isinstance(data, dict)
                        else ""
                    )
                    if text:
                        successful_texts.append(text)
                        samples.append(
                            ProbeRoundSample(
                                round_index=round_index,
                                status_code=resp.status_code,
                                latency_ms=elapsed_ms,
                                ok=True,
                                response_text=text,
                            )
                        )
                    else:
                        samples.append(
                            ProbeRoundSample(
                                round_index=round_index,
                                status_code=resp.status_code,
                                latency_ms=elapsed_ms,
                                ok=False,
                                error="Empty completion text in HTTP 200 response",
                            )
                        )
                else:
                    samples.append(
                        ProbeRoundSample(
                            round_index=round_index,
                            status_code=resp.status_code,
                            latency_ms=elapsed_ms,
                            ok=False,
                            error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
                latencies.append(elapsed_ms)
                samples.append(
                    ProbeRoundSample(
                        round_index=round_index,
                        status_code=0,
                        latency_ms=elapsed_ms,
                        ok=False,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

    sorted_lat = sorted(latencies)
    success_rate = round(len(successful_texts) / effective_rounds, 4)
    p50_ms = round(_percentile(sorted_lat, 50.0), 2)
    p95_ms = round(_percentile(sorted_lat, 95.0), 2)
    mean_ms = round(sum(sorted_lat) / len(sorted_lat), 2) if sorted_lat else 0.0
    poi = _compute_poi_analysis(effective_rounds, successful_texts)

    result = ProbeResult(
        endpoint_url=endpoint_url,
        prompt=prompt,
        session_id=int(session_id),
        rounds=effective_rounds,
        success_rate=success_rate,
        p50_latency_ms=p50_ms,
        p95_latency_ms=p95_ms,
        mean_latency_ms=mean_ms,
        poi_analysis=poi,
        samples=samples,
    )
    _record_probe(result)
    return result.model_dump_json()


@tool(min_scope="READ_ONLY", idempotent=True)
def evaluate_sla_policy(
    probe_json: str,
    max_p95_ms: float = 500.0,
    min_poi_agreement: float = 0.85,
    min_success_rate: float = 0.95,
) -> str:
    """Deterministically grade a `ProbeResult` JSON payload against Cortensor SLA thresholds.

    Returns JSON matching `SLAPolicyEvaluation` with grade (`HEALTHY`, `DEGRADED`, or
    `CRITICAL_DRIFT`) and recommended action (`NONE`, `MONITOR`, or `QUARANTINE`).
    """
    probe = ProbeResult.model_validate_json(probe_json)
    violations: list[str] = []

    if probe.poi_analysis.rounds_succeeded == 0:
        violations.append("zero_successful_inference_rounds")
    if probe.poi_analysis.poi_agreement_score < min_poi_agreement:
        violations.append(
            f"poi_agreement_below_threshold: {probe.poi_analysis.poi_agreement_score:.4f} < {min_poi_agreement:.4f}"
        )
    if probe.success_rate < min_success_rate:
        violations.append(
            f"success_rate_below_threshold: {probe.success_rate:.4f} < {min_success_rate:.4f}"
        )
    if probe.p95_latency_ms > max_p95_ms:
        violations.append(
            f"p95_latency_above_threshold: {probe.p95_latency_ms:.2f}ms > {max_p95_ms:.2f}ms"
        )

    grade: SLAGrade
    recommended_action: RecommendedAction

    if (
        probe.poi_analysis.rounds_succeeded == 0
        or probe.poi_analysis.poi_agreement_score < min_poi_agreement
    ):
        grade = "CRITICAL_DRIFT"
        recommended_action = "QUARANTINE"
    elif probe.success_rate < min_success_rate or probe.p95_latency_ms > max_p95_ms:
        grade = "DEGRADED"
        recommended_action = (
            "QUARANTINE"
            if (
                probe.success_rate < min_success_rate
                or probe.p95_latency_ms > max_p95_ms * 2.0
            )
            else "MONITOR"
        )
    else:
        grade = "HEALTHY"
        recommended_action = "NONE"

    evaluation = SLAPolicyEvaluation(
        endpoint_url=probe.endpoint_url,
        grade=grade,
        recommended_action=recommended_action,
        violations=violations,
        thresholds={
            "max_p95_ms": float(max_p95_ms),
            "min_poi_agreement": float(min_poi_agreement),
            "min_success_rate": float(min_success_rate),
        },
        measured={
            "p50_latency_ms": probe.p50_latency_ms,
            "p95_latency_ms": probe.p95_latency_ms,
            "success_rate": probe.success_rate,
            "poi_agreement_score": probe.poi_analysis.poi_agreement_score,
            "exact_match_ratio": probe.poi_analysis.exact_match_ratio,
        },
    )
    _record_evaluation(evaluation)
    return evaluation.model_dump_json()


@tool(min_scope="WRITE_SAFE", dangerous=True, idempotent=False)
def apply_router_quarantine(
    reason: str,
    quarantine_file: str,
    endpoint_url: str = "",
    severity: str = "HIGH",
) -> str:
    """Write a signed JSON quarantine directive for an unhealthy Cortensor Router endpoint.

    Marked `dangerous=True` and `idempotent=False` so OpenMinion's ActionPolicy requires
    explicit operator approval via `approval_callback` or `RuntimeTurnHandle.resolve_approval`.
    """
    resolved_endpoint = str(endpoint_url or "").strip()
    if not resolved_endpoint:
        with _LEDGER_LOCK:
            if _ACTIVE_LEDGER is not None and _ACTIVE_LEDGER.probes:
                resolved_endpoint = _ACTIVE_LEDGER.probes[-1].endpoint_url
    if not resolved_endpoint:
        resolved_endpoint = "unknown-router-endpoint"
    endpoint_url = resolved_endpoint
    normalized_severity = str(severity or "HIGH").strip().upper()
    if normalized_severity not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        normalized_severity = "HIGH"
    typed_severity: SeverityLevel = normalized_severity  # type: ignore[assignment]

    timestamp_utc = datetime.now(timezone.utc).isoformat()
    target_path = Path(quarantine_file).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    unsigned_payload = {
        "schema_version": "cortensor.quarantine.v1",
        "endpoint_url": endpoint_url,
        "reason": reason,
        "severity": typed_severity,
        "timestamp_utc": timestamp_utc,
        "status": "QUARANTINED",
    }
    canonical = json.dumps(unsigned_payload, sort_keys=True, ensure_ascii=True).encode(
        "utf-8"
    )
    signature = hashlib.sha256(canonical).hexdigest()

    signed_directive = {
        **unsigned_payload,
        "signature_sha256": signature,
    }
    target_path.write_text(
        json.dumps(signed_directive, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    action = QuarantineAction(
        endpoint_url=endpoint_url,
        reason=reason,
        severity=typed_severity,
        quarantine_file=str(target_path),
        applied=True,
        signature_sha256=signature,
        timestamp_utc=timestamp_utc,
    )
    _record_quarantine(action)
    return action.model_dump_json()
