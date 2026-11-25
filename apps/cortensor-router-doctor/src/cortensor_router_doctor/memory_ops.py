"""Durable OpenMinion memory operations with atomic/namespace-guarded bundle portability."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from openminion.modules.memory.models import MemoryNamespace, MemoryRecord
from openminion.modules.memory.portability.codec import (
    read_bundle_snapshot,
    write_bundle_snapshot,
)
from openminion.modules.memory.portability.models import (
    MemoryBundleExportOptions,
    MemoryBundleImportOptions,
    MemoryBundleImportResult,
    MemoryBundleSnapshot,
)
from openminion.modules.memory.storage.base import ListQueryOptions

from cortensor_router_doctor.models import RouterAuditReport

DEFAULT_AUDIT_SCOPE = "agent:router-doctor"


def _resolve_memory_service(runtime_or_service: Any) -> Any:
    """Return the underlying `MemoryService` from an `APIRuntime` or direct service."""
    assembly = getattr(runtime_or_service, "runtime_memory_assembly", None)
    if assembly is not None and getattr(assembly, "service", None) is not None:
        return assembly.service
    if hasattr(runtime_or_service, "write_record") and hasattr(
        runtime_or_service, "export_bundle_snapshot"
    ):
        return runtime_or_service
    raise TypeError(
        "Expected an APIRuntime with runtime_memory_assembly.service or a MemoryService instance"
    )


def _records_equivalent(left: MemoryRecord, right: MemoryRecord, *, ignore_id: bool) -> bool:
    left_dict = asdict(left)
    right_dict = asdict(right)
    if ignore_id:
        left_dict.pop("id", None)
        right_dict.pop("id", None)
    for transient in (
        "created_at",
        "updated_at",
        "supersedes_id",
        "superseded_by_id",
        "supersession_reason",
        "last_hit_at",
    ):
        left_dict.pop(transient, None)
        right_dict.pop(transient, None)
    return left_dict == right_dict


def _effective_namespace(
    record: MemoryRecord,
    scope_rewrites: dict[str, str],
) -> MemoryNamespace:
    rewritten_scope = str(scope_rewrites.get(record.scope, record.scope) or "").strip()
    if record.namespace is not None:
        if record.namespace == MemoryNamespace.from_scope(record.scope):
            return MemoryNamespace.from_scope(rewritten_scope)  # type: ignore[arg-type]
        return record.namespace
    return MemoryNamespace.from_scope(rewritten_scope)  # type: ignore[arg-type]


def record_audit_incident(
    runtime_or_service: Any,
    *,
    report: RouterAuditReport,
    scope: str = DEFAULT_AUDIT_SCOPE,
    incident_key: str | None = None,
    tags: list[str] | None = None,
    confidence: float = 0.95,
) -> str:
    """Persist a router audit finding into OpenMinion's durable memory store."""
    service = _resolve_memory_service(runtime_or_service)
    resolved_tags = list(
        dict.fromkeys(
            [
                "cortensor",
                "router-audit",
                report.verdict.lower(),
                *(tags or []),
            ]
        )
    )
    return str(
        service.write_record(
            scope=scope,
            record_type="fact",
            key=incident_key,
            title=f"Cortensor Router Audit [{report.verdict}]: {report.endpoint_url}",
            content=report.model_dump(mode="json"),
            tags=resolved_tags,
            confidence=confidence,
            agent_id="router-doctor",
        )
    )


def list_audit_incidents(
    runtime_or_service: Any,
    *,
    scope: str = DEFAULT_AUDIT_SCOPE,
    limit: int = 50,
) -> list[MemoryRecord]:
    """Read persisted router audit facts from OpenMinion's durable memory store."""
    service = _resolve_memory_service(runtime_or_service)
    return list(
        service.list(
            ListQueryOptions(
                scopes=[scope],
                types=["fact"],
                limit=limit,
            )
        )
    )


