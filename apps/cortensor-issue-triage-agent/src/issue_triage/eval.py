"""Quantitative evaluation: model predictions vs maintainer ground truth.

Takes N real issues from a public repo that already carry maintainer
labels, runs the classifier (one model call per issue, paced), and reports
per-class precision / recall / F1 plus a confidence-calibration summary.
No draft call is made during eval (that would double the cost for no
classification signal).

Two modes (see ``run_eval`` ``blind``):

- **label-blind (default, honest):** the issue's existing maintainer
  labels are hidden from the classifier prompt — they are the ground
  truth being scored, so showing them measures label-copying, not
  classification. The repo label list stays (closed vocabulary).
- **label-aware (``--label-aware``):** the original mode, kept only as a
  baseline. The 2026-11-16 run (accuracy 0.9, 9/10) was label-aware.

Ground-truth mapping is deliberately conservative: only issues whose
maintainer labels map to exactly one type count.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

from .github_client import label_names
from .models import EvalRecord
from .triage import TriageEngine

LABEL_TO_TYPE: dict[str, str] = {
    "bug": "bug",
    "enhancement": "feature",
    "feature": "feature",
    "feature-request": "feature",
    "question": "question",
    "documentation": "docs",
    "docs": "docs",
}


def ground_truth_type(labels: list[str]) -> str | None:
    """Map maintainer labels to one issue type, or None if ambiguous."""
    found = {LABEL_TO_TYPE[label.lower()] for label in labels if label.lower() in LABEL_TO_TYPE}
    if len(found) == 1:
        return next(iter(found))
    return None


def compute_metrics(records: list[EvalRecord]) -> dict:
    classes = ["bug", "feature", "question", "docs", "chore", "duplicate"]
    per_class: dict[str, dict] = {}
    for cls in classes:
        tp = sum(1 for r in records if r.ground_truth == cls and r.predicted == cls)
        fp = sum(1 for r in records if r.ground_truth != cls and r.predicted == cls)
        fn = sum(1 for r in records if r.ground_truth == cls and r.predicted != cls)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        support = sum(1 for r in records if r.ground_truth == cls)
        per_class[cls] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    accuracy = sum(1 for r in records if r.correct) / len(records) if records else 0.0

    # confidence calibration: mean confidence on correct vs wrong, and
    # accuracy inside confidence buckets
    correct_conf = [r.confidence for r in records if r.correct]
    wrong_conf = [r.confidence for r in records if not r.correct]
    buckets: dict[str, dict] = {}
    for name, low, high in ((">=0.8", 0.8, 1.01), ("0.5-0.8", 0.5, 0.8), ("<0.5", 0.0, 0.5)):
        bucket = [r for r in records if low <= r.confidence < high]
        buckets[name] = {
            "n": len(bucket),
            "accuracy": round(
                sum(1 for r in bucket if r.correct) / len(bucket), 3
            )
            if bucket
            else None,
        }
    return {
        "n": len(records),
        "accuracy": round(accuracy, 3),
        "per_class": per_class,
        "calibration": {
            "mean_confidence_correct": round(sum(correct_conf) / len(correct_conf), 3)
            if correct_conf
            else None,
            "mean_confidence_wrong": round(sum(wrong_conf) / len(wrong_conf), 3)
            if wrong_conf
            else None,
            "buckets": buckets,
        },
    }


def run_eval(
    engine: TriageEngine,
    repo: str,
    limit: int,
    issues: list[dict] | None = None,
    blind: bool = True,
) -> dict:
    """Run eval. ``issues`` overrides the GitHub fetch (tests / offline).
    ``blind`` (default True) hides each issue's existing maintainer labels
    from the classifier prompt — they are the ground truth, so showing
    them would score label-copying instead of classification. Linked PR
    bodies are not fetched in eval: the prompt must match the baseline
    run except for the hidden labels, and a 10-issue eval already uses
    ~60 unauthenticated GitHub requests."""
    if issues is None:
        raw = engine.github.list_issues(repo, state="all", per_page=max(limit * 3, 30))
        issues = [i for i in raw if "pull_request" not in i]
    repo_cache = engine.fetch_repo_cache(repo)
    records: list[EvalRecord] = []
    errors: list[dict] = []
    skipped = 0
    for issue in issues:
        if len(records) >= limit:
            break
        labels = label_names(issue)
        truth = ground_truth_type(labels)
        if truth is None:
            skipped += 1
            continue
        try:
            ctx = engine.fetch_context(
                repo, issue["number"], repo_cache=repo_cache, fetch_linked_prs=False
            )
            started = time.monotonic()
            verdict, meta = engine.classify(ctx, hide_existing_labels=blind)
            latency_ms = int((time.monotonic() - started) * 1000)
        except Exception as exc:  # noqa: BLE001 - per-issue resilience
            errors.append(
                {
                    "issue_number": issue["number"],
                    "title": issue.get("title") or "",
                    "ground_truth": truth,
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                }
            )
            continue
        records.append(
            EvalRecord(
                repo=repo,
                issue_number=issue["number"],
                title=issue.get("title") or "",
                ground_truth=truth,  # type: ignore[arg-type]
                predicted=verdict.issue_type,
                severity=verdict.severity,
                confidence=verdict.confidence,
                correct=verdict.issue_type == truth,
                maintainer_labels=labels,
                latency_ms=latency_ms,
            )
        )
    summary = compute_metrics(records)
    return {
        "repo": repo,
        "limit": limit,
        "mode": "label-blind" if blind else "label-aware",
        "skipped_unlabelled_or_ambiguous": skipped,
        "records": [r.model_dump() for r in records],
        "errors": errors,
        "metrics": summary,
        "llm_calls": engine.llm.calls_made,
    }


def save_eval_result(result: dict, out_dir: str | Path = "eval") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M")
    path = out_dir / f"results-{stamp}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
