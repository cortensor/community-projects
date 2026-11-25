"""Cortensor Router Doctor: SLA diagnostics, PoI drift auditing, and approval-gated remediation."""

from cortensor_router_doctor.models import (
    PoIDriftAnalysis,
    ProbeResult,
    ProbeRoundSample,
    QuarantineAction,
    RouterAuditReport,
    SLAPolicyEvaluation,
    VerdictMismatchError,
    verify_report_against_evidence,
)
from cortensor_router_doctor.router_sim import (
    RouterNodeProfile,
    SimulatedCortensorRouter,
)
from cortensor_router_doctor.tools import (
    apply_router_quarantine,
    evaluate_sla_policy,
    probe_cortensor_router,
)

__version__ = "0.1.0"

__all__ = [
    "PoIDriftAnalysis",
    "ProbeResult",
    "ProbeRoundSample",
    "QuarantineAction",
    "RouterAuditReport",
    "RouterNodeProfile",
    "SLAPolicyEvaluation",
    "SimulatedCortensorRouter",
    "VerdictMismatchError",
    "__version__",
    "apply_router_quarantine",
    "evaluate_sla_policy",
    "probe_cortensor_router",
    "verify_report_against_evidence",
]