def export_audit_bundle(
    runtime_or_service: Any,
    bundle_path: str | Path,
    *,
    scopes: list[str] | None = None,
    include_relations: bool = True,
) -> tuple[MemoryBundleSnapshot, Path]:
    """Export durable audit records into a signed `.tar.gz` `MemoryBundleSnapshot`."""
    service = _resolve_memory_service(runtime_or_service)
    effective_scopes = list(scopes) if scopes else [DEFAULT_AUDIT_SCOPE]
    snapshot = service.export_bundle_snapshot(
        MemoryBundleExportOptions(
            scopes=effective_scopes,
            types=["fact"],
            include_relations=include_relations,
        )
    )
    written = write_bundle_snapshot(snapshot, bundle_path)
    return snapshot, written


def validate_bundle_preflight(
    runtime_or_service: Any,
    snapshot: MemoryBundleSnapshot,
    options: MemoryBundleImportOptions,
) -> list[dict[str, Any]]:
    """Pre-flight validator guarding against OpenMinion 0.1.24 `MemoryMerger` bugs.

    Specifically guards against:
    1. Ignored `namespace_allowlist`: OpenMinion 0.1.24's `MemoryMerger` accepts
       `options.namespace_allowlist` on `MemoryBundleImportOptions` but never enforces it.
    2. Non-atomic `conflict_mode='error'`: OpenMinion 0.1.24's `MemoryMerger._import_direct_mode`
       writes earlier non-conflicting records before hitting a later conflicting record,
       returning `applied=False` while leaving partial writes persisted in SQLite.
    """
    service = _resolve_memory_service(runtime_or_service)
    violations: list[dict[str, Any]] = []

    if options.namespace_allowlist is not None:
        allowlist = list(options.namespace_allowlist)
        for record in snapshot.records:
            rec_ns = _effective_namespace(record, options.scope_rewrites)
            if not any(rec_ns.matches(allowed) for allowed in allowlist):
                violations.append(
                    {
                        "record_id": record.id,
                        "target_id": None,
                        "reason": "namespace_not_allowed",
                        "namespace": rec_ns.as_dict(),
                    }
                )

    if options.trust_mode == "direct" and options.conflict_mode == "error":
        for record in snapshot.records:
            rewritten_scope = str(
                options.scope_rewrites.get(record.scope, record.scope) or ""
            ).strip()
            existing_exact = (
                None
                if options.id_mode == "regenerate"
                else service._store.get(record.id)  # noqa: SLF001
            )
            if existing_exact is not None and not _records_equivalent(
                existing_exact, record, ignore_id=False
            ):
                violations.append(
                    {
                        "record_id": record.id,
                        "target_id": existing_exact.id,
                        "reason": "exact_id_conflict",
                    }
                )
                continue
            if record.key:
                existing_key = service.find_record_by_normalized_key(
                    scope=rewritten_scope,
                    record_type=record.type,
                    normalized_key=record.key,
                )
                if (
                    existing_key is not None
                    and existing_key.id != record.id
                    and not _records_equivalent(existing_key, record, ignore_id=True)
                ):
                    violations.append(
                        {
                            "record_id": record.id,
                            "target_id": existing_key.id,
                            "reason": "normalized_key_conflict",
                        }
                    )

    return violations


def import_audit_bundle_atomic(
    runtime_or_service: Any,
    bundle_or_path: str | Path | MemoryBundleSnapshot,
    *,
    options: MemoryBundleImportOptions | None = None,
) -> MemoryBundleImportResult:
    """Import a `MemoryBundleSnapshot` with atomic pre-flight conflict & namespace checks."""
    service = _resolve_memory_service(runtime_or_service)
    snapshot = (
        bundle_or_path
        if isinstance(bundle_or_path, MemoryBundleSnapshot)
        else read_bundle_snapshot(bundle_or_path)
    )
    effective_options = options or MemoryBundleImportOptions(
        trust_mode="direct",
        conflict_mode="error",
        id_mode="preserve",
    )

    preflight_conflicts = validate_bundle_preflight(
        service, snapshot, effective_options
    )
    if preflight_conflicts:
        return MemoryBundleImportResult(
            applied=False,
            trust_mode=effective_options.trust_mode,
            conflict_mode=effective_options.conflict_mode,
            id_mode=effective_options.id_mode,
            imported_records=0,
            skipped_records=0,
            conflicts=preflight_conflicts,
            rewrites=dict(effective_options.scope_rewrites),
        )

    return service.import_bundle_snapshot(snapshot, effective_options)
